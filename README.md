# Gmail MCP Server

A Docker-based Model Context Protocol (MCP) bridge server that provides AI-assisted Gmail management through OpenWebUI. This server enables AI agents to search, read, send, and organize emails via natural language commands.

## Overview

The Gmail MCP Server consists of two components:

1. **MCP Server** - Python-based server that interfaces with Gmail API
2. **MCP Bridge** - Node.js Express server that exposes an HTTP API for OpenWebUI

### Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐         ┌─────────────┐
│   OpenWebUI     │◄───────►│  MCP Bridge      │◄───────►│  Gmail MCP      │◄───────►│  Gmail API  │
│   Tools         │   HTTP  │  (Port 3002)     │  Docker │  Server         │  HTTPS  │             │
└─────────────────┘         └──────────────────┘         └─────────────────┘         └─────────────┘
```

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

- **Docker** and **Docker Compose** installed
- **Docker permissions** configured (see setup below)
- **Gmail API credentials** (access token)
- **OpenWebUI** already running (any version with Tools support)

### Docker Permissions Setup

The bridge server needs access to the Docker socket to communicate with the MCP server container. You have two options:

**Option 1: Add your user to the docker group (Recommended)**

```bash
# Add your user to the docker group
sudo usermod -aG docker $USER

# Activate the changes
newgrp docker

# Verify it works
docker ps
```

After this, you can run docker commands without `sudo`.

**Option 2: Run with sudo**

If you prefer not to add your user to the docker group, run all docker-compose commands with `sudo`:

```bash
sudo docker-compose up -d --build
```

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Gmail-MCP-Server.git
cd Gmail-MCP-Server
```

### 2. Get Gmail API Credentials

1. Visit [Google OAuth Playground](https://developers.google.com/oauthplayground/)
2. Select **Gmail API v1** scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/gmail.labels`
3. Click "Authorize APIs"
4. Exchange authorization code for tokens
5. Copy the **Access Token**

### 3. Configure Credentials

You have **two options** for providing your Gmail API access token:

#### Option A: Using credentials.json (Recommended)

Create a `credentials.json` file in the project root:

```bash
cp credentials.json.example credentials.json
```

Edit `credentials.json`:

```json
{
  "access_token": "your_gmail_access_token_here"
}
```

**Important**:
- Replace `your_gmail_access_token_here` with your actual Gmail API access token
- This file is in `.gitignore` and won't be committed
- Takes priority over environment variables

#### Option B: Using Environment Variables

Edit the `.env` file:

```bash
# Gmail API Access Token (required if not using credentials.json)
GMAIL_ACCESS_TOKEN=your_gmail_access_token_here

# MCP Bridge Server Port (default: 3002)
MCP_PORT=3002

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

**Note**: If both `credentials.json` and `GMAIL_ACCESS_TOKEN` are present, `credentials.json` takes priority.

### 4. Start the MCP Server

Using the setup script:

```bash
chmod +x setup.sh
./setup.sh
```

Select option 1 to start the server.

Or manually with Docker Compose:

```bash
docker-compose up -d --build
```

**Note:** If you get permission errors, you may need to run with `sudo` or add your user to the docker group (see Prerequisites → Docker Permissions Setup above).

The Gmail MCP Bridge will be available at: **http://localhost:3002**

### 5. Add Tool to OpenWebUI

1. **Open OpenWebUI** in your browser
2. Go to **Settings** → **Admin Panel** → **Tools**
3. Click **"+ Create New Tool"**
4. **Copy the contents** of `gmail_tools.py` from this repository
5. **Paste** into the tool editor
6. **Configure the bridge URL** in the Valves section:
   - If OpenWebUI is in Docker: `http://gmail-mcp-bridge:3002`
   - If OpenWebUI is local: `http://localhost:3002`
7. Click **"Save"**
8. **Enable** the Gmail Tools

### 6. Verify Installation

Test the health endpoint:

```bash
curl http://localhost:3002/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "gmail-mcp-bridge"
}
```

## Available Tools in OpenWebUI

Once the Gmail Tools are installed in OpenWebUI, you can use these functions:

### Search & Read
- `search_emails(query, max_results, response_format)` - Search emails
- `get_email(message_id, response_format)` - Get full email content
- `get_thread(thread_id, response_format)` - Get conversation thread
- `get_attachment_text(message_id, attachment_id, mime_type)` - Extract attachment text

### Summarization
- `summarize_emails(query, max_results, include_body)` - Summarize multiple emails

### Compose & Send
- `send_email(to, subject, body, cc, bcc, thread_id)` - Send email
- `create_draft(to, subject, body, cc)` - Create draft
- `list_drafts(max_results, response_format)` - List drafts
- `delete_draft(draft_id)` - Delete draft

### Organization
- `list_labels(response_format)` - List all labels
- `create_label(name, label_list_visibility, message_list_visibility)` - Create label
- `modify_labels(message_id, add_labels, remove_labels)` - Modify message labels
- `mark_read(message_id, mark_as_read)` - Mark as read/unread

## Usage Examples

### Using Natural Language in OpenWebUI

Once installed, you can ask the AI assistant in OpenWebUI:

```
Search for all unread emails from today
```

```
Summarize my emails from john@example.com this week
```

```
Send an email to jane@example.com with subject "Meeting Tomorrow" and tell her we'll meet at 2 PM
```

```
Create a draft to team@example.com about the project update
```

```
Mark message abc123 as read
```

```
Create a label called "Important" and add it to my latest email from boss@company.com
```

The AI will automatically call the appropriate Gmail tool functions to complete your request.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GMAIL_ACCESS_TOKEN` | Gmail API access token (required) | - |
| `MCP_PORT` | Port for MCP bridge server | 3002 |
| `LOG_LEVEL` | Logging level | INFO |

### Bridge URL Configuration

In OpenWebUI's Gmail Tools Valves settings:

- **Docker network**: `http://gmail-mcp-bridge:3002` (if OpenWebUI container is on same network)
- **Local**: `http://localhost:3002` (if OpenWebUI runs outside Docker)
- **Remote**: `http://YOUR_SERVER_IP:3002` (if bridge is on different host)

## File Structure

```
Gmail-MCP-Server/
├── Dockerfile              # Gmail MCP server container
├── Dockerfile.bridge       # Bridge server container
├── docker-compose.yml      # Multi-container orchestration
├── gmail_mcp.py           # Main MCP server implementation
├── bridge-server.js       # HTTP API bridge server
├── gmail_tools.py         # OpenWebUI Tool (upload to OpenWebUI)
├── requirements.txt       # Python dependencies
├── .env                   # Environment configuration
├── setup.sh              # Setup and management script
└── README.md             # This file
```

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
7. Clean up
8. Exit

Or use Docker Compose directly:

```bash
# Start servers
docker-compose up -d --build

# View logs
docker-compose logs -f

# View bridge logs only
docker-compose logs -f mcp-bridge

# View MCP server logs only
docker-compose logs -f gmail-mcp-server

# Stop servers
docker-compose down

# Restart servers
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
docker-compose logs

# Restart servers
docker-compose restart
```

### Docker Permission Errors

If you see errors like:
- `PermissionError: [Errno 13] Permission denied`
- `Error while fetching server API version: Connection aborted`
- `docker: not found` (when running inside bridge container)

**Solution 1: Add user to docker group (Recommended)**

```bash
# Add your user to the docker group
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker

# Verify it works
docker ps

# Restart the services
docker-compose down
docker-compose up -d --build
```

**Solution 2: Run with sudo**

```bash
sudo docker-compose down
sudo docker-compose up -d --build
sudo docker-compose logs -f
```

**Why this happens:**

The bridge container needs to execute `docker exec` commands to communicate with the gmail-mcp-server container. This requires access to `/var/run/docker.sock`, which is only accessible by the docker group or root.

### Gmail API authentication errors

- Verify your access token is valid and not expired
- Check that you've enabled the correct Gmail API scopes
- Generate a new access token from OAuth Playground if needed

### Port conflicts

If port 3002 is already in use:

1. Edit `.env` file: `MCP_PORT=3003`
2. Edit `docker-compose.yml`: Update port mapping to `3003:3003` and environment `PORT=3003`
3. Restart: `docker-compose down && docker-compose up -d --build`
4. Update bridge URL in OpenWebUI Tool Valves

### OpenWebUI can't connect to bridge

1. **Verify bridge is running**: `docker-compose ps`
2. **Check bridge logs**: `docker-compose logs mcp-bridge`
3. **Test health endpoint**: `curl http://localhost:3002/health`
4. **Check bridge URL** in OpenWebUI Tool Valves settings:
   - If both in Docker on same network: `http://gmail-mcp-bridge:3002`
   - If OpenWebUI is local: `http://localhost:3002`
   - If on different hosts: `http://SERVER_IP:3002`
5. **Connect Docker networks** if needed:
   ```bash
   docker network connect openwebui_network gmail-mcp-bridge
   ```

### Tools not appearing in OpenWebUI

1. Make sure you saved the `gmail_tools.py` in OpenWebUI Tools
2. Enable the Gmail Tools in OpenWebUI Settings
3. Refresh the page
4. Check OpenWebUI logs for errors

### Commands timeout

- Increase timeout in OpenWebUI Tool Valves (default: 300 seconds)
- Check Gmail API quota limits
- Verify network connectivity

## Security Considerations

- **Never commit `.env` file** with real credentials to version control
- Use OAuth refresh tokens for production deployments
- Regularly rotate API credentials
- Limit Gmail API scopes to only what's needed
- Run bridge server in private network when possible
- **Add authentication** to bridge server for production use
- Monitor API usage and set quotas

## Development

### Running locally without Docker

**MCP Server:**
```bash
cd Gmail-MCP-Server
pip install -r requirements.txt
export GMAIL_ACCESS_TOKEN=your_token_here
python gmail_mcp.py
```

**Bridge Server:**
```bash
npm install express cors
export PORT=3002
node bridge-server.js
```

### Testing the Bridge API

```bash
# Health check
curl http://localhost:3002/health

# Test search
curl -X POST http://localhost:3002/v1/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "gmail_search_messages",
    "arguments": {
      "query": "is:unread",
      "max_results": 5
    }
  }'
```

## API Reference

### Bridge Endpoints

**Health Check**
```
GET /health
Response: {"status": "ok", "service": "gmail-mcp-bridge"}
```

**Execute Tool**
```
POST /v1/tools/execute
Content-Type: application/json

Body:
{
  "tool_name": "gmail_search_messages",
  "arguments": {
    "query": "is:unread",
    "max_results": 10
  }
}
```

## Dependencies

**Python packages** (gmail-mcp-server):
- `mcp` - Model Context Protocol framework
- `fastmcp` - Fast MCP server implementation
- `httpx` - Async HTTP client
- `pydantic` - Data validation
- `PyPDF2` - PDF text extraction (optional)
- `python-docx` - DOCX text extraction (optional)

**Node.js packages** (mcp-bridge):
- `express` - Web server framework
- `cors` - CORS middleware

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
- Designed for [OpenWebUI](https://github.com/open-webui/open-webui)
- Uses Gmail API for email operations
- Inspired by the Kali-Pentest-MCP bridge architecture

## Support

For issues, questions, or contributions:

- Open an issue on GitHub
- Check existing documentation
- Review Gmail API documentation

## Changelog

### v2.0.0
- Added MCP bridge server architecture
- Created OpenWebUI Tool for easy integration
- Added all 13 Gmail management tools
- Email summarization feature
- Comprehensive documentation

### v1.0.0
- Initial release with basic Gmail integration
