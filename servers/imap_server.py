#!/usr/bin/env python3
"""
Generic IMAP/SMTP MCP Server for Claude.

Connects to any IMAP-compatible email provider (IONOS, Gmail, Outlook,
self-hosted, etc.) and exposes tools for reading, searching, sending,
and managing emails.

Environment variables:
  IMAP_HOST      — IMAP server hostname (e.g. imap.ionos.de)
  IMAP_PORT      — IMAP server port (default: 993)
  SMTP_HOST      — SMTP server hostname (e.g. smtp.ionos.de)
  SMTP_PORT      — SMTP server port (default: 587)
  EMAIL_ADDRESS  — Full email address for login
  EMAIL_PASSWORD — Password or app-specific password
  IMAP_READ_ONLY — "true" (default) hides send/move/delete; "false" enables them
"""

import os
import sys
import json
import email
import imaplib
import smtplib
import re
from datetime import datetime, timedelta
from email import policy
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, parseaddr

# ---------------------------------------------------------------------------
# MCP Protocol helpers (minimal stdio implementation)
# ---------------------------------------------------------------------------

def read_message():
    """Read a JSON-RPC message from stdin (Content-Length framing)."""
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if line == b"\r\n" or line == b"\n":
            break
        if b":" in line:
            key, value = line.decode().split(":", 1)
            headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", 0))
    if length == 0:
        return None
    body = sys.stdin.buffer.read(length)
    return json.loads(body.decode())


def send_message(msg):
    """Write a JSON-RPC message to stdout (Content-Length framing)."""
    body = json.dumps(msg)
    header = f"Content-Length: {len(body.encode())}\r\n\r\n"
    sys.stdout.buffer.write(header.encode() + body.encode())
    sys.stdout.buffer.flush()


def make_response(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def make_error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# IMAP helpers
# ---------------------------------------------------------------------------

def get_imap_connection():
    host = os.environ.get("IMAP_HOST", "")
    port = int(os.environ.get("IMAP_PORT", "993"))
    user = os.environ.get("EMAIL_ADDRESS", "")
    password = os.environ.get("EMAIL_PASSWORD", "")
    if not host or not user or not password:
        raise ValueError("Missing IMAP configuration. Set IMAP_HOST, EMAIL_ADDRESS, and EMAIL_PASSWORD.")
    conn = imaplib.IMAP4_SSL(host, port)
    conn.login(user, password)
    return conn


def decode_mime_header(raw):
    """Decode a MIME-encoded header value to a plain string."""
    if raw is None:
        return ""
    parts = decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def get_text_from_message(msg):
    """Extract plain-text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        # Fallback to HTML if no plain text
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/html" and "attachment" not in cd:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                html = payload.decode(charset, errors="replace")
                # Minimal HTML strip
                text = re.sub(r"<[^>]+>", " ", html)
                text = re.sub(r"\s+", " ", text).strip()
                return text
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def list_attachments(msg):
    """Return a list of attachment filenames."""
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            cd = str(part.get("Content-Disposition", ""))
            if "attachment" in cd:
                fname = part.get_filename()
                if fname:
                    attachments.append(decode_mime_header(fname))
    return attachments


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def tool_list_folders():
    """List all mailbox folders."""
    conn = get_imap_connection()
    try:
        status, folders_raw = conn.list()
        folders = []
        for f in folders_raw:
            if isinstance(f, bytes):
                # Parse folder name from IMAP LIST response
                match = re.search(rb'"([^"]*)" "?([^"]*)"?$', f)
                if match:
                    folders.append(match.group(2).decode("utf-8", errors="replace"))
                else:
                    decoded = f.decode("utf-8", errors="replace")
                    parts = decoded.rsplit('" ', 1)
                    if len(parts) == 2:
                        folders.append(parts[1].strip('"'))
                    else:
                        folders.append(decoded)
        return {"folders": folders}
    finally:
        conn.logout()


def tool_list_emails(folder="INBOX", limit=20, offset=0):
    """List emails in a folder, most recent first."""
    conn = get_imap_connection()
    try:
        status, _ = conn.select(f'"{folder}"', readonly=True)
        if status != "OK":
            return {"error": f"Could not open folder: {folder}"}

        status, data = conn.search(None, "ALL")
        if status != "OK":
            return {"emails": [], "total": 0}

        ids = data[0].split()
        total = len(ids)
        # Most recent first
        ids = list(reversed(ids))
        page = ids[offset : offset + limit]

        emails = []
        for uid in page:
            status, msg_data = conn.fetch(uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if status == "OK" and msg_data[0] is not None:
                raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
                msg = email.message_from_bytes(raw, policy=policy.default)
                emails.append({
                    "id": uid.decode(),
                    "from": decode_mime_header(msg.get("From", "")),
                    "subject": decode_mime_header(msg.get("Subject", "(no subject)")),
                    "date": decode_mime_header(msg.get("Date", "")),
                })

        return {"emails": emails, "total": total, "folder": folder, "offset": offset, "limit": limit}
    finally:
        conn.logout()


def tool_read_email(email_id, folder="INBOX"):
    """Read a single email by its ID."""
    conn = get_imap_connection()
    try:
        conn.select(f'"{folder}"', readonly=True)
        status, msg_data = conn.fetch(str(email_id).encode(), "(RFC822)")
        if status != "OK" or msg_data[0] is None:
            return {"error": f"Email {email_id} not found in {folder}"}

        raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
        msg = email.message_from_bytes(raw, policy=policy.default)

        return {
            "id": str(email_id),
            "folder": folder,
            "from": decode_mime_header(msg.get("From", "")),
            "to": decode_mime_header(msg.get("To", "")),
            "cc": decode_mime_header(msg.get("Cc", "")),
            "subject": decode_mime_header(msg.get("Subject", "")),
            "date": decode_mime_header(msg.get("Date", "")),
            "body": get_text_from_message(msg),
            "attachments": list_attachments(msg),
        }
    finally:
        conn.logout()


def tool_search_emails(query, folder="INBOX", limit=20):
    """Search emails using IMAP search criteria.

    Supports: subject, from, to, since, before, body text.
    """
    conn = get_imap_connection()
    try:
        conn.select(f'"{folder}"', readonly=True)

        # Build IMAP search criteria
        criteria = []
        if "subject:" in query.lower():
            match = re.search(r'subject:\s*"?([^"]+)"?', query, re.IGNORECASE)
            if match:
                criteria.append(f'SUBJECT "{match.group(1).strip()}"')
        if "from:" in query.lower():
            match = re.search(r'from:\s*"?([^"]+)"?', query, re.IGNORECASE)
            if match:
                criteria.append(f'FROM "{match.group(1).strip()}"')
        if "to:" in query.lower():
            match = re.search(r'to:\s*"?([^"]+)"?', query, re.IGNORECASE)
            if match:
                criteria.append(f'TO "{match.group(1).strip()}"')
        if "since:" in query.lower():
            match = re.search(r'since:\s*(\d{4}-\d{2}-\d{2})', query, re.IGNORECASE)
            if match:
                d = datetime.strptime(match.group(1), "%Y-%m-%d")
                criteria.append(f'SINCE {d.strftime("%d-%b-%Y")}')
        if "before:" in query.lower():
            match = re.search(r'before:\s*(\d{4}-\d{2}-\d{2})', query, re.IGNORECASE)
            if match:
                d = datetime.strptime(match.group(1), "%Y-%m-%d")
                criteria.append(f'BEFORE {d.strftime("%d-%b-%Y")}')

        # If no structured criteria, search in body/subject
        if not criteria:
            clean_query = query.strip()
            if clean_query:
                criteria.append(f'OR SUBJECT "{clean_query}" BODY "{clean_query}"')

        search_str = " ".join(criteria) if criteria else "ALL"
        status, data = conn.search(None, f'({search_str})')

        if status != "OK":
            return {"emails": [], "total": 0, "query": search_str}

        ids = data[0].split()
        total = len(ids)
        ids = list(reversed(ids))[:limit]

        emails = []
        for uid in ids:
            status, msg_data = conn.fetch(uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if status == "OK" and msg_data[0] is not None:
                raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
                msg = email.message_from_bytes(raw, policy=policy.default)
                emails.append({
                    "id": uid.decode(),
                    "from": decode_mime_header(msg.get("From", "")),
                    "subject": decode_mime_header(msg.get("Subject", "(no subject)")),
                    "date": decode_mime_header(msg.get("Date", "")),
                })

        return {"emails": emails, "total": total, "query": search_str}
    finally:
        conn.logout()


def tool_send_email(to, subject, body, cc="", bcc="", reply_to_id="", reply_to_folder="INBOX"):
    """Send an email via SMTP. Optionally reply to an existing message."""
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("EMAIL_ADDRESS", "")
    password = os.environ.get("EMAIL_PASSWORD", "")

    if not smtp_host or not user or not password:
        raise ValueError("Missing SMTP configuration. Set SMTP_HOST, EMAIL_ADDRESS, and EMAIL_PASSWORD.")

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc

    # If replying, set In-Reply-To and References headers
    if reply_to_id:
        try:
            conn = get_imap_connection()
            conn.select(f'"{reply_to_folder}"', readonly=True)
            status, msg_data = conn.fetch(str(reply_to_id).encode(), "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID REFERENCES)])")
            if status == "OK" and msg_data[0] is not None:
                raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
                orig = email.message_from_bytes(raw, policy=policy.default)
                message_id = orig.get("Message-ID", "")
                references = orig.get("References", "")
                if message_id:
                    msg["In-Reply-To"] = message_id
                    msg["References"] = f"{references} {message_id}".strip()
            conn.logout()
        except Exception:
            pass  # Send without reply headers if lookup fails

    msg.attach(MIMEText(body, "plain", "utf-8"))

    recipients = [addr.strip() for addr in to.split(",")]
    if cc:
        recipients += [addr.strip() for addr in cc.split(",")]
    if bcc:
        recipients += [addr.strip() for addr in bcc.split(",")]

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(user, recipients, msg.as_string())

    return {"status": "sent", "to": to, "subject": subject}


def tool_move_email(email_id, source_folder="INBOX", target_folder="Archive"):
    """Move an email to a different folder."""
    conn = get_imap_connection()
    try:
        conn.select(f'"{source_folder}"')
        status, _ = conn.copy(str(email_id).encode(), f'"{target_folder}"')
        if status == "OK":
            conn.store(str(email_id).encode(), "+FLAGS", "\\Deleted")
            conn.expunge()
            return {"status": "moved", "email_id": str(email_id), "from": source_folder, "to": target_folder}
        else:
            return {"error": f"Failed to copy email to {target_folder}"}
    finally:
        conn.logout()


def tool_delete_email(email_id, folder="INBOX"):
    """Move an email to Trash."""
    # Try common trash folder names
    conn = get_imap_connection()
    try:
        status, folders_raw = conn.list()
        trash_folder = None
        trash_names = ["Trash", "Deleted", "Papierkorb", "Deleted Items", "Deleted Messages"]
        for f in folders_raw:
            if isinstance(f, bytes):
                decoded = f.decode("utf-8", errors="replace")
                for tn in trash_names:
                    if tn.lower() in decoded.lower():
                        match = re.search(r'"([^"]*)" "?([^"]*)"?$', f)
                        if match:
                            trash_folder = match.group(2).decode("utf-8", errors="replace")
                        break
            if trash_folder:
                break
        conn.logout()

        if trash_folder and trash_folder != folder:
            return tool_move_email(email_id, folder, trash_folder)
        else:
            # Fallback: flag as deleted
            conn = get_imap_connection()
            try:
                conn.select(f'"{folder}"')
                conn.store(str(email_id).encode(), "+FLAGS", "\\Deleted")
                conn.expunge()
                return {"status": "deleted", "email_id": str(email_id), "folder": folder}
            finally:
                conn.logout()
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# MCP Tool dispatch
# ---------------------------------------------------------------------------

WRITE_TOOLS = {"send_email", "move_email", "delete_email"}


def is_read_only():
    """Return True unless IMAP_READ_ONLY is set to false/0/no (default: true)."""
    return os.environ.get("IMAP_READ_ONLY", "true").strip().lower() not in ("false", "0", "no")


TOOLS = {
    "list_folders": {
        "description": "List all mailbox folders (INBOX, Sent, Drafts, etc.)",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    "list_emails": {
        "description": "List emails in a folder, most recent first. Use offset for pagination.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Mailbox folder (default: INBOX)", "default": "INBOX"},
                "limit": {"type": "integer", "description": "Max emails to return (default: 20)", "default": 20},
                "offset": {"type": "integer", "description": "Skip this many emails (default: 0)", "default": 0},
            },
            "required": [],
        },
    },
    "read_email": {
        "description": "Read a single email's full content by its ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "email_id": {"type": "string", "description": "The email ID from list_emails"},
                "folder": {"type": "string", "description": "Mailbox folder (default: INBOX)", "default": "INBOX"},
            },
            "required": ["email_id"],
        },
    },
    "search_emails": {
        "description": "Search emails. Use structured queries like 'from:name@example.com', 'subject:meeting', 'since:2025-01-01', 'before:2025-12-31', or plain text to search subject and body.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (supports from:, subject:, to:, since:, before:, or plain text)"},
                "folder": {"type": "string", "description": "Mailbox folder (default: INBOX)", "default": "INBOX"},
                "limit": {"type": "integer", "description": "Max results (default: 20)", "default": 20},
            },
            "required": ["query"],
        },
    },
    "send_email": {
        "description": "Send an email via SMTP. Can also reply to an existing email by providing reply_to_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address(es), comma-separated"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body (plain text)"},
                "cc": {"type": "string", "description": "CC recipients, comma-separated", "default": ""},
                "bcc": {"type": "string", "description": "BCC recipients, comma-separated", "default": ""},
                "reply_to_id": {"type": "string", "description": "Email ID to reply to (sets threading headers)", "default": ""},
                "reply_to_folder": {"type": "string", "description": "Folder of the email being replied to", "default": "INBOX"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    "move_email": {
        "description": "Move an email to a different folder.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "email_id": {"type": "string", "description": "The email ID"},
                "source_folder": {"type": "string", "description": "Current folder (default: INBOX)", "default": "INBOX"},
                "target_folder": {"type": "string", "description": "Destination folder"},
            },
            "required": ["email_id", "target_folder"],
        },
    },
    "delete_email": {
        "description": "Move an email to the Trash folder.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "email_id": {"type": "string", "description": "The email ID"},
                "folder": {"type": "string", "description": "Current folder (default: INBOX)", "default": "INBOX"},
            },
            "required": ["email_id"],
        },
    },
}


def dispatch_tool(name, arguments):
    """Call the appropriate tool function."""
    if name in WRITE_TOOLS and is_read_only():
        return {"error": f"{name} is disabled (IMAP_READ_ONLY is on)."}
    try:
        if name == "list_folders":
            return tool_list_folders()
        elif name == "list_emails":
            return tool_list_emails(
                folder=arguments.get("folder", "INBOX"),
                limit=arguments.get("limit", 20),
                offset=arguments.get("offset", 0),
            )
        elif name == "read_email":
            return tool_read_email(
                email_id=arguments["email_id"],
                folder=arguments.get("folder", "INBOX"),
            )
        elif name == "search_emails":
            return tool_search_emails(
                query=arguments["query"],
                folder=arguments.get("folder", "INBOX"),
                limit=arguments.get("limit", 20),
            )
        elif name == "send_email":
            return tool_send_email(
                to=arguments["to"],
                subject=arguments["subject"],
                body=arguments["body"],
                cc=arguments.get("cc", ""),
                bcc=arguments.get("bcc", ""),
                reply_to_id=arguments.get("reply_to_id", ""),
                reply_to_folder=arguments.get("reply_to_folder", "INBOX"),
            )
        elif name == "move_email":
            return tool_move_email(
                email_id=arguments["email_id"],
                source_folder=arguments.get("source_folder", "INBOX"),
                target_folder=arguments["target_folder"],
            )
        elif name == "delete_email":
            return tool_delete_email(
                email_id=arguments["email_id"],
                folder=arguments.get("folder", "INBOX"),
            )
        else:
            return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Main MCP server loop
# ---------------------------------------------------------------------------

def main():
    while True:
        msg = read_message()
        if msg is None:
            break

        method = msg.get("method", "")
        req_id = msg.get("id")
        params = msg.get("params", {})

        if method == "initialize":
            send_message(make_response(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "imap-connector",
                    "version": "0.1.0",
                },
            }))

        elif method == "notifications/initialized":
            pass  # No response needed

        elif method == "tools/list":
            tool_list = [
                {"name": name, "description": spec["description"], "inputSchema": spec["inputSchema"]}
                for name, spec in TOOLS.items()
                if not (name in WRITE_TOOLS and is_read_only())
            ]
            send_message(make_response(req_id, {"tools": tool_list}))

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = dispatch_tool(tool_name, arguments)
            send_message(make_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]
            }))

        elif method == "ping":
            send_message(make_response(req_id, {}))

        else:
            if req_id is not None:
                send_message(make_error(req_id, -32601, f"Method not found: {method}"))


if __name__ == "__main__":
    main()
