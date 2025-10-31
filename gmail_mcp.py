"""Gmail MCP Server

A comprehensive MCP server for Gmail integration that enables AI assistants to:
- Search emails using keywords, sender names, or date ranges
- Read email content and view conversation threads
- Download and extract text from attachments (PDF, DOCX, TXT)
- Send new emails with AI assistance
- Draft and manage email replies
- Create and manage labels
- Mark emails as read/unread

This server follows MCP best practices for tool design, response formatting, and error handling.
"""

import json
import base64
import io
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, field_validator, ConfigDict
import httpx

# Constants
CHARACTER_LIMIT = 25000  # Maximum response size in characters
API_BASE_URL = "https://gmail.googleapis.com/gmail/v1"
DEFAULT_MAX_RESULTS = 20


# Response format enum
class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


# Lifespan management for persistent HTTP client
@asynccontextmanager
async def app_lifespan(app):
    """Manage HTTP client lifecycle."""
    client = httpx.AsyncClient(timeout=30.0)
    yield {"http_client": client}
    await client.aclose()


# Initialize FastMCP server
mcp = FastMCP("gmail_mcp", lifespan=app_lifespan)


# ============================================================================
# SHARED UTILITIES
# ============================================================================

def format_timestamp(timestamp_ms: int) -> str:
    """Convert Gmail timestamp (milliseconds) to human-readable format."""
    dt = datetime.fromtimestamp(int(timestamp_ms) / 1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def extract_email_address(email_str: str) -> str:
    """Extract email address from 'Name <email@domain.com>' format."""
    match = re.search(r'<(.+?)>', email_str)
    return match.group(1) if match else email_str


def truncate_response(content: str, metadata: Dict[str, Any] = None) -> str:
    """Truncate response if it exceeds CHARACTER_LIMIT."""
    if len(content) <= CHARACTER_LIMIT:
        return content
    
    truncated = content[:CHARACTER_LIMIT]
    truncation_msg = f"\n\n[Response truncated at {CHARACTER_LIMIT} characters. "
    
    if metadata:
        truncation_msg += "Use filters or pagination to refine results.]"
    else:
        truncation_msg += "Original content was longer.]"
    
    return truncated + truncation_msg


async def make_gmail_request(
    ctx: Context,
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Make authenticated request to Gmail API.
    
    Args:
        ctx: Context containing HTTP client and auth
        method: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint (without base URL)
        params: Query parameters
        json_data: JSON request body
        
    Returns:
        API response as dictionary
        
    Raises:
        httpx.HTTPStatusError: On API errors with helpful messages
    """
    client = ctx.request_context.lifespan_state["http_client"]
    
    # Get access token - in production, this would come from OAuth flow
    # For now, we'll request it interactively when needed
    access_token = await ctx.elicit(
        prompt="Please provide your Gmail API access token:",
        input_type="password"
    )
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        response = await client.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        error_msg = f"Gmail API error: {e.response.status_code}"
        try:
            error_data = e.response.json()
            if "error" in error_data:
                error_msg += f" - {error_data['error'].get('message', 'Unknown error')}"
        except:
            pass
        raise httpx.HTTPStatusError(error_msg, request=e.request, response=e.response)


def format_email_markdown(message: Dict[str, Any], include_body: bool = True) -> str:
    """Format email message as Markdown."""
    headers = {h["name"]: h["value"] for h in message.get("payload", {}).get("headers", [])}
    
    result = f"# Email: {headers.get('Subject', '(No Subject)')}\n\n"
    result += f"**From:** {headers.get('From', 'Unknown')}\n"
    result += f"**To:** {headers.get('To', 'Unknown')}\n"
    
    if headers.get('Cc'):
        result += f"**Cc:** {headers['Cc']}\n"
    
    result += f"**Date:** {headers.get('Date', 'Unknown')}\n"
    result += f"**Message ID:** {message['id']}\n"
    
    labels = message.get("labelIds", [])
    if labels:
        result += f"**Labels:** {', '.join(labels)}\n"
    
    if include_body:
        result += f"\n## Body\n\n"
        body = extract_email_body(message)
        result += body if body else "(No body content)"
    
    return result


def format_email_json(message: Dict[str, Any]) -> Dict[str, Any]:
    """Format email message as structured JSON."""
    headers = {h["name"]: h["value"] for h in message.get("payload", {}).get("headers", [])}
    
    return {
        "id": message["id"],
        "thread_id": message.get("threadId"),
        "subject": headers.get("Subject", "(No Subject)"),
        "from": headers.get("From", "Unknown"),
        "to": headers.get("To", "Unknown"),
        "cc": headers.get("Cc"),
        "date": headers.get("Date", "Unknown"),
        "timestamp": message.get("internalDate"),
        "labels": message.get("labelIds", []),
        "snippet": message.get("snippet"),
        "body": extract_email_body(message)
    }


def extract_email_body(message: Dict[str, Any]) -> str:
    """Extract email body text from message payload."""
    payload = message.get("payload", {})
    
    # Try to get body from parts
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                body_data = part.get("body", {}).get("data")
                if body_data:
                    return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
    
    # Try to get body directly
    body_data = payload.get("body", {}).get("data")
    if body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
    
    return ""


def extract_attachments_info(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract attachment metadata from message."""
    attachments = []
    payload = message.get("payload", {})
    
    def process_part(part: Dict[str, Any]):
        if part.get("filename"):
            attachments.append({
                "filename": part["filename"],
                "mime_type": part.get("mimeType"),
                "size": part.get("body", {}).get("size", 0),
                "attachment_id": part.get("body", {}).get("attachmentId")
            })
        
        if "parts" in part:
            for subpart in part["parts"]:
                process_part(subpart)
    
    if "parts" in payload:
        for part in payload["parts"]:
            process_part(part)
    
    return attachments


async def download_attachment_text(
    ctx: Context,
    message_id: str,
    attachment_id: str,
    mime_type: str
) -> str:
    """Download attachment and extract text content.
    
    Supports PDF, DOCX, and TXT files.
    """
    # Download attachment
    response = await make_gmail_request(
        ctx,
        "GET",
        f"/users/me/messages/{message_id}/attachments/{attachment_id}"
    )
    
    attachment_data = base64.urlsafe_b64decode(response["data"])
    
    # Extract text based on MIME type
    if mime_type == "text/plain":
        return attachment_data.decode("utf-8", errors="ignore")
    
    elif mime_type == "application/pdf":
        # Extract text from PDF using PyPDF2
        try:
            import PyPDF2
            pdf_file = io.BytesIO(attachment_data)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except ImportError:
            return "[PDF text extraction requires PyPDF2 library]"
        except Exception as e:
            return f"[Error extracting PDF text: {str(e)}]"
    
    elif mime_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
        # Extract text from DOCX using python-docx
        try:
            import docx
            docx_file = io.BytesIO(attachment_data)
            doc = docx.Document(docx_file)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except ImportError:
            return "[DOCX text extraction requires python-docx library]"
        except Exception as e:
            return f"[Error extracting DOCX text: {str(e)}]"
    
    else:
        return f"[Unsupported file type: {mime_type}]"


# ============================================================================
# SEARCH TOOLS
# ============================================================================

class GmailSearchInput(BaseModel):
    """Input model for searching Gmail messages."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    query: str = Field(
        ...,
        description=(
            "Gmail search query using Gmail search operators. Examples:\n"
            "- 'from:john@example.com' - emails from specific sender\n"
            "- 'subject:meeting' - emails with 'meeting' in subject\n"
            "- 'after:2024/01/01 before:2024/12/31' - date range\n"
            "- 'has:attachment' - emails with attachments\n"
            "- 'is:unread' - unread emails\n"
            "- 'in:inbox' - emails in inbox\n"
            "Multiple terms can be combined: 'from:john subject:report after:2024/10/01'"
        ),
        min_length=1,
        max_length=500
    )
    max_results: int = Field(
        default=DEFAULT_MAX_RESULTS,
        description="Maximum number of results to return",
        ge=1,
        le=100
    )
    page_token: Optional[str] = Field(
        default=None,
        description="Token for pagination to get next page of results"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for structured data"
    )


@mcp.tool(
    name="gmail_search_messages",
    annotations={
        "title": "Search Gmail Messages",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def gmail_search_messages(params: GmailSearchInput, ctx: Context) -> str:
    """Search Gmail messages using Gmail search operators.
    
    This tool allows searching emails by keywords, sender, date ranges, labels, and more.
    It uses the same query syntax as the Gmail web interface.
    
    Args:
        params (GmailSearchInput): Search parameters containing:
            - query (str): Gmail search query with operators
            - max_results (int): Maximum results to return (default: 20, max: 100)
            - page_token (Optional[str]): Token for pagination
            - response_format (ResponseFormat): Output format (markdown or json)
    
    Returns:
        str: Search results in requested format with message summaries and pagination info
        
    Examples:
        - Search for emails from a specific sender: query="from:john@example.com"
        - Search by date range: query="after:2024/01/01 before:2024/12/31"
        - Search unread emails: query="is:unread"
        - Complex search: query="from:boss subject:urgent after:2024/10/01"
    """
    try:
        # Search messages
        search_params = {
            "q": params.query,
            "maxResults": params.max_results
        }
        if params.page_token:
            search_params["pageToken"] = params.page_token
        
        response = await make_gmail_request(ctx, "GET", "/users/me/messages", params=search_params)
        
        messages = response.get("messages", [])
        next_page_token = response.get("nextPageToken")
        result_size_estimate = response.get("resultSizeEstimate", 0)
        
        if not messages:
            return "No messages found matching the search query."
        
        # Fetch details for each message
        detailed_messages = []
        for msg in messages:
            msg_detail = await make_gmail_request(ctx, "GET", f"/users/me/messages/{msg['id']}")
            detailed_messages.append(msg_detail)
        
        # Format response
        if params.response_format == ResponseFormat.MARKDOWN:
            result = f"# Gmail Search Results\n\n"
            result += f"**Query:** `{params.query}`\n"
            result += f"**Results:** {len(messages)} of approximately {result_size_estimate} total\n\n"
            
            for i, msg in enumerate(detailed_messages, 1):
                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                result += f"## {i}. {headers.get('Subject', '(No Subject)')}\n"
                result += f"- **From:** {headers.get('From', 'Unknown')}\n"
                result += f"- **Date:** {headers.get('Date', 'Unknown')}\n"
                result += f"- **Message ID:** {msg['id']}\n"
                result += f"- **Snippet:** {msg.get('snippet', '')}\n"
                
                attachments = extract_attachments_info(msg)
                if attachments:
                    result += f"- **Attachments:** {', '.join([a['filename'] for a in attachments])}\n"
                
                result += "\n"
            
            if next_page_token:
                result += f"\n**More results available.** Use page_token='{next_page_token}' to get the next page.\n"
        
        else:  # JSON format
            result_data = {
                "query": params.query,
                "result_count": len(messages),
                "estimated_total": result_size_estimate,
                "messages": [format_email_json(msg) for msg in detailed_messages],
                "has_more": bool(next_page_token),
                "next_page_token": next_page_token
            }
            result = json.dumps(result_data, indent=2)
        
        return truncate_response(result, {"next_page_token": next_page_token})
        
    except httpx.HTTPStatusError as e:
        return f"Error searching Gmail: {str(e)}. Please check your query syntax and try again."
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# EMAIL SUMMARIZATION TOOLS
# ============================================================================

class SummarizeEmailsInput(BaseModel):
    """Input model for summarizing multiple emails."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

    query: str = Field(
        ...,
        description=(
            "Gmail search query to find emails to summarize. Examples:\n"
            "- 'is:unread' - summarize unread emails\n"
            "- 'from:john@example.com after:2024/10/01' - emails from John since Oct 1\n"
            "- 'subject:meeting' - emails about meetings\n"
            "Use Gmail search operators to filter emails for summarization."
        ),
        min_length=1,
        max_length=500
    )
    max_results: int = Field(
        default=10,
        description="Maximum number of emails to include in summary",
        ge=1,
        le=50
    )
    include_body: bool = Field(
        default=True,
        description="Include email body content (recommended for detailed summaries)"
    )


@mcp.tool(
    name="gmail_summarize_emails",
    annotations={
        "title": "Summarize Gmail Messages",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def gmail_summarize_emails(params: SummarizeEmailsInput, ctx: Context) -> str:
    """Fetch and format emails for summarization by the AI assistant.

    This tool retrieves multiple emails based on a search query and formats them
    in a way that makes it easy for the AI to generate summaries. The actual
    summarization is performed by the AI assistant, not this tool.

    Args:
        params (SummarizeEmailsInput): Parameters containing:
            - query (str): Gmail search query to find emails
            - max_results (int): Maximum emails to include (default: 10, max: 50)
            - include_body (bool): Include email body content for detailed summaries

    Returns:
        str: Formatted email data ready for AI summarization

    Examples:
        - Summarize unread emails: query="is:unread"
        - Summarize today's emails: query="after:2024/10/31"
        - Summarize emails from a person: query="from:john@example.com"
    """
    try:
        # Search for emails
        search_params = {
            "q": params.query,
            "maxResults": params.max_results
        }

        response = await make_gmail_request(ctx, "GET", "/users/me/messages", params=search_params)

        messages = response.get("messages", [])
        result_size_estimate = response.get("resultSizeEstimate", 0)

        if not messages:
            return "No messages found matching the search query. Cannot generate summary."

        # Fetch details for each message
        detailed_messages = []
        for msg in messages:
            msg_detail = await make_gmail_request(ctx, "GET", f"/users/me/messages/{msg['id']}")
            detailed_messages.append(msg_detail)

        # Format for summarization
        result = f"# Emails for Summarization\n\n"
        result += f"**Search Query:** `{params.query}`\n"
        result += f"**Emails Retrieved:** {len(messages)} of approximately {result_size_estimate} total\n"
        result += f"**Note:** Please provide a concise summary of these emails.\n\n"
        result += "---\n\n"

        for i, msg in enumerate(detailed_messages, 1):
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

            result += f"## Email {i}/{len(messages)}\n\n"
            result += f"**Subject:** {headers.get('Subject', '(No Subject)')}\n"
            result += f"**From:** {headers.get('From', 'Unknown')}\n"
            result += f"**To:** {headers.get('To', 'Unknown')}\n"
            result += f"**Date:** {headers.get('Date', 'Unknown')}\n"

            # Include snippet for quick overview
            result += f"**Snippet:** {msg.get('snippet', '')}\n"

            # Optionally include body for detailed summary
            if params.include_body:
                body = extract_email_body(msg)
                if body:
                    # Truncate very long bodies to keep response manageable
                    body_preview = body[:1000] + "..." if len(body) > 1000 else body
                    result += f"\n**Content:**\n{body_preview}\n"

            # Check for attachments
            attachments = extract_attachments_info(msg)
            if attachments:
                result += f"**Attachments:** {', '.join([a['filename'] for a in attachments])}\n"

            result += "\n---\n\n"

        return truncate_response(result)

    except httpx.HTTPStatusError as e:
        return f"Error fetching emails for summary: {str(e)}. Please check your query syntax."
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# READ EMAIL TOOLS
# ============================================================================

class GetEmailInput(BaseModel):
    """Input model for retrieving a specific email message."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    message_id: str = Field(
        ...,
        description="The Gmail message ID to retrieve",
        min_length=1
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for structured data"
    )
    include_attachments_info: bool = Field(
        default=True,
        description="Include information about attachments in the response"
    )


@mcp.tool(
    name="gmail_get_message",
    annotations={
        "title": "Get Gmail Message",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def gmail_get_message(params: GetEmailInput, ctx: Context) -> str:
    """Retrieve the full content of a specific Gmail message.
    
    This tool fetches complete message details including headers, body, and attachment info.
    
    Args:
        params (GetEmailInput): Parameters containing:
            - message_id (str): Gmail message ID to retrieve
            - response_format (ResponseFormat): Output format (markdown or json)
            - include_attachments_info (bool): Include attachment details
    
    Returns:
        str: Complete message content in requested format
    """
    try:
        message = await make_gmail_request(ctx, "GET", f"/users/me/messages/{params.message_id}")
        
        if params.response_format == ResponseFormat.MARKDOWN:
            result = format_email_markdown(message, include_body=True)
            
            if params.include_attachments_info:
                attachments = extract_attachments_info(message)
                if attachments:
                    result += "\n## Attachments\n\n"
                    for att in attachments:
                        result += f"- **{att['filename']}** ({att['mime_type']}, {att['size']} bytes)\n"
                        result += f"  - Attachment ID: {att['attachment_id']}\n"
        else:
            result = json.dumps(format_email_json(message), indent=2)
        
        return truncate_response(result)
        
    except httpx.HTTPStatusError as e:
        return f"Error retrieving message: {str(e)}. Please verify the message ID is correct."
    except Exception as e:
        return f"Unexpected error: {str(e)}"


class GetThreadInput(BaseModel):
    """Input model for retrieving an email thread."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    thread_id: str = Field(
        ...,
        description="The Gmail thread ID to retrieve",
        min_length=1
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for structured data"
    )


@mcp.tool(
    name="gmail_get_thread",
    annotations={
        "title": "Get Gmail Thread",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def gmail_get_thread(params: GetThreadInput, ctx: Context) -> str:
    """Retrieve an entire email conversation thread.
    
    This tool fetches all messages in a conversation thread, showing the complete back-and-forth.
    
    Args:
        params (GetThreadInput): Parameters containing:
            - thread_id (str): Gmail thread ID to retrieve
            - response_format (ResponseFormat): Output format (markdown or json)
    
    Returns:
        str: Complete thread with all messages in chronological order
    """
    try:
        thread = await make_gmail_request(ctx, "GET", f"/users/me/threads/{params.thread_id}")
        
        messages = thread.get("messages", [])
        
        if params.response_format == ResponseFormat.MARKDOWN:
            headers = {h["name"]: h["value"] for h in messages[0].get("payload", {}).get("headers", [])}
            result = f"# Thread: {headers.get('Subject', '(No Subject)')}\n\n"
            result += f"**Thread ID:** {params.thread_id}\n"
            result += f"**Messages in thread:** {len(messages)}\n\n"
            result += "---\n\n"
            
            for i, msg in enumerate(messages, 1):
                msg_headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                result += f"## Message {i} of {len(messages)}\n\n"
                result += f"**From:** {msg_headers.get('From', 'Unknown')}\n"
                result += f"**Date:** {msg_headers.get('Date', 'Unknown')}\n"
                result += f"**Message ID:** {msg['id']}\n\n"
                
                body = extract_email_body(msg)
                result += f"{body if body else '(No body content)'}\n\n"
                result += "---\n\n"
        
        else:
            result_data = {
                "thread_id": params.thread_id,
                "message_count": len(messages),
                "messages": [format_email_json(msg) for msg in messages]
            }
            result = json.dumps(result_data, indent=2)
        
        return truncate_response(result)
        
    except httpx.HTTPStatusError as e:
        return f"Error retrieving thread: {str(e)}. Please verify the thread ID is correct."
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# ATTACHMENT TOOLS
# ============================================================================

class GetAttachmentInput(BaseModel):
    """Input model for downloading and extracting text from attachments."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    message_id: str = Field(
        ...,
        description="The Gmail message ID containing the attachment",
        min_length=1
    )
    attachment_id: str = Field(
        ...,
        description="The attachment ID to download",
        min_length=1
    )
    mime_type: str = Field(
        ...,
        description="MIME type of the attachment (e.g., 'application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')"
    )


@mcp.tool(
    name="gmail_get_attachment_text",
    annotations={
        "title": "Extract Text from Gmail Attachment",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def gmail_get_attachment_text(params: GetAttachmentInput, ctx: Context) -> str:
    """Download a Gmail attachment and extract its text content.
    
    Supports text extraction from PDF, DOCX, and TXT files.
    
    Args:
        params (GetAttachmentInput): Parameters containing:
            - message_id (str): Message ID containing the attachment
            - attachment_id (str): Attachment ID to download
            - mime_type (str): MIME type of the attachment
    
    Returns:
        str: Extracted text content from the attachment
        
    Note:
        Requires PyPDF2 for PDF files and python-docx for DOCX files.
    """
    try:
        text = await download_attachment_text(
            ctx,
            params.message_id,
            params.attachment_id,
            params.mime_type
        )
        
        return truncate_response(text)
        
    except httpx.HTTPStatusError as e:
        return f"Error downloading attachment: {str(e)}. Please verify the message and attachment IDs are correct."
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# SEND EMAIL TOOLS
# ============================================================================

class SendEmailInput(BaseModel):
    """Input model for sending email messages."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    to: str = Field(
        ...,
        description="Recipient email address(es). Multiple addresses separated by commas.",
        min_length=1
    )
    subject: str = Field(
        ...,
        description="Email subject line",
        min_length=1,
        max_length=500
    )
    body: str = Field(
        ...,
        description="Email body content (plain text)",
        min_length=1
    )
    cc: Optional[str] = Field(
        default=None,
        description="CC recipient email address(es). Multiple addresses separated by commas."
    )
    bcc: Optional[str] = Field(
        default=None,
        description="BCC recipient email address(es). Multiple addresses separated by commas."
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Thread ID to reply to (makes this email part of an existing conversation)"
    )


@mcp.tool(
    name="gmail_send_message",
    annotations={
        "title": "Send Gmail Message",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def gmail_send_message(params: SendEmailInput, ctx: Context) -> str:
    """Send a new email message via Gmail.
    
    This tool composes and sends email messages with support for multiple recipients,
    CC, BCC, and threading (replies).
    
    Args:
        params (SendEmailInput): Email parameters containing:
            - to (str): Recipient email address(es)
            - subject (str): Email subject
            - body (str): Email body content
            - cc (Optional[str]): CC recipients
            - bcc (Optional[str]): BCC recipients
            - thread_id (Optional[str]): Thread ID to reply to
    
    Returns:
        str: Confirmation with sent message ID and details
    """
    try:
        # Construct RFC 2822 formatted message
        message_lines = [
            f"To: {params.to}",
            f"Subject: {params.subject}"
        ]
        
        if params.cc:
            message_lines.append(f"Cc: {params.cc}")
        
        if params.bcc:
            message_lines.append(f"Bcc: {params.bcc}")
        
        message_lines.append("")  # Blank line between headers and body
        message_lines.append(params.body)
        
        raw_message = "\n".join(message_lines)
        encoded_message = base64.urlsafe_b64encode(raw_message.encode("utf-8")).decode("utf-8")
        
        # Prepare request body
        request_body = {"raw": encoded_message}
        if params.thread_id:
            request_body["threadId"] = params.thread_id
        
        # Send message
        response = await make_gmail_request(
            ctx,
            "POST",
            "/users/me/messages/send",
            json_data=request_body
        )
        
        result = f"✅ Email sent successfully!\n\n"
        result += f"**Message ID:** {response['id']}\n"
        result += f"**Thread ID:** {response['threadId']}\n"
        result += f"**To:** {params.to}\n"
        result += f"**Subject:** {params.subject}\n"
        
        if params.thread_id:
            result += f"\n(Sent as reply in thread {params.thread_id})"
        
        return result
        
    except httpx.HTTPStatusError as e:
        return f"Error sending email: {str(e)}. Please check recipient addresses and try again."
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# DRAFT MANAGEMENT TOOLS
# ============================================================================

class CreateDraftInput(BaseModel):
    """Input model for creating email drafts."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    to: str = Field(
        ...,
        description="Recipient email address(es). Multiple addresses separated by commas.",
        min_length=1
    )
    subject: str = Field(
        ...,
        description="Email subject line",
        min_length=1,
        max_length=500
    )
    body: str = Field(
        ...,
        description="Email body content (plain text)",
        min_length=1
    )
    cc: Optional[str] = Field(
        default=None,
        description="CC recipient email address(es)"
    )


@mcp.tool(
    name="gmail_create_draft",
    annotations={
        "title": "Create Gmail Draft",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def gmail_create_draft(params: CreateDraftInput, ctx: Context) -> str:
    """Create a new email draft in Gmail.
    
    This tool creates a draft that can be edited, sent later, or deleted.
    
    Args:
        params (CreateDraftInput): Draft parameters containing:
            - to (str): Recipient email address(es)
            - subject (str): Email subject
            - body (str): Email body content
            - cc (Optional[str]): CC recipients
    
    Returns:
        str: Confirmation with draft ID and details
    """
    try:
        # Construct message
        message_lines = [
            f"To: {params.to}",
            f"Subject: {params.subject}"
        ]
        
        if params.cc:
            message_lines.append(f"Cc: {params.cc}")
        
        message_lines.append("")
        message_lines.append(params.body)
        
        raw_message = "\n".join(message_lines)
        encoded_message = base64.urlsafe_b64encode(raw_message.encode("utf-8")).decode("utf-8")
        
        # Create draft
        response = await make_gmail_request(
            ctx,
            "POST",
            "/users/me/drafts",
            json_data={
                "message": {"raw": encoded_message}
            }
        )
        
        result = f"📝 Draft created successfully!\n\n"
        result += f"**Draft ID:** {response['id']}\n"
        result += f"**Message ID:** {response['message']['id']}\n"
        result += f"**To:** {params.to}\n"
        result += f"**Subject:** {params.subject}\n"
        result += f"\nThe draft is saved and can be edited or sent later."
        
        return result
        
    except httpx.HTTPStatusError as e:
        return f"Error creating draft: {str(e)}. Please check your input and try again."
    except Exception as e:
        return f"Unexpected error: {str(e)}"


class ListDraftsInput(BaseModel):
    """Input model for listing drafts."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    max_results: int = Field(
        default=DEFAULT_MAX_RESULTS,
        description="Maximum number of drafts to return",
        ge=1,
        le=100
    )
    page_token: Optional[str] = Field(
        default=None,
        description="Token for pagination"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )


@mcp.tool(
    name="gmail_list_drafts",
    annotations={
        "title": "List Gmail Drafts",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def gmail_list_drafts(params: ListDraftsInput, ctx: Context) -> str:
    """List all email drafts in Gmail.
    
    Args:
        params (ListDraftsInput): Parameters containing:
            - max_results (int): Maximum results to return
            - page_token (Optional[str]): Pagination token
            - response_format (ResponseFormat): Output format
    
    Returns:
        str: List of drafts with details
    """
    try:
        list_params = {"maxResults": params.max_results}
        if params.page_token:
            list_params["pageToken"] = params.page_token
        
        response = await make_gmail_request(ctx, "GET", "/users/me/drafts", params=list_params)
        
        drafts = response.get("drafts", [])
        next_page_token = response.get("nextPageToken")
        
        if not drafts:
            return "No drafts found."
        
        # Fetch details for each draft
        detailed_drafts = []
        for draft in drafts:
            draft_detail = await make_gmail_request(ctx, "GET", f"/users/me/drafts/{draft['id']}")
            detailed_drafts.append(draft_detail)
        
        if params.response_format == ResponseFormat.MARKDOWN:
            result = f"# Gmail Drafts\n\n**Count:** {len(drafts)}\n\n"
            
            for i, draft in enumerate(detailed_drafts, 1):
                msg = draft["message"]
                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                
                result += f"## {i}. {headers.get('Subject', '(No Subject)')}\n"
                result += f"- **Draft ID:** {draft['id']}\n"
                result += f"- **To:** {headers.get('To', 'Unknown')}\n"
                result += f"- **Snippet:** {msg.get('snippet', '')}\n\n"
            
            if next_page_token:
                result += f"\n**More drafts available.** Use page_token='{next_page_token}' to get more.\n"
        else:
            result_data = {
                "count": len(drafts),
                "drafts": [
                    {
                        "draft_id": d["id"],
                        "message": format_email_json(d["message"])
                    }
                    for d in detailed_drafts
                ],
                "has_more": bool(next_page_token),
                "next_page_token": next_page_token
            }
            result = json.dumps(result_data, indent=2)
        
        return truncate_response(result)
        
    except httpx.HTTPStatusError as e:
        return f"Error listing drafts: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


class DeleteDraftInput(BaseModel):
    """Input model for deleting drafts."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    draft_id: str = Field(
        ...,
        description="The draft ID to delete",
        min_length=1
    )


@mcp.tool(
    name="gmail_delete_draft",
    annotations={
        "title": "Delete Gmail Draft",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def gmail_delete_draft(params: DeleteDraftInput, ctx: Context) -> str:
    """Delete an email draft from Gmail.
    
    Args:
        params (DeleteDraftInput): Parameters containing:
            - draft_id (str): Draft ID to delete
    
    Returns:
        str: Confirmation of deletion
    """
    try:
        await make_gmail_request(ctx, "DELETE", f"/users/me/drafts/{params.draft_id}")
        return f"✅ Draft {params.draft_id} deleted successfully."
        
    except httpx.HTTPStatusError as e:
        return f"Error deleting draft: {str(e)}. Please verify the draft ID is correct."
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# LABEL MANAGEMENT TOOLS
# ============================================================================

class ListLabelsInput(BaseModel):
    """Input model for listing labels."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )


@mcp.tool(
    name="gmail_list_labels",
    annotations={
        "title": "List Gmail Labels",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def gmail_list_labels(params: ListLabelsInput, ctx: Context) -> str:
    """List all labels in Gmail account.
    
    Args:
        params (ListLabelsInput): Parameters containing:
            - response_format (ResponseFormat): Output format
    
    Returns:
        str: List of all labels with IDs and types
    """
    try:
        response = await make_gmail_request(ctx, "GET", "/users/me/labels")
        labels = response.get("labels", [])
        
        if params.response_format == ResponseFormat.MARKDOWN:
            result = f"# Gmail Labels\n\n**Total:** {len(labels)}\n\n"
            
            # Group by type
            system_labels = [l for l in labels if l.get("type") == "system"]
            user_labels = [l for l in labels if l.get("type") == "user"]
            
            if system_labels:
                result += "## System Labels\n\n"
                for label in system_labels:
                    result += f"- **{label['name']}** (ID: {label['id']})\n"
                result += "\n"
            
            if user_labels:
                result += "## User Labels\n\n"
                for label in user_labels:
                    result += f"- **{label['name']}** (ID: {label['id']})\n"
        else:
            result = json.dumps({"labels": labels}, indent=2)
        
        return result
        
    except httpx.HTTPStatusError as e:
        return f"Error listing labels: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


class CreateLabelInput(BaseModel):
    """Input model for creating labels."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    name: str = Field(
        ...,
        description="Label name",
        min_length=1,
        max_length=100
    )
    label_list_visibility: Literal["labelShow", "labelShowIfUnread", "labelHide"] = Field(
        default="labelShow",
        description="Visibility in label list"
    )
    message_list_visibility: Literal["show", "hide"] = Field(
        default="show",
        description="Visibility in message list"
    )


@mcp.tool(
    name="gmail_create_label",
    annotations={
        "title": "Create Gmail Label",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def gmail_create_label(params: CreateLabelInput, ctx: Context) -> str:
    """Create a new label in Gmail.
    
    Args:
        params (CreateLabelInput): Label parameters containing:
            - name (str): Label name
            - label_list_visibility (str): Show behavior in label list
            - message_list_visibility (str): Show behavior in message list
    
    Returns:
        str: Confirmation with new label ID
    """
    try:
        response = await make_gmail_request(
            ctx,
            "POST",
            "/users/me/labels",
            json_data={
                "name": params.name,
                "labelListVisibility": params.label_list_visibility,
                "messageListVisibility": params.message_list_visibility
            }
        )
        
        result = f"✅ Label created successfully!\n\n"
        result += f"**Label Name:** {response['name']}\n"
        result += f"**Label ID:** {response['id']}\n"
        
        return result
        
    except httpx.HTTPStatusError as e:
        return f"Error creating label: {str(e)}. The label name may already exist."
    except Exception as e:
        return f"Unexpected error: {str(e)}"


class ModifyLabelsInput(BaseModel):
    """Input model for modifying message labels."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    message_id: str = Field(
        ...,
        description="Message ID to modify",
        min_length=1
    )
    add_label_ids: Optional[List[str]] = Field(
        default=None,
        description="List of label IDs to add to the message"
    )
    remove_label_ids: Optional[List[str]] = Field(
        default=None,
        description="List of label IDs to remove from the message"
    )


@mcp.tool(
    name="gmail_modify_message_labels",
    annotations={
        "title": "Modify Gmail Message Labels",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def gmail_modify_message_labels(params: ModifyLabelsInput, ctx: Context) -> str:
    """Add or remove labels from a Gmail message.
    
    Args:
        params (ModifyLabelsInput): Parameters containing:
            - message_id (str): Message ID to modify
            - add_label_ids (Optional[List[str]]): Labels to add
            - remove_label_ids (Optional[List[str]]): Labels to remove
    
    Returns:
        str: Confirmation of label changes
    """
    try:
        request_body = {}
        if params.add_label_ids:
            request_body["addLabelIds"] = params.add_label_ids
        if params.remove_label_ids:
            request_body["removeLabelIds"] = params.remove_label_ids
        
        response = await make_gmail_request(
            ctx,
            "POST",
            f"/users/me/messages/{params.message_id}/modify",
            json_data=request_body
        )
        
        result = f"✅ Labels modified successfully!\n\n"
        result += f"**Message ID:** {params.message_id}\n"
        result += f"**Current Labels:** {', '.join(response.get('labelIds', []))}\n"
        
        return result
        
    except httpx.HTTPStatusError as e:
        return f"Error modifying labels: {str(e)}. Please verify message and label IDs."
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# READ/UNREAD MANAGEMENT
# ============================================================================

class MarkReadInput(BaseModel):
    """Input model for marking messages as read/unread."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    message_id: str = Field(
        ...,
        description="Message ID to mark as read or unread",
        min_length=1
    )
    mark_as_read: bool = Field(
        ...,
        description="True to mark as read, False to mark as unread"
    )


@mcp.tool(
    name="gmail_mark_message_read",
    annotations={
        "title": "Mark Gmail Message Read/Unread",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def gmail_mark_message_read(params: MarkReadInput, ctx: Context) -> str:
    """Mark a Gmail message as read or unread.
    
    Args:
        params (MarkReadInput): Parameters containing:
            - message_id (str): Message ID to modify
            - mark_as_read (bool): True for read, False for unread
    
    Returns:
        str: Confirmation of status change
    """
    try:
        if params.mark_as_read:
            # Remove UNREAD label
            request_body = {"removeLabelIds": ["UNREAD"]}
            action = "read"
        else:
            # Add UNREAD label
            request_body = {"addLabelIds": ["UNREAD"]}
            action = "unread"
        
        await make_gmail_request(
            ctx,
            "POST",
            f"/users/me/messages/{params.message_id}/modify",
            json_data=request_body
        )
        
        return f"✅ Message {params.message_id} marked as {action}."
        
    except httpx.HTTPStatusError as e:
        return f"Error marking message: {str(e)}. Please verify the message ID is correct."
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# SERVER ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    mcp.run()
