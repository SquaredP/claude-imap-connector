# Contributing to Claude IMAP Connector

Thank you for your interest in contributing to the Claude IMAP Connector! This MCP (Model Context Protocol) server enables Claude to interact with email accounts through natural language. This document provides guidelines and instructions for setting up and contributing to the project.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Access to an IMAP/SMTP email account
- Claude Desktop or Claude Code installed

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/SquaredP/Claude-IMAP-Connector.git
   cd Claude-IMAP-Connector
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   Or if you don't have a requirements.txt yet, the connector uses these standard libraries:
   - `imaplib` (built-in)
   - `smtplib` (built-in)
   - `email` (built-in)

3. **Configure your email settings**

   Copy the example configuration file:
   ```bash
   cp .mcp.json.example .mcp.json
   ```

   Edit `.mcp.json` and add your email credentials:
   ```json
   {
     "mcpServers": {
       "imap-connector": {
         "command": "python3",
         "args": ["${CLAUDE_PLUGIN_ROOT}/servers/imap_server.py"],
         "env": {
           "IMAP_HOST": "imap.your-provider.com",
           "IMAP_PORT": "993",
           "SMTP_HOST": "smtp.your-provider.com",
           "SMTP_PORT": "587",
           "TLS_CA_FILE": "",
           "TLS_VERIFY": "true",
           "EMAIL_ADDRESS": "your-email@example.com",
           "EMAIL_PASSWORD": "your-app-password"
         }
       }
     }
   }
   ```

   **Important**: Never commit your `.mcp.json` file with real credentials!

4. **Test the connector**
   ```bash
   python3 servers/imap_server.py
   ```

## Development Guidelines

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and modular

### Adding New Features

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Implement your feature**
   - Add new MCP tools in `servers/imap_server.py`
   - Create corresponding command files in `commands/` if needed
   - Update documentation in `README.md`

3. **Test thoroughly**
   - Test with multiple email providers (Gmail, Outlook, etc.)
   - Verify error handling
   - Ensure backward compatibility

4. **Submit a pull request**
   - Write a clear description of your changes
   - Reference any related issues
   - Include examples of usage

### Common Enhancement Ideas

- **Attachment support**: Download and upload email attachments
- **HTML email rendering**: Better handling of HTML emails
- **Advanced search**: More complex query operators
- **Calendar integration**: Parse and create calendar invitations
- **Email templates**: Pre-defined email templates
- **Batch operations**: Move/delete multiple emails at once
- **Label/tag support**: Gmail labels and folder management
- **Draft support**: Save and manage email drafts

## Testing

### Manual Testing

Test against different email providers:
- Gmail (requires App Password)
- Outlook/Office 365
- IONOS
- Yahoo Mail
- Fastmail
- Self-hosted mail servers

### Test Cases

- [ ] List folders from mailbox
- [ ] Read emails from inbox
- [ ] Search emails with various criteria
- [ ] Send plain text email
- [ ] Send email with CC/BCC
- [ ] Reply to existing thread
- [ ] Move email between folders
- [ ] Delete email
- [ ] Handle authentication errors
- [ ] Handle network timeouts
- [ ] Handle malformed email data

## Security Considerations

- Never log or store email passwords
- Use SSL/TLS for all connections
- Validate user input to prevent injection attacks
- Handle sensitive data carefully
- Request explicit user confirmation before sending emails

## Documentation

When adding features, please update:
- `README.md` - User-facing documentation
- Command files in `commands/` - Command descriptions
- Code comments and docstrings
- This `CONTRIBUTING.md` if setup changes

## Questions or Issues?

- Open an issue on GitHub
- Tag issues appropriately (bug, enhancement, question)
- Provide detailed reproduction steps for bugs
- Include your email provider and any relevant error messages

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
