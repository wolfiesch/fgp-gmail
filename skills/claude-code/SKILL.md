---
name: gmail
description: Fast Gmail access via FGP daemon (10x faster than MCP)
tools:
  - gmail.inbox
  - gmail.unread
  - gmail.search
  - gmail.send
  - gmail.thread
---

# Gmail Skill

Fast Gmail integration via the FGP daemon. Provides 10x faster response times than MCP-based tools.

## Available Methods

| Method | Description |
|--------|-------------|
| `gmail.inbox` | List recent emails from inbox |
| `gmail.unread` | Get unread count and summaries |
| `gmail.search` | Search emails by query |
| `gmail.send` | Send an email |
| `gmail.thread` | Get email thread by ID |

## Usage Examples

### Check Inbox

```bash
fgp call gmail.inbox -p '{"limit": 10}'
```

### Get Unread Count

```bash
fgp call gmail.unread
```

Returns unread count and first 10 unread email summaries.

### Search Emails

```bash
fgp call gmail.search -p '{"query": "from:newsletter", "limit": 5}'
```

Gmail search syntax supported (from:, to:, subject:, is:unread, etc.)

### Send Email

```bash
fgp call gmail.send -p '{"to": "user@example.com", "subject": "Hello", "body": "Message body"}'
```

### Get Thread

```bash
fgp call gmail.thread -p '{"thread_id": "abc123"}'
```

## Response Format

All methods return JSON. Example inbox response:

```json
{
  "emails": [
    {
      "id": "18abc123",
      "thread_id": "18abc123",
      "from": "sender@example.com",
      "subject": "Meeting tomorrow",
      "date": "Mon, 13 Jan 2026 10:00:00 -0800",
      "snippet": "Just a reminder about our meeting..."
    }
  ],
  "count": 10
}
```

## Setup

1. Ensure Gmail OAuth credentials are configured in `~/.fgp/auth/google/`
2. Run `fgp start gmail` to start the daemon
3. First run will prompt for OAuth authorization

## Performance

| Metric | FGP Gmail | Traditional MCP |
|--------|-----------|-----------------|
| Cold start | ~50ms | ~300-500ms |
| Warm call | ~10-30ms | N/A (always cold) |
| Batch support | Yes | No |
