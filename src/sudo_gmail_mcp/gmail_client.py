from __future__ import annotations

import base64
import ipaddress
import mimetypes
import os
from dataclasses import dataclass
from email import policy
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from requests import Response
from requests.exceptions import RequestException

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
MAX_REMOTE_ATTACHMENT_BYTES = 10 * 1024 * 1024
REMOTE_ATTACHMENT_TIMEOUT_SECONDS = 15
BLOCKED_ATTACHMENT_SCHEMES = {"http", "file"}
BLOCKED_ATTACHMENT_HOSTS = {"localhost", "127.0.0.1", "::1"}
UNREAD_LABEL = "UNREAD"
INBOX_LABEL = "INBOX"
TRASH_LABEL = "TRASH"
SENT_LABEL = "SENT"
DRAFT_LABEL = "DRAFT"


@dataclass(slots=True)
class AttachmentInput:
    path: str
    mime_type: str | None = None


@dataclass(slots=True)
class ResolvedAttachment:
    content: bytes
    filename: str
    mime_type: str | None = None


class GmailConfigError(RuntimeError):
    pass


class AttachmentError(RuntimeError):
    pass


class RemoteAttachmentError(AttachmentError):
    pass


class UnsafeAttachmentURLError(RemoteAttachmentError):
    pass


class AttachmentTooLargeError(RemoteAttachmentError):
    pass


class AttachmentDownloadError(RemoteAttachmentError):
    pass


class UnsupportedAttachmentSchemeError(AttachmentError):
    pass


class LocalAttachmentNotFoundError(AttachmentError):
    pass


class InvalidAttachmentURLError(AttachmentError):
    pass


class InvalidAttachmentFilenameError(AttachmentError):
    pass


class RemoteAttachmentSession:
    def get(self, url: str, *, stream: bool, timeout: int) -> Response:
        return requests.get(url, stream=stream, timeout=timeout)


DEFAULT_REMOTE_ATTACHMENT_SESSION = RemoteAttachmentSession()


class GmailClient:
    def __init__(self) -> None:
        self.credentials_path = Path(
            os.environ.get("GMAIL_MCP_CREDENTIALS_FILE", "credentials.json")
        ).expanduser()
        self.token_path = Path(
            os.environ.get("GMAIL_MCP_TOKEN_FILE", ".sudo-gmail-mcp/token.json")
        ).expanduser()
        self._service = None

    def get_service(self):
        if self._service is None:
            creds = self._load_credentials()
            self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return self._service

    def _load_credentials(self) -> Credentials:
        creds: Credentials | None = None

        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._write_token(creds)
            return creds

        if not self.credentials_path.exists():
            raise GmailConfigError(
                "Missing Gmail OAuth client credentials. Set GMAIL_MCP_CREDENTIALS_FILE or place credentials.json in the project root."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.credentials_path), SCOPES
        )
        creds = flow.run_local_server(port=0)
        self._write_token(creds)
        return creds

    def _write_token(self, creds: Credentials) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(creds.to_json(), encoding="utf-8")

    def create_draft(
        self,
        *,
        to: list[str],
        subject: str,
        body_text: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        body_html: str | None = None,
        attachments: list[AttachmentInput] | None = None,
    ) -> dict[str, Any]:
        body = build_gmail_message_request(
            to=to,
            subject=subject,
            body_text=body_text,
            cc=cc or [],
            bcc=bcc or [],
            body_html=body_html,
            attachments=attachments or [],
        )
        return (
            self.get_service()
            .users()
            .drafts()
            .create(userId="me", body={"message": body})
            .execute()
        )

    def update_draft(
        self,
        *,
        draft_id: str,
        to: list[str],
        subject: str,
        body_text: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        body_html: str | None = None,
        attachments: list[AttachmentInput] | None = None,
    ) -> dict[str, Any]:
        body = build_gmail_message_request(
            to=to,
            subject=subject,
            body_text=body_text,
            cc=cc or [],
            bcc=bcc or [],
            body_html=body_html,
            attachments=attachments or [],
        )
        return (
            self.get_service()
            .users()
            .drafts()
            .update(userId="me", id=draft_id, body={"id": draft_id, "message": body})
            .execute()
        )

    def get_draft(self, draft_id: str) -> dict[str, Any]:
        draft = (
            self.get_service()
            .users()
            .drafts()
            .get(userId="me", id=draft_id, format="full")
            .execute()
        )
        return format_draft(draft)

    def send_draft(self, draft_id: str) -> dict[str, Any]:
        return (
            self.get_service()
            .users()
            .drafts()
            .send(userId="me", body={"id": draft_id})
            .execute()
        )

    def send_message(
        self,
        *,
        to: list[str],
        subject: str,
        body_text: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        body_html: str | None = None,
        attachments: list[AttachmentInput] | None = None,
    ) -> dict[str, Any]:
        body = build_gmail_message_request(
            to=to,
            subject=subject,
            body_text=body_text,
            cc=cc or [],
            bcc=bcc or [],
            body_html=body_html,
            attachments=attachments or [],
        )
        return (
            self.get_service()
            .users()
            .messages()
            .send(userId="me", body=body)
            .execute()
        )

    def reply_to_message(
        self,
        *,
        message_id: str,
        body_text: str,
        body_html: str | None = None,
        attachments: list[AttachmentInput] | None = None,
        reply_all: bool = False,
    ) -> dict[str, Any]:
        original = self._get_message_raw(message_id)
        headers = get_headers_map(original)
        recipients = build_reply_recipients(headers, reply_all=reply_all)
        subject = build_reply_subject(headers.get("Subject"))
        references = build_references(headers)

        body = build_gmail_message_request(
            to=recipients["to"],
            subject=subject,
            body_text=body_text,
            cc=recipients["cc"],
            bcc=[],
            body_html=body_html,
            attachments=attachments or [],
            in_reply_to=headers.get("Message-ID"),
            references=references,
            thread_id=original.get("threadId"),
        )
        return (
            self.get_service()
            .users()
            .messages()
            .send(userId="me", body=body)
            .execute()
        )

    def forward_message(
        self,
        *,
        message_id: str,
        to: list[str],
        body_text: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        body_html: str | None = None,
        attachments: list[AttachmentInput] | None = None,
    ) -> dict[str, Any]:
        original = self._get_message_raw(message_id)
        headers = get_headers_map(original)
        forward_body = build_forward_body(
            body_text=body_text,
            original_message=format_message(original),
        )
        subject = build_forward_subject(headers.get("Subject"))
        body = build_gmail_message_request(
            to=to,
            subject=subject,
            body_text=forward_body,
            cc=cc or [],
            bcc=bcc or [],
            body_html=body_html,
            attachments=attachments or [],
        )
        return (
            self.get_service()
            .users()
            .messages()
            .send(userId="me", body=body)
            .execute()
        )

    def list_labels(self) -> list[dict[str, Any]]:
        response = self.get_service().users().labels().list(userId="me").execute()
        return response.get("labels", [])

    def mark_message_read(self, message_id: str) -> dict[str, Any]:
        response = (
            self.get_service()
            .users()
            .messages()
            .modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": [UNREAD_LABEL]},
            )
            .execute()
        )
        return summarize_modified_message(response)

    def mark_message_unread(self, message_id: str) -> dict[str, Any]:
        response = (
            self.get_service()
            .users()
            .messages()
            .modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": [UNREAD_LABEL]},
            )
            .execute()
        )
        return summarize_modified_message(response)

    def list_messages(
        self,
        *,
        query: str | None = None,
        label_ids: list[str] | None = None,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        response = (
            self.get_service()
            .users()
            .messages()
            .list(
                userId="me",
                q=query,
                labelIds=label_ids or None,
                maxResults=max(1, min(max_results, 100)),
            )
            .execute()
        )
        messages = response.get("messages", [])
        return [self.get_message_summary(message["id"]) for message in messages]

    def get_message_summary(self, message_id: str) -> dict[str, Any]:
        message = self.get_message(message_id)
        return {
            "id": message["id"],
            "threadId": message.get("threadId"),
            "labelIds": message.get("labelIds", []),
            "snippet": message.get("snippet", ""),
            "internalDate": message.get("internalDate"),
            "headers": {
                "from": message["headers"].get("From"),
                "to": message["headers"].get("To"),
                "subject": message["headers"].get("Subject"),
                "date": message["headers"].get("Date"),
            },
        }

    def get_message(self, message_id: str) -> dict[str, Any]:
        return format_message(self._get_message_raw(message_id))

    def _get_message_raw(self, message_id: str) -> dict[str, Any]:
        return (
            self.get_service()
            .users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

    def search_messages(
        self,
        *,
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
        query = build_gmail_query(
            raw_query=raw_query,
            subject_keywords=subject_keywords or [],
            body_keywords=body_keywords or [],
            from_addresses=from_addresses or [],
            company_domains=company_domains or [],
            has_attachments=has_attachments,
            newer_than_days=newer_than_days,
        )
        results = self.list_messages(
            query=query,
            label_ids=label_ids,
            max_results=max_results,
        )
        return {"query": query, "messages": results}


def parse_email_addresses(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def build_gmail_message_request(
    *,
    to: list[str],
    subject: str,
    body_text: str,
    cc: list[str],
    bcc: list[str],
    body_html: str | None,
    attachments: list[AttachmentInput],
    in_reply_to: str | None = None,
    references: str | None = None,
    thread_id: str | None = None,
) -> dict[str, str]:
    message = build_mime_message(
        to=to,
        subject=subject,
        body_text=body_text,
        cc=cc,
        bcc=bcc,
        body_html=body_html,
        attachments=attachments,
        in_reply_to=in_reply_to,
        references=references,
    )
    body = {"raw": encode_message(message)}
    if thread_id:
        body["threadId"] = thread_id
    return body


def build_mime_message(
    *,
    to: list[str],
    subject: str,
    body_text: str,
    cc: list[str],
    bcc: list[str],
    body_html: str | None,
    attachments: list[AttachmentInput],
    in_reply_to: str | None = None,
    references: str | None = None,
) -> EmailMessage:
    if not to:
        raise ValueError("At least one recipient is required.")

    message = EmailMessage(policy=policy.SMTP)
    message["To"] = ", ".join(parse_email_addresses(to))
    if cc:
        message["Cc"] = ", ".join(parse_email_addresses(cc))
    if bcc:
        message["Bcc"] = ", ".join(parse_email_addresses(bcc))
    message["Subject"] = subject
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
    if references:
        message["References"] = references
    message.set_content(body_text)

    if body_html:
        message.add_alternative(body_html, subtype="html")

    for attachment in attachments:
        add_attachment(message, attachment)

    return message


def add_attachment(message: EmailMessage, attachment: AttachmentInput) -> None:
    resolved = resolve_attachment_payload(attachment)
    mime_type = attachment.mime_type or resolved.mime_type
    maintype, subtype = split_mime_type(mime_type)
    message.add_attachment(
        resolved.content,
        maintype=maintype,
        subtype=subtype,
        filename=resolved.filename,
    )


def resolve_attachment_payload(
    attachment: AttachmentInput,
    *,
    session: RemoteAttachmentSession | None = None,
) -> ResolvedAttachment:
    source = classify_attachment_source(attachment.path)
    if source == "local":
        return read_local_attachment(attachment)
    return download_remote_attachment(attachment, session=session)


def classify_attachment_source(value: str) -> str:
    stripped = value.strip()
    parsed = urlparse(stripped)
    if parsed.scheme == "https":
        return "url"
    if len(parsed.scheme) == 1 and len(stripped) >= 3 and stripped[1:3] in {":/", ":\\"}:
        return "local"
    if parsed.scheme:
        return "url"
    return "local"


def read_local_attachment(attachment: AttachmentInput) -> ResolvedAttachment:
    path = Path(attachment.path).expanduser()
    if not path.exists() or not path.is_file():
        raise LocalAttachmentNotFoundError(f"Attachment not found: {path}")

    mime_type = attachment.mime_type or mimetypes.guess_type(path.name)[0]
    return ResolvedAttachment(
        content=path.read_bytes(),
        filename=path.name,
        mime_type=mime_type,
    )


def download_remote_attachment(
    attachment: AttachmentInput,
    *,
    session: RemoteAttachmentSession | None = None,
) -> ResolvedAttachment:
    parsed = urlparse(attachment.path.strip())
    validate_remote_attachment_url(parsed)
    active_session = session or DEFAULT_REMOTE_ATTACHMENT_SESSION

    try:
        response = active_session.get(
            attachment.path,
            stream=True,
            timeout=REMOTE_ATTACHMENT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        try:
            filename = choose_remote_attachment_filename(response, attachment.path)
            content = read_remote_attachment_bytes(response)
            mime_type = attachment.mime_type or get_response_content_type(response)
            if not mime_type:
                mime_type = mimetypes.guess_type(filename)[0]
            return ResolvedAttachment(
                content=content,
                filename=filename,
                mime_type=mime_type,
            )
        finally:
            response.close()
    except RequestException as error:
        raise AttachmentDownloadError(
            f"Failed to download attachment URL: {attachment.path}"
        ) from error


def validate_remote_attachment_url(parsed) -> None:
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower() if parsed.hostname else None

    if scheme in BLOCKED_ATTACHMENT_SCHEMES:
        raise UnsupportedAttachmentSchemeError(
            f"Unsupported attachment URL scheme: {scheme}"
        )
    if scheme != "https":
        raise UnsupportedAttachmentSchemeError(
            "Only local file paths and HTTPS attachment URLs are supported."
        )
    if not hostname:
        raise InvalidAttachmentURLError("Attachment URL must include a hostname.")
    if hostname in BLOCKED_ATTACHMENT_HOSTS or is_blocked_ip_address(hostname):
        raise UnsafeAttachmentURLError(
            "Attachment URL targets a blocked host or private network address."
        )


def is_blocked_ip_address(hostname: str) -> bool:
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def choose_remote_attachment_filename(response: Response, url: str) -> str:
    content_disposition = response.headers.get("Content-Disposition")
    filename = extract_filename_from_content_disposition(content_disposition)
    if filename:
        return sanitize_attachment_filename(filename)

    path_name = Path(unquote(urlparse(url).path)).name
    if path_name:
        return sanitize_attachment_filename(path_name)

    return "attachment"


def extract_filename_from_content_disposition(value: str | None) -> str | None:
    if not value:
        return None
    for part in value.split(";"):
        key, separator, raw_value = part.strip().partition("=")
        if separator == "=" and key.lower() == "filename":
            filename = raw_value.strip().strip('"')
            if filename:
                return filename
    return None


def sanitize_attachment_filename(value: str) -> str:
    cleaned = value.replace("\\", "_").replace("/", "_").strip().strip(".")
    cleaned = "".join(
        character for character in cleaned if character >= " " and character != "\x7f"
    )
    if not cleaned:
        raise InvalidAttachmentFilenameError(
            "Attachment filename could not be derived safely."
        )
    return cleaned


def read_remote_attachment_bytes(response: Response) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > MAX_REMOTE_ATTACHMENT_BYTES:
        raise AttachmentTooLargeError(
            f"Attachment URL exceeds the maximum allowed size of {MAX_REMOTE_ATTACHMENT_BYTES} bytes."
        )

    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > MAX_REMOTE_ATTACHMENT_BYTES:
            raise AttachmentTooLargeError(
                f"Attachment URL exceeds the maximum allowed size of {MAX_REMOTE_ATTACHMENT_BYTES} bytes."
            )
        chunks.append(chunk)
    return b"".join(chunks)


def get_response_content_type(response: Response) -> str | None:
    content_type = response.headers.get("Content-Type")
    if not content_type:
        return None
    return content_type.split(";", 1)[0].strip() or None


def split_mime_type(value: str | None) -> tuple[str, str]:
    if value and "/" in value:
        return value.split("/", 1)
    return "application", "octet-stream"


def encode_message(message: EmailMessage) -> str:
    return base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")


def extract_message_bodies(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    text_body = None
    html_body = None

    mime_type = payload.get("mimeType")
    body_data = payload.get("body", {}).get("data")
    if mime_type == "text/plain" and body_data:
        text_body = decode_base64_url(body_data)
    elif mime_type == "text/html" and body_data:
        html_body = decode_base64_url(body_data)

    for part in payload.get("parts", []) or []:
        part_text, part_html = extract_message_bodies(part)
        if part_text and text_body is None:
            text_body = part_text
        if part_html and html_body is None:
            html_body = part_html

    return text_body, html_body


def format_message(response: dict[str, Any]) -> dict[str, Any]:
    headers = get_headers_map(response)
    text_body, html_body = extract_message_bodies(response.get("payload", {}))
    return {
        "id": response["id"],
        "threadId": response.get("threadId"),
        "labelIds": response.get("labelIds", []),
        "snippet": response.get("snippet", ""),
        "internalDate": response.get("internalDate"),
        "sizeEstimate": response.get("sizeEstimate"),
        "historyId": response.get("historyId"),
        "headers": headers,
        "bodyText": text_body,
        "bodyHtml": html_body,
    }


def format_draft(draft: dict[str, Any]) -> dict[str, Any]:
    return {
        "draftId": draft.get("id"),
        "message": format_message(draft["message"]),
    }


def summarize_modified_message(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "messageId": message.get("id"),
        "threadId": message.get("threadId"),
        "labelIds": message.get("labelIds", []),
    }


def get_headers_map(message: dict[str, Any]) -> dict[str, str]:
    return {
        header["name"]: header["value"]
        for header in message.get("payload", {}).get("headers", [])
    }


def build_reply_recipients(headers: dict[str, str], *, reply_all: bool) -> dict[str, list[str]]:
    to = [headers.get("Reply-To") or headers.get("From") or ""]
    cc: list[str] = []
    if reply_all:
        cc = parse_header_addresses(headers.get("Cc"))
    return {
        "to": parse_email_addresses(to),
        "cc": cc,
    }


def parse_header_addresses(value: str | None) -> list[str]:
    if not value:
        return []
    return parse_email_addresses([part.strip() for part in value.split(",")])


def build_reply_subject(subject: str | None) -> str:
    base = (subject or "").strip()
    if base.lower().startswith("re:"):
        return base
    return f"Re: {base}" if base else "Re:"


def build_forward_subject(subject: str | None) -> str:
    base = (subject or "").strip()
    if base.lower().startswith("fwd:"):
        return base
    return f"Fwd: {base}" if base else "Fwd:"


def build_references(headers: dict[str, str]) -> str | None:
    references = headers.get("References", "").strip()
    message_id = (headers.get("Message-ID") or "").strip()
    if references and message_id:
        return f"{references} {message_id}".strip()
    return references or message_id or None


def build_forward_body(*, body_text: str, original_message: dict[str, Any]) -> str:
    headers = original_message["headers"]
    lines = [body_text.rstrip(), "", "---------- Forwarded message ---------"]
    if headers.get("From"):
        lines.append(f"From: {headers['From']}")
    if headers.get("Date"):
        lines.append(f"Date: {headers['Date']}")
    if headers.get("Subject"):
        lines.append(f"Subject: {headers['Subject']}")
    if headers.get("To"):
        lines.append(f"To: {headers['To']}")
    if headers.get("Cc"):
        lines.append(f"Cc: {headers['Cc']}")
    lines.append("")
    lines.append(original_message.get("bodyText") or original_message.get("snippet") or "")
    return "\n".join(lines).strip()


def decode_base64_url(value: str) -> str:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8")).decode(
        "utf-8", errors="replace"
    )


def quote_gmail_term(value: str) -> str:
    escaped = value.replace('"', '\\"').strip()
    if not escaped:
        return ""
    if " " in escaped:
        return f'"{escaped}"'
    return escaped


def build_or_query(prefix: str, values: list[str]) -> list[str]:
    quoted = [f"{prefix}:{quote_gmail_term(value)}" for value in values if value.strip()]
    if not quoted:
        return []
    if len(quoted) == 1:
        return quoted
    return ["(" + " OR ".join(quoted) + ")"]


def build_gmail_query(
    *,
    raw_query: str | None,
    subject_keywords: list[str],
    body_keywords: list[str],
    from_addresses: list[str],
    company_domains: list[str],
    has_attachments: bool | None,
    newer_than_days: int | None,
) -> str | None:
    parts: list[str] = []

    if raw_query and raw_query.strip():
        parts.append(raw_query.strip())

    parts.extend(build_or_query("subject", subject_keywords))
    parts.extend(build_or_query("from", from_addresses))

    for keyword in body_keywords:
        quoted = quote_gmail_term(keyword)
        if quoted:
            parts.append(quoted)

    domain_terms = [
        f"from:*@{domain.strip().lstrip('@')}" for domain in company_domains if domain.strip()
    ]
    if domain_terms:
        if len(domain_terms) == 1:
            parts.append(domain_terms[0])
        else:
            parts.append("(" + " OR ".join(domain_terms) + ")")

    if has_attachments:
        parts.append("has:attachment")

    if newer_than_days is not None:
        if newer_than_days <= 0:
            raise ValueError("newer_than_days must be greater than 0.")
        parts.append(f"newer_than:{newer_than_days}d")

    if not parts:
        return None

    return " ".join(parts)


def format_http_error(error: HttpError) -> str:
    return f"Gmail API error: {error.status_code} {error.reason}"
