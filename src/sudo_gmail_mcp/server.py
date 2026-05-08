from __future__ import annotations

from typing import Any

from googleapiclient.errors import HttpError
from mcp.server.fastmcp import FastMCP

from sudo_gmail_mcp.gmail_client import (
    AttachmentError,
    AttachmentInput,
    GmailClient,
    GmailConfigError,
    format_http_error,
)

server = FastMCP("sudo-gmail-mcp")
client = GmailClient()


@server.tool()
def create_gmail_draft(
    to: list[str],
    subject: str,
    body_text: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    body_html: str | None = None,
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    """Create a Gmail draft with optional CC, BCC, HTML body, and file attachments."""
    try:
        draft = client.create_draft(
            to=to,
            subject=subject,
            body_text=body_text,
            cc=cc,
            bcc=bcc,
            body_html=body_html,
            attachments=[AttachmentInput(path=path) for path in attachments or []],
        )
        return {
            "draftId": draft.get("id"),
            "messageId": draft.get("message", {}).get("id"),
        }
    except (AttachmentError, GmailConfigError, ValueError) as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


@server.tool()
def update_gmail_draft(
    draft_id: str,
    to: list[str],
    subject: str,
    body_text: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    body_html: str | None = None,
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    """Update an existing Gmail draft by its draft ID."""
    try:
        draft = client.update_draft(
            draft_id=draft_id,
            to=to,
            subject=subject,
            body_text=body_text,
            cc=cc,
            bcc=bcc,
            body_html=body_html,
            attachments=[AttachmentInput(path=path) for path in attachments or []],
        )
        return {
            "draftId": draft.get("id"),
            "messageId": draft.get("message", {}).get("id"),
        }
    except (AttachmentError, GmailConfigError, ValueError) as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


@server.tool()
def get_gmail_draft(draft_id: str) -> dict[str, Any]:
    """Get one Gmail draft with decoded text and HTML bodies when available."""
    try:
        return client.get_draft(draft_id)
    except GmailConfigError as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


@server.tool()
def send_gmail_draft(draft_id: str) -> dict[str, Any]:
    """Send an existing Gmail draft by its draft ID."""
    try:
        message = client.send_draft(draft_id)
        return {
            "messageId": message.get("id"),
            "threadId": message.get("threadId"),
            "labelIds": message.get("labelIds", []),
        }
    except GmailConfigError as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


@server.tool()
def reply_to_gmail_message(
    message_id: str,
    body_text: str,
    body_html: str | None = None,
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    """Reply to a Gmail message."""
    try:
        message = client.reply_to_message(
            message_id=message_id,
            body_text=body_text,
            body_html=body_html,
            attachments=[AttachmentInput(path=path) for path in attachments or []],
            reply_all=False,
        )
        return {
            "messageId": message.get("id"),
            "threadId": message.get("threadId"),
            "labelIds": message.get("labelIds", []),
        }
    except (AttachmentError, GmailConfigError, ValueError) as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


@server.tool()
def reply_all_gmail_message(
    message_id: str,
    body_text: str,
    body_html: str | None = None,
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    """Reply-all to a Gmail message."""
    try:
        message = client.reply_to_message(
            message_id=message_id,
            body_text=body_text,
            body_html=body_html,
            attachments=[AttachmentInput(path=path) for path in attachments or []],
            reply_all=True,
        )
        return {
            "messageId": message.get("id"),
            "threadId": message.get("threadId"),
            "labelIds": message.get("labelIds", []),
        }
    except (AttachmentError, GmailConfigError, ValueError) as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


@server.tool()
def forward_gmail_message(
    message_id: str,
    to: list[str],
    body_text: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    body_html: str | None = None,
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    """Forward a Gmail message to new recipients."""
    try:
        message = client.forward_message(
            message_id=message_id,
            to=to,
            body_text=body_text,
            cc=cc,
            bcc=bcc,
            body_html=body_html,
            attachments=[AttachmentInput(path=path) for path in attachments or []],
        )
        return {
            "messageId": message.get("id"),
            "threadId": message.get("threadId"),
            "labelIds": message.get("labelIds", []),
        }
    except (AttachmentError, GmailConfigError, ValueError) as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


@server.tool()
def send_gmail_message(
    to: list[str],
    subject: str,
    body_text: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    body_html: str | None = None,
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    """Send a Gmail message with optional CC, BCC, HTML body, and file attachments."""
    try:
        message = client.send_message(
            to=to,
            subject=subject,
            body_text=body_text,
            cc=cc,
            bcc=bcc,
            body_html=body_html,
            attachments=[AttachmentInput(path=path) for path in attachments or []],
        )
        return {
            "messageId": message.get("id"),
            "threadId": message.get("threadId"),
            "labelIds": message.get("labelIds", []),
        }
    except (AttachmentError, GmailConfigError, ValueError) as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


@server.tool()
def list_gmail_labels() -> dict[str, Any]:
    """List Gmail labels."""
    try:
        labels = client.list_labels()
        return {"labels": labels, "count": len(labels)}
    except GmailConfigError as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


@server.tool()
def mark_gmail_message_read(message_id: str) -> dict[str, Any]:
    """Mark a Gmail message as read."""
    try:
        return client.mark_message_read(message_id)
    except GmailConfigError as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


@server.tool()
def mark_gmail_message_unread(message_id: str) -> dict[str, Any]:
    """Mark a Gmail message as unread."""
    try:
        return client.mark_message_unread(message_id)
    except GmailConfigError as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


@server.tool()
def list_gmail_messages(
    query: str | None = None,
    label_ids: list[str] | None = None,
    max_results: int = 10,
) -> dict[str, Any]:
    """List Gmail messages, optionally filtered by Gmail search query and labels."""
    try:
        messages = client.list_messages(
            query=query,
            label_ids=label_ids,
            max_results=max_results,
        )
        return {"messages": messages, "count": len(messages)}
    except GmailConfigError as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


@server.tool()
def get_gmail_message(message_id: str) -> dict[str, Any]:
    """Get one Gmail message with decoded text and HTML bodies when available."""
    try:
        return client.get_message(message_id)
    except GmailConfigError as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


@server.tool()
def search_gmail_messages(
    raw_query: str | None = None,
    subject_keywords: list[str] | None = None,
    body_keywords: list[str] | None = None,
    from_addresses: list[str] | None = None,
    company_domains: list[str] | None = None,
    has_attachments: bool | None = None,
    newer_than_days: int | None = None,
    label_ids: list[str] | None = None,
    max_results: int = 10,
) -> dict[str, Any]:
    """Search Gmail using either a raw Gmail query or structured filter fields."""
    try:
        return client.search_messages(
            raw_query=raw_query,
            subject_keywords=subject_keywords,
            body_keywords=body_keywords,
            from_addresses=from_addresses,
            company_domains=company_domains,
            has_attachments=has_attachments,
            newer_than_days=newer_than_days,
            label_ids=label_ids,
            max_results=max_results,
        )
    except (GmailConfigError, ValueError) as error:
        raise RuntimeError(str(error)) from error
    except HttpError as error:
        raise RuntimeError(format_http_error(error)) from error


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
