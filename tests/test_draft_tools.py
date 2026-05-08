from gmail_mcp.gmail_client import format_draft


def test_format_draft_returns_draft_id_and_message_fields() -> None:
    draft = {
        "id": "draft-123",
        "message": {
            "id": "msg-123",
            "threadId": "thread-123",
            "labelIds": ["DRAFT"],
            "snippet": "hello",
            "internalDate": "1710000000000",
            "sizeEstimate": 123,
            "historyId": "456",
            "payload": {
                "headers": [
                    {"name": "To", "value": "jane@example.com"},
                    {"name": "Subject", "value": "Hello"},
                ],
                "mimeType": "text/plain",
                "body": {"data": "aGVsbG8="},
            },
        },
    }

    result = format_draft(draft)

    assert result["draftId"] == "draft-123"
    assert result["message"]["id"] == "msg-123"
    assert result["message"]["headers"]["Subject"] == "Hello"
    assert result["message"]["bodyText"] == "hello"
