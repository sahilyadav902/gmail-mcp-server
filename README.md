# sudo-gmail-mcp

A Python MCP server for Gmail that lets MCP clients such as Claude Desktop, Codex desktop, and other compatible clients use the published package name `sudo-gmail-mcp`:

- create Gmail drafts with `to`, `cc`, `bcc`, `subject`, `body_text`, optional `body_html`, and attachments from local files or HTTPS URLs
- update existing Gmail drafts
- fetch and send Gmail drafts by draft ID
- reply, reply-all, and forward messages
- send Gmail messages with the same fields and attachment support
- list Gmail labels
- mark messages read or unread
- list recent Gmail messages
- read a specific Gmail message
- search Gmail using raw Gmail queries or structured filters such as subject keywords, body keywords, senders, and company domains
- preserve original attachment filenames and file extensions when safely available

Warning: `send_gmail_message`, `send_gmail_draft`, `reply_to_gmail_message`, `reply_all_gmail_message`, and `forward_gmail_message` send mail immediately from your Gmail account.

## Tools

### `create_gmail_draft`
Creates a Gmail draft with optional attachments.

Inputs:
- `to: list[str]`
- `subject: str`
- `body_text: str`
- `cc: list[str] | None`
- `bcc: list[str] | None`
- `body_html: str | None`
- `attachments: list[str] | None` — local file paths or HTTPS URLs

### `update_gmail_draft`
Updates an existing draft by Gmail draft ID.

Inputs:
- `draft_id: str`
- `to: list[str]`
- `subject: str`
- `body_text: str`
- `cc: list[str] | None`
- `bcc: list[str] | None`
- `body_html: str | None`
- `attachments: list[str] | None` — local file paths or HTTPS URLs

### `get_gmail_draft`
Fetches a draft by Gmail draft ID.

Inputs:
- `draft_id: str`

### `send_gmail_draft`
Sends an existing draft by Gmail draft ID.

Inputs:
- `draft_id: str`

### `reply_to_gmail_message`
Replies to a Gmail message.

Inputs:
- `message_id: str`
- `body_text: str`
- `body_html: str | None`
- `attachments: list[str] | None` — local file paths or HTTPS URLs

### `reply_all_gmail_message`
Replies-all to a Gmail message.

Inputs:
- `message_id: str`
- `body_text: str`
- `body_html: str | None`
- `attachments: list[str] | None` — local file paths or HTTPS URLs

### `forward_gmail_message`
Forwards a Gmail message.

Inputs:
- `message_id: str`
- `to: list[str]`
- `body_text: str`
- `cc: list[str] | None`
- `bcc: list[str] | None`
- `body_html: str | None`
- `attachments: list[str] | None` — local file paths or HTTPS URLs

### `send_gmail_message`
Sends a Gmail message immediately.

Inputs:
- `to: list[str]`
- `subject: str`
- `body_text: str`
- `cc: list[str] | None`
- `bcc: list[str] | None`
- `body_html: str | None`
- `attachments: list[str] | None` — local file paths or HTTPS URLs

### `list_gmail_labels`
Lists Gmail labels.

### `mark_gmail_message_read`
Marks a Gmail message as read.

Inputs:
- `message_id: str`

### `mark_gmail_message_unread`
Marks a Gmail message as unread.

Inputs:
- `message_id: str`

### `list_gmail_messages`
Lists Gmail messages.

Inputs:
- `query: str | None`
- `label_ids: list[str] | None`
- `max_results: int`

### `get_gmail_message`
Fetches a full Gmail message.

Inputs:
- `message_id: str`

### `search_gmail_messages`
Searches Gmail using structured filters and returns the Gmail query it built.

Inputs:
- `raw_query: str | None`
- `subject_keywords: list[str] | None`
- `body_keywords: list[str] | None`
- `from_addresses: list[str] | None`
- `company_domains: list[str] | None`
- `has_attachments: bool | None`
- `newer_than_days: int | None`
- `label_ids: list[str] | None`
- `max_results: int`

## Prerequisites

- Python 3.10+
- A Google account with Gmail enabled
- A Google Cloud project with the Gmail API enabled
- OAuth desktop client credentials downloaded as JSON

## Gmail API setup

1. Open Google Cloud Console.
2. Create or select a project.
3. Enable **Gmail API**.
4. Go to **APIs & Services** → **OAuth consent screen**.
5. Configure the consent screen.
6. Go to **APIs & Services** → **Credentials**.
7. Create **OAuth client ID** credentials.
8. Choose **Desktop app**.
9. Download the JSON credentials file.
10. Save it as `credentials.json` in the project root, or set a custom path with `GMAIL_MCP_CREDENTIALS_FILE`.

## Install from source

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -e .
```

## Install from pip

After you publish the package to PyPI, install it anywhere without cloning the repo:

```bash
pip install sudo-gmail-mcp
```

Then run it with:

```bash
sudo-gmail-mcp
```

If you want to pin a specific release:

```bash
pip install sudo-gmail-mcp==0.1.0
```

## Authentication

The first time the server needs Gmail access, it opens a local browser OAuth flow.

By default:
- client credentials file: `credentials.json`
- refresh token file: `token.json`

Environment variables:

- `GMAIL_MCP_CREDENTIALS_FILE` — path to Google OAuth desktop credentials JSON
- `GMAIL_MCP_TOKEN_FILE` — path where the Gmail refresh token will be stored

Example:

```bash
export GMAIL_MCP_CREDENTIALS_FILE="C:/path/to/credentials.json"
export GMAIL_MCP_TOKEN_FILE="C:/path/to/token.json"
```

On Windows PowerShell:

```powershell
$env:GMAIL_MCP_CREDENTIALS_FILE = "C:\path\to\credentials.json"
$env:GMAIL_MCP_TOKEN_FILE = "C:\path\to\token.json"
```

## Run locally

```bash
sudo-gmail-mcp
```

## Claude Desktop MCP config

Add a server entry pointing to the installed command. Example shape:

```json
{
  "mcpServers": {
    "gmail": {
      "command": "sudo-gmail-mcp",
      "env": {
        "GMAIL_MCP_CREDENTIALS_FILE": "C:/path/to/credentials.json",
        "GMAIL_MCP_TOKEN_FILE": "C:/path/to/token.json"
      }
    }
  }
}
```

If your client requires launching via Python directly, use:

```json
{
  "mcpServers": {
    "gmail": {
      "command": "python",
      "args": ["-m", "sudo_gmail_mcp.server"],
      "env": {
        "GMAIL_MCP_CREDENTIALS_FILE": "C:/path/to/credentials.json",
        "GMAIL_MCP_TOKEN_FILE": "C:/path/to/token.json"
      }
    }
  }
}
```

## Codex or other MCP clients

Use the same pattern:
- command: `sudo-gmail-mcp` or `python -m sudo_gmail_mcp.server`
- pass the Gmail credentials/token file paths through environment variables

## Attachment URL safety

Remote attachments support HTTPS URLs only.

Blocked attachment sources:
- `http://...`
- `file://...`
- `https://localhost/...`
- private-network or loopback IP targets such as `https://127.0.0.1/...` or `https://192.168.1.10/...`

Safety behavior:
- remote downloads are size-limited to 10 MB
- filenames are taken from `Content-Disposition` when available, otherwise from the URL path
- filenames are sanitized before attaching
- original filename and extension are preserved when safely available

## Example prompts in an MCP client

- "Create a Gmail draft to jane@example.com with cc to finance@example.com, subject 'Q2 follow-up', body 'Please see attached', and attach `C:/tmp/report.pdf`."
- "Update Gmail draft `r-1234567890` with a new subject and body."
- "Get the Gmail draft with ID `r-1234567890`."
- "Send the Gmail draft with ID `r-1234567890`."
- "Reply to message `<message_id>` with body 'Thanks, received.'"
- "Reply all to message `<message_id>` and attach `C:/tmp/notes.txt`."
- "Forward message `<message_id>` to jane@example.com with note 'Please review'."
- "List Gmail labels."
- "Mark message `<message_id>` as read."
- "Mark message `<message_id>` as unread."
- "Send an email to jane@example.com with subject 'Hello', body 'Checking in', and attach `C:/tmp/agenda.docx`."
- "Create a Gmail draft to jane@example.com and attach `https://example.com/files/report.pdf`."
- "Send an email to jane@example.com and attach `https://example.com/files/invoice.pdf`."
- "List my last 10 inbox emails."
- "Get message `<message_id>`."
- "Search my email for invoices from stripe.com in the last 30 days with attachments."

## Security notes

- Keep `credentials.json` and token files private.
- Do not commit OAuth credentials or refresh tokens.
- This server uses the Gmail scope `https://www.googleapis.com/auth/gmail.modify`, which allows reading mailbox data, creating drafts, sending messages, replying, forwarding, and modifying labels/read state.
- Sending/replying/forwarding tools act immediately, so use them carefully.
- Remote attachment URLs are restricted to HTTPS and blocked for localhost/private-network targets.
- Remote attachment downloads are limited to 10 MB.

## Build and publish the pip package

Build distributable artifacts:

```bash
python -m pip install --upgrade pip
pip install -e .[dev]
python -m build
```

This creates:
- `dist/*.tar.gz` — source distribution
- `dist/*.whl` — wheel distribution

Validate the package metadata before upload:

```bash
python -m twine check dist/*
```

Upload to TestPyPI first:

```bash
python -m twine upload --repository testpypi dist/*
```

Install from TestPyPI to verify:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple sudo-gmail-mcp
```

Upload to PyPI:

```bash
python -m twine upload dist/*
```

After publishing, anyone can install and run it with:

```bash
pip install sudo-gmail-mcp
sudo-gmail-mcp
```

## Development

Install development tooling:

```bash
pip install -e .[dev]
pytest
```

## Release checklist

1. Update the version in `pyproject.toml` and `src/sudo_gmail_mcp/__init__.py`.
2. Clear old build artifacts if needed.
3. Run `pytest`.
4. Run `python -m build`.
5. Run `python -m twine check dist/*`.
6. Upload to TestPyPI, verify install, then upload to PyPI.
7. Create a git tag matching the release version if you want versioned releases in GitHub.

## Suggested future features

- archive/unarchive tools
- trash/untrash tools
- label add/remove tools for messages and threads
- thread-level tools
- download Gmail attachments
- pagination support for large searches
- unread/starred/important convenience filters
- better HTML sanitization or markdown-to-HTML support for outgoing messages
- attachment metadata in read/search results
