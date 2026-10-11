---
description: Compose and send an email
argument-hint: [recipient or description]
allowed-tools: ["mcp__imap-connector__send_email", "mcp__imap-connector__read_email", "mcp__imap-connector__search_emails"]
---

Help the user compose and send an email: $ARGUMENTS

Follow this process:

1. **Gather information**: Determine the recipient (to), subject, and body from the user's input. Ask for anything that's missing.
2. **Draft the email**: Write a draft and present it to the user for review before sending. Show to, subject, and body clearly.
3. **Get confirmation**: ALWAYS ask for explicit confirmation before calling `send_email`. Never send without the user saying "yes" or "send".
4. **Send**: Once confirmed, call `send_email` with the final to, subject, body, and optional cc/bcc.
5. **Confirm delivery**: Report that the email was sent successfully.

If the user wants to reply to an existing email:
- First search or list emails to find the original message
- Read the original email for context
- Use `reply_to_id` when sending to maintain the email thread

If `send_email` reports that it is disabled, tell the user to set `IMAP_READ_ONLY=false` in their configuration and restart Claude.

Write emails in the same language the user is using. Keep the tone appropriate to the context.
