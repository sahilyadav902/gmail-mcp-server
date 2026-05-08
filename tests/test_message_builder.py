import base64
from pathlib import Path

import pytest

from sudo_gmail_mcp.gmail_client import (
    AttachmentInput,
    AttachmentTooLargeError,
    RemoteAttachmentSession,
    UnsafeAttachmentURLError,
    UnsupportedAttachmentSchemeError,
    build_gmail_message_request,
    build_gmail_query,
    build_mime_message,
    decode_base64_url,
    download_remote_attachment,
    encode_message,
    extract_message_bodies,
)


class FakeResponse:
    def __init__(self, *, chunks: list[bytes], headers: dict[str, str], status_code: int = 200) -> None:
        self._chunks = chunks
        self.headers = headers
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size: int):
        return iter(self._chunks)

    def close(self) -> None:
        return None


class UrlFilenameSession(RemoteAttachmentSession):
    def get(self, url: str, *, stream: bool, timeout: int):
        return FakeResponse(
            chunks=[b"pdf bytes"],
            headers={"Content-Type": "application/pdf"},
        )


class ContentDispositionSession(RemoteAttachmentSession):
    def get(self, url: str, *, stream: bool, timeout: int):
        return FakeResponse(
            chunks=[b"xlsx bytes"],
            headers={
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Content-Disposition": 'attachment; filename="report final.xlsx"',
            },
        )


class UnsafeFilenameSession(RemoteAttachmentSession):
    def get(self, url: str, *, stream: bool, timeout: int):
        return FakeResponse(
            chunks=[b"zip bytes"],
            headers={
                "Content-Type": "application/zip",
                "Content-Disposition": 'attachment; filename="../../secret.zip"',
            },
        )


class OversizedSession(RemoteAttachmentSession):
    def get(self, url: str, *, stream: bool, timeout: int):
        return FakeResponse(
            chunks=[b"a" * (10 * 1024 * 1024), b"b"],
            headers={"Content-Type": "application/pdf"},
        )


class HeaderTooLargeSession(RemoteAttachmentSession):
    def get(self, url: str, *, stream: bool, timeout: int):
        return FakeResponse(
            chunks=[b"small"],
            headers={
                "Content-Type": "application/pdf",
                "Content-Length": str((10 * 1024 * 1024) + 1),
            },
        )


class MessageRequestSession(RemoteAttachmentSession):
    def get(self, url: str, *, stream: bool, timeout: int):
        return FakeResponse(
            chunks=[b"remote content"],
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": 'attachment; filename="invoice.pdf"',
            },
        )


def test_build_mime_message_with_html_and_attachment(tmp_path: Path) -> None:
    attachment = tmp_path / "example.txt"
    attachment.write_text("hello attachment", encoding="utf-8")

    message = build_mime_message(
        to=["to@example.com"],
        cc=["cc@example.com"],
        bcc=["bcc@example.com"],
        subject="Hello",
        body_text="Plain body",
        body_html="<p>HTML body</p>",
        attachments=[AttachmentInput(path=str(attachment))],
    )

    assert message["To"] == "to@example.com"
    assert message["Cc"] == "cc@example.com"
    assert message["Bcc"] == "bcc@example.com"
    assert message["Subject"] == "Hello"

    payloads = list(message.iter_attachments())
    assert len(payloads) == 1
    assert payloads[0].get_filename() == "example.txt"


def test_encode_message_returns_base64url() -> None:
    message = build_mime_message(
        to=["to@example.com"],
        cc=[],
        bcc=[],
        subject="Hi",
        body_text="Body",
        body_html=None,
        attachments=[],
    )

    encoded = encode_message(message)
    decoded = base64.urlsafe_b64decode(encoded.encode("utf-8"))

    assert b"Subject: Hi" in decoded


def test_build_gmail_message_request_wraps_raw_message() -> None:
    request = build_gmail_message_request(
        to=["to@example.com"],
        cc=[],
        bcc=[],
        subject="Hi",
        body_text="Body",
        body_html=None,
        attachments=[],
    )

    assert set(request.keys()) == {"raw"}
    decoded = base64.urlsafe_b64decode(request["raw"].encode("utf-8"))
    assert b"Subject: Hi" in decoded


def test_attachment_keeps_original_filename_and_extension(tmp_path: Path) -> None:
    attachment = tmp_path / "Quarterly Report.pdf"
    attachment.write_bytes(b"pdf bytes")

    message = build_mime_message(
        to=["to@example.com"],
        cc=[],
        bcc=[],
        subject="Attachment",
        body_text="See attached",
        body_html=None,
        attachments=[AttachmentInput(path=str(attachment))],
    )

    payload = list(message.iter_attachments())[0]
    assert payload.get_filename() == "Quarterly Report.pdf"


def test_remote_attachment_uses_filename_from_url() -> None:
    resolved = download_remote_attachment(
        AttachmentInput(path="https://example.com/files/report.pdf"),
        session=UrlFilenameSession(),
    )

    assert resolved.filename == "report.pdf"
    assert resolved.mime_type == "application/pdf"
    assert resolved.content == b"pdf bytes"


def test_remote_attachment_uses_content_disposition_filename() -> None:
    resolved = download_remote_attachment(
        AttachmentInput(path="https://example.com/download?id=123"),
        session=ContentDispositionSession(),
    )

    assert resolved.filename == "report final.xlsx"


def test_remote_attachment_sanitizes_filename() -> None:
    resolved = download_remote_attachment(
        AttachmentInput(path="https://example.com/archive"),
        session=UnsafeFilenameSession(),
    )

    assert resolved.filename == "_.._secret.zip"


def test_remote_attachment_rejects_http() -> None:
    with pytest.raises(UnsupportedAttachmentSchemeError):
        download_remote_attachment(
            AttachmentInput(path="http://example.com/file.pdf"),
        )


def test_remote_attachment_rejects_file_scheme() -> None:
    with pytest.raises(UnsupportedAttachmentSchemeError):
        download_remote_attachment(
            AttachmentInput(path="file:///tmp/file.pdf"),
        )


def test_remote_attachment_rejects_localhost() -> None:
    with pytest.raises(UnsafeAttachmentURLError):
        download_remote_attachment(
            AttachmentInput(path="https://localhost/file.pdf"),
        )


def test_remote_attachment_rejects_private_ip() -> None:
    with pytest.raises(UnsafeAttachmentURLError):
        download_remote_attachment(
            AttachmentInput(path="https://192.168.1.10/file.pdf"),
        )


def test_remote_attachment_rejects_large_content_length() -> None:
    with pytest.raises(AttachmentTooLargeError):
        download_remote_attachment(
            AttachmentInput(path="https://example.com/file.pdf"),
            session=HeaderTooLargeSession(),
        )


def test_remote_attachment_rejects_stream_larger_than_limit() -> None:
    with pytest.raises(AttachmentTooLargeError):
        download_remote_attachment(
            AttachmentInput(path="https://example.com/file.pdf"),
            session=OversizedSession(),
        )


def test_build_message_request_supports_remote_attachment() -> None:
    import sudo_gmail_mcp.gmail_client as gmail_client

    original = gmail_client.DEFAULT_REMOTE_ATTACHMENT_SESSION
    gmail_client.DEFAULT_REMOTE_ATTACHMENT_SESSION = MessageRequestSession()
    try:
        request = build_gmail_message_request(
            to=["to@example.com"],
            cc=[],
            bcc=[],
            subject="Remote",
            body_text="See attached",
            body_html=None,
            attachments=[AttachmentInput(path="https://example.com/invoice.pdf")],
        )
    finally:
        gmail_client.DEFAULT_REMOTE_ATTACHMENT_SESSION = original

    decoded = base64.urlsafe_b64decode(request["raw"].encode("utf-8"))
    assert b'filename="invoice.pdf"' in decoded


def test_extract_message_bodies_reads_nested_parts() -> None:
    plain = base64.urlsafe_b64encode(b"plain text").decode("utf-8")
    html = base64.urlsafe_b64encode(b"<p>html</p>").decode("utf-8")
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": plain}},
            {"mimeType": "text/html", "body": {"data": html}},
        ],
    }

    text_body, html_body = extract_message_bodies(payload)

    assert text_body == "plain text"
    assert html_body == "<p>html</p>"


def test_build_gmail_query_combines_filters() -> None:
    query = build_gmail_query(
        raw_query="label:inbox",
        subject_keywords=["invoice reminder"],
        body_keywords=["overdue"],
        from_addresses=["billing@example.com"],
        company_domains=["stripe.com", "acme.com"],
        has_attachments=True,
        newer_than_days=30,
    )

    assert query == (
        'label:inbox subject:"invoice reminder" from:billing@example.com overdue '
        '(from:*@stripe.com OR from:*@acme.com) has:attachment newer_than:30d'
    )


def test_build_gmail_query_returns_none_without_filters() -> None:
    query = build_gmail_query(
        raw_query=None,
        subject_keywords=[],
        body_keywords=[],
        from_addresses=[],
        company_domains=[],
        has_attachments=None,
        newer_than_days=None,
    )

    assert query is None


def test_build_gmail_query_rejects_invalid_newer_than_days() -> None:
    with pytest.raises(ValueError, match="newer_than_days must be greater than 0."):
        build_gmail_query(
            raw_query=None,
            subject_keywords=[],
            body_keywords=[],
            from_addresses=[],
            company_domains=[],
            has_attachments=None,
            newer_than_days=0,
        )


def test_decode_base64_url_handles_missing_padding() -> None:
    encoded = base64.urlsafe_b64encode(b"hello").decode("utf-8").rstrip("=")
    assert decode_base64_url(encoded) == "hello"
