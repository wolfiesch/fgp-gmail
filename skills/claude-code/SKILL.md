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

## Method Parameters

### gmail.inbox

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 10 | Maximum emails to return (1-100) |

```bash
fgp call gmail.inbox -p '{"limit": 10}'
```

### gmail.unread

No parameters. Returns unread count and first 10 unread email summaries.

```bash
fgp call gmail.unread
```

### gmail.search

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Gmail search query |
| `limit` | integer | No | 10 | Maximum emails to return |

```bash
fgp call gmail.search -p '{"query": "from:newsletter", "limit": 5}'
```

**Search syntax examples:**
- `from:sender@example.com` - Filter by sender
- `to:recipient@example.com` - Filter by recipient
- `subject:keyword` - Filter by subject
- `is:unread` - Only unread emails
- `after:2025/01/01` - After date
- `before:2025/12/31` - Before date
- `has:attachment` - Has attachments
- `label:important` - Has label

### gmail.send

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `to` | string | Yes | - | Recipient email address |
| `subject` | string | Yes | - | Email subject line |
| `body` | string | Yes | - | Email body (plain text) |

```bash
fgp call gmail.send -p '{"to": "user@example.com", "subject": "Hello", "body": "Message body"}'
```

### gmail.thread

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `thread_id` | string | Yes | - | Thread ID from inbox/search results |

```bash
fgp call gmail.thread -p '{"thread_id": "18abc123"}'
```

## Response Schemas

### Email Object

```json
{
  "id": "18abc123",
  "thread_id": "18abc123",
  "from": "sender@example.com",
  "subject": "Meeting tomorrow",
  "date": "Mon, 13 Jan 2026 10:00:00 -0800",
  "snippet": "Just a reminder about our meeting..."
}
```

### inbox/search Response

```json
{
  "emails": [/* array of email objects */],
  "count": 10,
  "query": "from:newsletter"  // only for search
}
```

### unread Response

```json
{
  "unread_count": 5,
  "emails": [/* first 10 unread emails */]
}
```

### send Response

```json
{
  "sent": true,
  "message_id": "18abc456",
  "thread_id": "18abc123"
}
```

### thread Response

```json
{
  "thread_id": "18abc123",
  "messages": [/* array of messages with to/from */],
  "count": 3
}
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "Gmail API error: invalid_grant" | OAuth token expired | Re-run OAuth flow |
| "Gmail API error: 403" | Insufficient permissions | Check OAuth scopes |
| "query parameter is required" | Missing search query | Add query parameter |
| "gmail-cli failed" | Python script error | Check Python 3 installed |

## Setup

1. **Get OAuth credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project and enable Gmail API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download `credentials.json`

2. **Place credentials:**
   ```bash
   mkdir -p ~/.fgp/auth/google
   mv credentials.json ~/.fgp/auth/google/
   ```

3. **Start daemon:**
   ```bash
   fgp start gmail
   ```

4. **Authorize (first run only):**
   - Browser opens for Google OAuth
   - Grant permissions
   - Token saved automatically

## Troubleshooting

| Issue | Check | Fix |
|-------|-------|-----|
| Daemon not running | `fgp status gmail` | `fgp start gmail` |
| Connection refused | Socket exists? | `fgp start gmail` |
| OAuth expired | Token age | Delete token, restart |
| Python not found | `python3 --version` | Install Python 3 |
| No credentials | `~/.fgp/auth/google/` | Add credentials.json |

**Logs location:** `~/.fgp/services/gmail/logs/`

## Performance

| Metric | FGP Gmail | Traditional MCP |
|--------|-----------|-----------------|
| Cold start | ~50ms | ~300-500ms |
| Warm call | ~10-30ms | N/A (always cold) |
| Batch support | Yes | No |

**Tips for best performance:**
- Keep daemon running (warm calls are fastest)
- Use `limit` parameter to reduce payload size
- Batch related queries when possible
