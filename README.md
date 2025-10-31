# Gmail MCP Server

A comprehensive Model Context Protocol (MCP) server that enables AI agents and assistants to manage Gmail accounts through natural language commands. This server acts as middleware that translates AI commands into secure Gmail API calls.

## Overview

Gmail MCP Server provides a complete set of tools for AI assistants to interact with Gmail, including:

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
- Basic understanding of Docker and Gmail API

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Gmail-MCP-Server.git
cd Gmail-MCP-Server
```

### 2. Configure Environment

The `.env` file is already created with the following configuration:

```bash
# Gmail API Access Token (required)
GMAIL_ACCESS_TOKEN=your_gmail_access_token_here

# OpenWebUI Configuration
OPENWEBUI_ADMIN_EMAIL=admin@example.com
OPENWEBUI_ADMIN_PASSWORD=changeme
ENABLE_SIGNUP=true
DEFAULT_MODELS=llama3.2:latest

# Network Configuration
OPENWEBUI_PORT=3000
OLLAMA_PORT=11434

# MCP Configuration
ENABLE_MCP=true
MCP_SERVERS=gmail
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

### 4. Run Setup Script

```bash
chmod +x setup.sh
./setup.sh
```

The setup script provides options to:
- Start/stop/restart services
- View logs
- Download LLM models
- Check service status
- Update services
- Clean up data

### 5. Access OpenWebUI

Once services are running, access OpenWebUI at:

```
http://localhost:3000
```

Login with the credentials from your `.env` file (default: admin@example.com / changeme)

## Manual Docker Setup

If you prefer to run Docker commands manually:

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Pull a model (required for first run)
docker exec -it ollama ollama pull llama3.2
```

## Available MCP Tools

The Gmail MCP Server provides the following tools:

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
| `OPENWEBUI_PORT` | Port for OpenWebUI | 3000 |
| `OLLAMA_PORT` | Port for Ollama API | 11434 |
| `ENABLE_MCP` | Enable MCP support | true |
| `MCP_SERVERS` | MCP servers to load | gmail |
| `DEFAULT_MODELS` | Default LLM model | llama3.2:latest |

### Docker Compose Services

- **openwebui**: Web interface for AI assistant (port 3000)
- **ollama**: Local LLM service (port 11434)

## Usage Examples

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
├── docker-compose.yml    # Docker services configuration
├── gmail_mcp.py         # Main MCP server implementation
├── requirements.txt     # Python dependencies
├── .env                # Environment configuration
├── setup.sh            # Setup and management script
└── README.md           # This file
```

## Dependencies

Python packages (automatically installed via Docker):

- `mcp` - Model Context Protocol framework
- `fastmcp` - Fast MCP server implementation
- `httpx` - Async HTTP client
- `pydantic` - Data validation
- `PyPDF2` - PDF text extraction (optional)
- `python-docx` - DOCX text extraction (optional)

## Troubleshooting

### Services won't start

```bash
# Check Docker status
docker ps

# View detailed logs
docker-compose logs

# Restart services
docker-compose restart
```

### Gmail API authentication errors

- Verify your access token is valid and not expired
- Check that you've enabled the correct Gmail API scopes
- Generate a new access token from OAuth Playground if needed

### Port conflicts

If port 3000 or 11434 is already in use:

1. Edit `.env` file to change `OPENWEBUI_PORT` or `OLLAMA_PORT`
2. Edit `docker-compose.yml` to update port mappings
3. Restart services

### Model not found

```bash
# List available models
docker exec -it ollama ollama list

# Download a model
docker exec -it ollama ollama pull llama3.2
```

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

Test individual tools using the MCP client or through OpenWebUI interface.

## Security Considerations

- **Never commit your `.env` file** with real credentials to version control
- Use OAuth refresh tokens for production deployments
- Regularly rotate API credentials
- Limit Gmail API scopes to only what's needed
- Use environment-specific access tokens

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
- Uses [OpenWebUI](https://github.com/open-webui/open-webui) for the interface
- Powered by [Ollama](https://ollama.ai/) for local LLM support

## Support

For issues, questions, or contributions:

- Open an issue on GitHub
- Check existing documentation
- Review Gmail API documentation

## Changelog

### v1.0.0
- Initial release
- Full Gmail integration via MCP
- Docker deployment support
- OpenWebUI integration
- Comprehensive email management tools
