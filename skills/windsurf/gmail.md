# Gmail Workflow

Fast Gmail integration via FGP daemon. Provides 10x faster response times than MCP-based tools.

## Available Methods

| Method | Description |
|--------|-------------|
| `gmail.inbox` | List recent emails from inbox |
| `gmail.unread` | Get unread count and summaries |
| `gmail.search` | Search emails by query |
| `gmail.send` | Send an email |
| `gmail.thread` | Get email thread by ID |

## Commands

### gmail.inbox - Check Inbox

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 10 | Maximum emails to return (1-100) |

```bash
fgp call gmail.inbox -p '{"limit": 10}'
```

**Response:**
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

---

### gmail.unread - Get Unread Count

No parameters. Returns unread count and first 10 unread email summaries.

```bash
fgp call gmail.unread
```

**Response:**
```json
{
  "unread_count": 5,
  "emails": [/* first 10 unread emails */]
}
```

---

### gmail.search - Search Emails

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Gmail search query |
| `limit` | integer | No | 10 | Maximum emails to return |

```bash
fgp call gmail.search -p '{"query": "from:newsletter", "limit": 5}'
```

**Search Syntax Examples:**
- `from:sender@example.com` - Filter by sender
- `to:recipient@example.com` - Filter by recipient
- `subject:keyword` - Filter by subject
- `is:unread` - Only unread emails
- `after:2025/01/01` - After date
- `before:2025/12/31` - Before date
- `has:attachment` - Has attachments
- `label:important` - Has label

**Response:**
```json
{
  "emails": [/* array of email objects */],
  "count": 5,
  "query": "from:newsletter"
}
```

---

### gmail.send - Send Email

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `to` | string | Yes | - | Recipient email address |
| `subject` | string | Yes | - | Email subject line |
| `body` | string | Yes | - | Email body (plain text) |

```bash
fgp call gmail.send -p '{"to": "user@example.com", "subject": "Hello", "body": "Message body"}'
```

**Response:**
```json
{
  "sent": true,
  "message_id": "18abc456",
  "thread_id": "18abc123"
}
```

---

### gmail.thread - Get Thread

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `thread_id` | string | Yes | - | Thread ID from inbox/search results |

```bash
fgp call gmail.thread -p '{"thread_id": "18abc123"}'
```

**Response:**
```json
{
  "thread_id": "18abc123",
  "messages": [/* array of messages with to/from */],
  "count": 3
}
```

## Workflow Steps

1. **User requests email action** (check inbox, send, search)
2. **Run appropriate `fgp call gmail.*` command** with parameters
3. **Parse JSON response** for structured data
4. **Present results to user** in readable format

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `Gmail API error: invalid_grant` | OAuth token expired | Re-run OAuth flow |
| `Gmail API error: 403` | Insufficient permissions | Check OAuth scopes |
| `query parameter is required` | Missing search query | Add query parameter |
| `gmail-cli failed` | Python script error | Check Python 3 installed |

## Troubleshooting

| Issue | Check | Fix |
|-------|-------|-----|
| Daemon not running | `fgp status gmail` | `fgp start gmail` |
| Connection refused | Socket exists? | `fgp start gmail` |
| OAuth expired | Token age | Delete token, restart |
| Python not found | `python3 --version` | Install Python 3 |
| No credentials | `~/.fgp/auth/google/` | Add credentials.json |

**Logs location:** `~/.fgp/services/gmail/logs/`

## Performance Tips

- **Keep daemon running** - Warm calls are fastest (10-30ms vs 300-500ms cold start)
- **Use `limit` parameter** - Reduce payload size for faster responses
- **Batch related queries** - Combine operations when possible
- **Cache thread IDs** - Avoid repeated lookups for the same thread
