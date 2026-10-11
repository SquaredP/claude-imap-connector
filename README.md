# Claude IMAP Connector

A universal MCP (Model Context Protocol) server that connects Claude to any IMAP/SMTP email account. Works with IONOS, Gmail, Outlook, Fastmail, self-hosted servers, and more.

This MCP server enables Claude to interact with your email through natural language commands. Read, search, send, and organize emails directly from your Claude conversations.

## Features

- **Read emails** — browse your inbox and other folders
- **Search** — find emails by sender, subject, date, or keywords
- **Send** — compose and send emails via SMTP, including threaded replies
- **Organize** — move emails between folders and delete messages
- **List folders** — see all available mailbox folders

## Setup

### Required Environment Variables

Set these in your system environment or Claude configuration:

| Variable | Description | Example |
|----------|-------------|---------|
| `IMAP_HOST` | IMAP server hostname | `imap.ionos.de` |
| `IMAP_PORT` | IMAP server port (default: 993) | `993` |
| `SMTP_HOST` | SMTP server hostname | `smtp.ionos.de` |
| `SMTP_PORT` | SMTP server port (default: 587) | `587` |
| `TLS_CA_FILE` | Optional PEM file with extra trusted certificate(s), for self-signed servers | `/etc/ssl/my-mail.pem` |
| `TLS_VERIFY` | Set to `false` to skip certificate checks (insecure, default: `true`) | `true` |
| `EMAIL_ADDRESS` | Your email address (used for login) | `your-email@example.com` |
| `EMAIL_PASSWORD` | Email password or app-specific password | `your-password` |

### Common Provider Settings

| Provider | IMAP Host | SMTP Host |
|----------|-----------|-----------|
| IONOS | `imap.ionos.de` | `smtp.ionos.de` |
| Gmail | `imap.gmail.com` | `smtp.gmail.com` |
| Outlook | `outlook.office365.com` | `smtp.office365.com` |
| Yahoo | `imap.mail.yahoo.com` | `smtp.mail.yahoo.com` |
| Fastmail | `imap.fastmail.com` | `smtp.fastmail.com` |
| GMX | `imap.gmx.net` | `mail.gmx.net` |
| Web.de | `imap.web.de` | `smtp.web.de` |

> **Gmail users**: You need an [App Password](https://support.google.com/accounts/answer/185833) since Gmail blocks less secure apps.

## Commands

| Command | Description |
|---------|-------------|
| `/mail-check` | Check your inbox for recent emails |
| `/mail-search [query]` | Search emails (e.g., `/mail-search emails from Max about training`) |
| `/mail-send [details]` | Compose and send an email |

## MCP Tools

The connector exposes these tools for direct use:

- `list_folders` — List all mailbox folders
- `list_emails` — List emails in a folder with pagination
- `read_email` — Read a single email's full content
- `search_emails` — Search with structured queries (`from:`, `subject:`, `since:`, `before:`)
- `send_email` — Send an email with optional CC/BCC and reply threading
- `move_email` — Move an email between folders
- `delete_email` — Move an email to trash

## Security Notes

- Credentials are passed via environment variables and never stored in the plugin
- All IMAP connections use SSL/TLS (port 993)
- SMTP connections use STARTTLS (port 587)
- Emails are never sent without explicit user confirmation

## Troubleshooting

- **Connection refused**: Verify IMAP_HOST and SMTP_HOST are correct for your provider
- **Authentication failed**: Double-check EMAIL_ADDRESS and EMAIL_PASSWORD; some providers require app-specific passwords
- **Certificate verify failed**: Your server likely uses a self-signed certificate. Export it (e.g. `openssl s_client -connect imap.example.com:993 -showcerts`) and point `TLS_CA_FILE` at it. `TLS_VERIFY=false` also works but lets anyone on the network path read your password.
- **Folder not found**: Use `/mail-check` with `list_folders` to see available folder names — they vary by provider and language

## Quick Start

1. **Copy the example configuration**:
   ```bash
   cp .mcp.json.example .mcp.json
   ```

2. **Edit `.mcp.json`** with your email provider settings

3. **Install in Claude**:
   - Place this folder in your Claude plugins directory
   - Restart Claude to load the connector

4. **Test it**:
   ```
   /mail-check
   ```

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Setting up the development environment
- Code style and standards
- Submitting pull requests
- Feature ideas and enhancements

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/SquaredP/Claude-IMAP-Connector/issues)
- **Community**: Join the Claude community to discuss email automation workflows
- **Security**: For security concerns, please review our security practices in CONTRIBUTING.md
