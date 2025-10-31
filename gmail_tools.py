"""
title: Gmail Tools
author: Gmail MCP Server
version: 1.0.0
description: AI-powered Gmail management tools via MCP server
required_open_webui_version: 0.3.9
"""

from pydantic import BaseModel, Field
import requests
from typing import Optional


class Tools:
    class Valves(BaseModel):
        bridge_url: str = Field(
            default="http://localhost:3002",
            description="URL of the Gmail MCP bridge server"
        )
        timeout: int = Field(
            default=300,
            description="Request timeout in seconds"
        )

    def __init__(self):
        self.valves = self.Valves()

    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool via the Gmail MCP bridge server"""
        try:
            url = f"{self.valves.bridge_url}/v1/tools/execute"
            payload = {
                "tool_name": tool_name,
                "arguments": arguments,
            }
            r = requests.post(url, json=payload, timeout=self.valves.timeout)
            if r.status_code == 200:
                result = r.json()
                return result.get("result", {}).get("output", "No output")
            return f"HTTP Error: {r.status_code}\nResponse: {r.text}"
        except requests.exceptions.Timeout:
            return f"Request timed out after {self.valves.timeout} seconds."
        except requests.exceptions.ConnectionError:
            return f"Cannot connect to Gmail MCP bridge at {self.valves.bridge_url}"
        except Exception as e:
            return f"Error: {str(e)}"

    # ============================================================================
    # SEARCH & READ TOOLS
    # ============================================================================

    def search_emails(
        self,
        query: str,
        max_results: int = 20,
        response_format: str = "markdown"
    ) -> str:
        """
        Search Gmail messages using Gmail search operators.

        Args:
            query: Gmail search query (e.g., 'from:john@example.com', 'is:unread', 'after:2024/01/01')
            max_results: Maximum number of results (1-100, default: 20)
            response_format: Output format ('markdown' or 'json')

        Examples:
            - search_emails("from:john@example.com")
            - search_emails("is:unread after:2024/10/01")
            - search_emails("subject:meeting has:attachment")
        """
        return self._execute_tool("gmail_search_messages", {
            "query": query,
            "max_results": max_results,
            "response_format": response_format
        })

    def get_email(
        self,
        message_id: str,
        response_format: str = "markdown"
    ) -> str:
        """
        Get the full content of a specific email message.

        Args:
            message_id: The Gmail message ID
            response_format: Output format ('markdown' or 'json')
        """
        return self._execute_tool("gmail_get_message", {
            "message_id": message_id,
            "response_format": response_format,
            "include_attachments_info": True
        })

    def get_thread(
        self,
        thread_id: str,
        response_format: str = "markdown"
    ) -> str:
        """
        Get an entire email conversation thread.

        Args:
            thread_id: The Gmail thread ID
            response_format: Output format ('markdown' or 'json')
        """
        return self._execute_tool("gmail_get_thread", {
            "thread_id": thread_id,
            "response_format": response_format
        })

    def get_attachment_text(
        self,
        message_id: str,
        attachment_id: str,
        mime_type: str
    ) -> str:
        """
        Download and extract text from an email attachment.

        Args:
            message_id: The Gmail message ID containing the attachment
            attachment_id: The attachment ID
            mime_type: MIME type (e.g., 'application/pdf', 'text/plain')
        """
        return self._execute_tool("gmail_get_attachment_text", {
            "message_id": message_id,
            "attachment_id": attachment_id,
            "mime_type": mime_type
        })

    # ============================================================================
    # SUMMARIZATION TOOLS
    # ============================================================================

    def summarize_emails(
        self,
        query: str,
        max_results: int = 10,
        include_body: bool = True
    ) -> str:
        """
        Fetch and summarize multiple emails based on a search query.

        Args:
            query: Gmail search query to find emails to summarize
            max_results: Maximum number of emails to include (1-50, default: 10)
            include_body: Include full email body for detailed summaries

        Examples:
            - summarize_emails("is:unread")
            - summarize_emails("from:john@example.com after:2024/10/01")
            - summarize_emails("subject:project after:2024/10/20", max_results=5)
        """
        return self._execute_tool("gmail_summarize_emails", {
            "query": query,
            "max_results": max_results,
            "include_body": include_body
        })

    # ============================================================================
    # COMPOSE & SEND TOOLS
    # ============================================================================

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> str:
        """
        Send a new email message.

        Args:
            to: Recipient email address(es), comma-separated
            subject: Email subject
            body: Email body (plain text)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            thread_id: Thread ID to reply to (optional)
        """
        args = {
            "to": to,
            "subject": subject,
            "body": body
        }
        if cc:
            args["cc"] = cc
        if bcc:
            args["bcc"] = bcc
        if thread_id:
            args["thread_id"] = thread_id

        return self._execute_tool("gmail_send_message", args)

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None
    ) -> str:
        """
        Create a new email draft.

        Args:
            to: Recipient email address(es)
            subject: Email subject
            body: Email body (plain text)
            cc: CC recipients (optional)
        """
        args = {
            "to": to,
            "subject": subject,
            "body": body
        }
        if cc:
            args["cc"] = cc

        return self._execute_tool("gmail_create_draft", args)

    def list_drafts(
        self,
        max_results: int = 20,
        response_format: str = "markdown"
    ) -> str:
        """
        List all email drafts.

        Args:
            max_results: Maximum number of drafts to return (1-100)
            response_format: Output format ('markdown' or 'json')
        """
        return self._execute_tool("gmail_list_drafts", {
            "max_results": max_results,
            "response_format": response_format
        })

    def delete_draft(self, draft_id: str) -> str:
        """
        Delete an email draft.

        Args:
            draft_id: The draft ID to delete
        """
        return self._execute_tool("gmail_delete_draft", {
            "draft_id": draft_id
        })

    # ============================================================================
    # ORGANIZATION TOOLS
    # ============================================================================

    def list_labels(self, response_format: str = "markdown") -> str:
        """
        List all Gmail labels.

        Args:
            response_format: Output format ('markdown' or 'json')
        """
        return self._execute_tool("gmail_list_labels", {
            "response_format": response_format
        })

    def create_label(
        self,
        name: str,
        label_list_visibility: str = "labelShow",
        message_list_visibility: str = "show"
    ) -> str:
        """
        Create a new Gmail label.

        Args:
            name: Label name
            label_list_visibility: 'labelShow', 'labelShowIfUnread', or 'labelHide'
            message_list_visibility: 'show' or 'hide'
        """
        return self._execute_tool("gmail_create_label", {
            "name": name,
            "label_list_visibility": label_list_visibility,
            "message_list_visibility": message_list_visibility
        })

    def modify_labels(
        self,
        message_id: str,
        add_labels: Optional[list] = None,
        remove_labels: Optional[list] = None
    ) -> str:
        """
        Add or remove labels from a message.

        Args:
            message_id: The message ID to modify
            add_labels: List of label IDs to add
            remove_labels: List of label IDs to remove
        """
        args = {"message_id": message_id}
        if add_labels:
            args["add_label_ids"] = add_labels
        if remove_labels:
            args["remove_label_ids"] = remove_labels

        return self._execute_tool("gmail_modify_message_labels", args)

    def mark_read(self, message_id: str, mark_as_read: bool = True) -> str:
        """
        Mark a message as read or unread.

        Args:
            message_id: The message ID
            mark_as_read: True to mark as read, False to mark as unread
        """
        return self._execute_tool("gmail_mark_message_read", {
            "message_id": message_id,
            "mark_as_read": mark_as_read
        })
