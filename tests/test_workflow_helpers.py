from sudo_gmail_mcp.gmail_client import (
    UNREAD_LABEL,
    build_forward_body,
    build_forward_subject,
    build_references,
    build_reply_recipients,
    build_reply_subject,
    summarize_modified_message,
)


def test_build_reply_subject_adds_prefix() -> None:
    assert build_reply_subject("Quarterly update") == "Re: Quarterly update"
    assert build_reply_subject("Re: Quarterly update") == "Re: Quarterly update"


def test_build_forward_subject_adds_prefix() -> None:
    assert build_forward_subject("Quarterly update") == "Fwd: Quarterly update"
    assert build_forward_subject("Fwd: Quarterly update") == "Fwd: Quarterly update"


def test_build_references_appends_message_id() -> None:
    headers = {
        "References": "<parent@example.com>",
        "Message-ID": "<child@example.com>",
    }
    assert build_references(headers) == "<parent@example.com> <child@example.com>"


def test_build_reply_recipients_reply_to() -> None:
    headers = {
        "From": "sender@example.com",
        "Reply-To": "reply@example.com",
        "Cc": "team@example.com, staff@example.com",
    }
    recipients = build_reply_recipients(headers, reply_all=False)
    assert recipients == {"to": ["reply@example.com"], "cc": []}


def test_build_reply_recipients_reply_all() -> None:
    headers = {
        "From": "sender@example.com",
        "Cc": "team@example.com, staff@example.com",
    }
    recipients = build_reply_recipients(headers, reply_all=True)
    assert recipients == {
        "to": ["sender@example.com"],
        "cc": ["team@example.com", "staff@example.com"],
    }


def test_build_forward_body_contains_original_message() -> None:
    original = {
        "headers": {
            "From": "sender@example.com",
            "Date": "Fri, 8 May 2026 10:00:00 +0000",
            "Subject": "Quarterly update",
            "To": "team@example.com",
        },
        "bodyText": "Original body",
        "snippet": "snippet",
    }
    body = build_forward_body(body_text="Please see below", original_message=original)
    assert "Please see below" in body
    assert "Forwarded message" in body
    assert "Original body" in body


def test_summarize_modified_message_returns_message_fields() -> None:
    message = {
        "id": "msg-123",
        "threadId": "thread-123",
        "labelIds": [UNREAD_LABEL],
    }
    assert summarize_modified_message(message) == {
        "messageId": "msg-123",
        "threadId": "thread-123",
        "labelIds": [UNREAD_LABEL],
    }
