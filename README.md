# Gmail MCP Server

A standalone Model Context Protocol (MCP) server that enables AI agents and assistants to manage Gmail accounts through natural language commands. This server acts as middleware that translates AI commands into secure Gmail API calls.

## Overview

Gmail MCP Server is a standalone service that connects to any MCP-compatible client (like OpenWebUI, Claude Desktop, or other AI assistants) and provides complete Gmail integration capabilities:

- **Email Search**: Search emails using keywords, sender names, date ranges, and Gmail operators
- **Email Reading**: Read email content and view conversation threads
- **Email Summarization**: AI-powered summarization of multiple emails at once
- **Attachment Handling**: Download and extract text from attachments (PDF, DOCX, TXT)
- **Email Composition**: Send new emails with AI assistance
- **Draft Management**: Create, list, and manage email drafts
- **Label Management**: Create and manage Gmail labels
- **Email Organization**: Mark emails as read/unread, organize with labels

## Features

### Email Search & Reading
- Advanced search using Gmail search operators
- Retrieve complete message content with headers and body
- View entire conversation threads
- Extract attachment information

### Email Summarization
- Summarize multiple emails at once using AI
- Filter emails by search query for targeted summaries
- Support for unread emails, date ranges, and specific senders
- Configurable detail level (with or without full body content)

### Email Composition
- Send emails with support for To, CC, and BCC
- Reply to existing threads
- Create and manage drafts
- Plain text email support

### Organization & Management
- Create custom labels
- Add/remove labels from messages
- Mark messages as read/unread
- List all available labels

### Attachment Support
- Extract text from PDF files
- Extract text from DOCX files
- Download plain text attachments
- Attachment metadata extraction

## Prerequisites

- **Docker** and **Docker Compose** installed on your system
- **Gmail API credentials** (access token)
- **An MCP-compatible client** (OpenWebUI, Claude Desktop, etc.) already running

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/taddiemason/Gmail-MCP-Server.git
cd Gmail-MCP-Server
```

### 2. Configure Environment

Edit the `.env` file with your Gmail API credentials:

```bash
# Gmail API Access Token (required)
GMAIL_ACCESS_TOKEN=your_gmail_access_token_here

# MCP Server Port (default: 3002)
MCP_PORT=3002

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

**Important**: Replace `your_gmail_access_token_here` with your actual Gmail API access token.

### 3. Get Gmail API Credentials

1. Visit [Google OAuth Playground](https://developers.google.com/oauthplayground/)
2. Select **Gmail API v1** scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/gmail.labels`
3. Click "Authorize APIs"
4. Exchange authorization code for tokens
5. Copy the **Access Token** to your `.env` file

### 4. Start the MCP Server

Using the setup script:

```bash
chmod +x setup.sh
./setup.sh
```

Or manually with Docker Compose:

```bash
docker-compose up -d --build
```

The Gmail MCP Server will be available at: **http://localhost:3002**

### 5. Connect to OpenWebUI

If you have OpenWebUI already running, connect the Gmail MCP Server:

#### Option A: OpenWebUI in Docker (same network)

1. Add the Gmail MCP server to OpenWebUI's network:
   ```bash
   docker network connect openwebui_network gmail-mcp-server
   ```

2. In OpenWebUI:
   - Go to **Settings > Admin Panel > MCP Servers**
   - Click "Add MCP Server"
   - Server URL: `http://gmail-mcp-server:3002`
   - Name: `Gmail MCP`
   - Save

#### Option B: OpenWebUI running locally (not in Docker)

1. In OpenWebUI:
   - Go to **Settings > Admin Panel > MCP Servers**
   - Click "Add MCP Server"
   - Server URL: `http://localhost:3002`
   - Name: `Gmail MCP`
   - Save

#### Option C: Configure via OpenWebUI config file

Add to your OpenWebUI MCP configuration:

```json
{
  "mcpServers": {
    "gmail": {
      "command": "http",
      "args": ["http://localhost:3002"]
    }
  }
}
```

## Available MCP Tools

The Gmail MCP Server provides 15 tools organized by category:

### Search & Read

- **gmail_search_messages**: Search emails using Gmail operators
- **gmail_get_message**: Retrieve full message content
- **gmail_get_thread**: Get entire conversation thread
- **gmail_get_attachment_text**: Extract text from attachments

### Summarization

- **gmail_summarize_emails**: Fetch and format multiple emails for AI summarization

### Compose & Send

- **gmail_send_message**: Send new email or reply to thread
- **gmail_create_draft**: Create email draft
- **gmail_list_drafts**: List all drafts
- **gmail_delete_draft**: Delete a draft

### Organization

- **gmail_list_labels**: List all Gmail labels
- **gmail_create_label**: Create new label
- **gmail_modify_message_labels**: Add/remove labels from message
- **gmail_mark_message_read**: Mark message as read/unread

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GMAIL_ACCESS_TOKEN` | Gmail API access token (required) | - |
| `MCP_PORT` | Port for MCP server | 3002 |
| `LOG_LEVEL` | Logging level | INFO |
| `CHARACTER_LIMIT` | Max response size in characters | 25000 |

### Docker Compose Service

- **gmail-mcp**: Standalone MCP server (port 3002)

## Usage Examples

Once connected to OpenWebUI or another MCP client, you can use natural language:

### Search for emails from a specific sender

```
Search for all emails from john@example.com
```

### Read an email

```
Show me the content of message ID abc123
```

### Summarize emails

```
Summarize my unread emails from today
```

```
Give me a summary of all emails from john@example.com this week
```

### Send an email

```
Send an email to jane@example.com with subject "Meeting Tomorrow" and body "Let's meet at 2 PM"
```

### Create a draft

```
Create a draft email to team@example.com about the project update
```

### Organize emails

```
Create a label called "Important" and add it to message abc123
```

## File Structure

```
Gmail-MCP-Server/
├── Dockerfile           # Docker container configuration
├── docker-compose.yml   # Docker Compose service definition
├── gmail_mcp.py        # Main MCP server implementation
├── requirements.txt    # Python dependencies
├── .env               # Environment configuration
├── setup.sh           # Setup and management script
└── README.md          # This file
```

## Dependencies

Python packages (automatically installed via Docker):

- `mcp` - Model Context Protocol framework
- `fastmcp` - Fast MCP server implementation
- `httpx` - Async HTTP client
- `pydantic` - Data validation
- `PyPDF2` - PDF text extraction (optional)
- `python-docx` - DOCX text extraction (optional)

## Management Commands

Using the setup script:

```bash
./setup.sh
```

Options:
1. Start Gmail MCP Server
2. Stop Gmail MCP Server
3. Restart Gmail MCP Server
4. View logs
5. Check status
6. Update server
7. Clean up (remove all data)
8. Exit

Or use Docker Compose directly:

```bash
# Start server
docker-compose up -d

# View logs
docker-compose logs -f

# Stop server
docker-compose down

# Restart server
docker-compose restart

# Check status
docker-compose ps
```

## Troubleshooting

### Server won't start

```bash
# Check Docker status
docker ps

# View detailed logs
docker-compose logs gmail-mcp

# Restart server
docker-compose restart
```

### Gmail API authentication errors

- Verify your access token is valid and not expired
- Check that you've enabled the correct Gmail API scopes
- Generate a new access token from OAuth Playground if needed

### Port conflicts

If port 3002 is already in use:

1. Edit `.env` file to change `MCP_PORT=3003`
2. Edit `docker-compose.yml` to update port mappings: `3003:3003`
3. Restart server

### OpenWebUI can't connect to MCP server

1. Verify the server is running: `docker-compose ps`
2. Check logs: `docker-compose logs gmail-mcp`
3. Ensure correct URL in OpenWebUI:
   - Docker network: `http://gmail-mcp-server:3002`
   - Local: `http://localhost:3002`
4. Check firewall settings

## Development

### Running locally without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable
export GMAIL_ACCESS_TOKEN=your_token_here

# Run the MCP server
python gmail_mcp.py
```

### Testing

Test individual tools using any MCP client or through OpenWebUI interface.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────┐
│   OpenWebUI     │◄───────►│  Gmail MCP       │◄───────►│  Gmail API  │
│   or other      │   MCP   │  Server          │  HTTPS  │             │
│   MCP Client    │         │  (Port 3002)     │         │             │
└─────────────────┘         └──────────────────┘         └─────────────┘
```

The Gmail MCP Server acts as a bridge between:
1. **MCP Clients** (OpenWebUI, Claude Desktop, etc.) - Send natural language requests
2. **Gmail API** - Processes requests and returns email data

## Security Considerations

- **Never commit your `.env` file** with real credentials to version control
- Use OAuth refresh tokens for production deployments
- Regularly rotate API credentials
- Limit Gmail API scopes to only what's needed
- Use environment-specific access tokens
- Run the MCP server in a private network when possible

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- Compatible with [OpenWebUI](https://github.com/open-webui/open-webui)
- Uses Gmail API for email operations

## Support

For issues, questions, or contributions:

- Open an issue on GitHub
- Check existing documentation
- Review Gmail API documentation

## Changelog

### v2.0.0
- Refactored to standalone MCP server architecture
- Removed bundled OpenWebUI (assumes external instance)
- Simplified Docker setup
- Added comprehensive connection instructions
- Improved documentation

### v1.0.0
- Initial release with bundled OpenWebUI
- Full Gmail integration via MCP
- Email summarization feature
- Comprehensive email management tools
