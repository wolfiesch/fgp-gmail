# Gmail Workflow

Fast Gmail integration via FGP daemon. 10x faster than MCP-based tools.

## Commands

### Check Inbox
```bash
fgp call gmail.inbox -p '{"limit": 10}'
```

### Get Unread Count
```bash
fgp call gmail.unread
```

### Search Emails
```bash
fgp call gmail.search -p '{"query": "from:newsletter", "limit": 5}'
```

Supports Gmail search syntax: `from:`, `to:`, `subject:`, `is:unread`, `after:`, `has:attachment`

### Send Email
```bash
fgp call gmail.send -p '{"to": "user@example.com", "subject": "Hello", "body": "Message body"}'
```

### Get Thread
```bash
fgp call gmail.thread -p '{"thread_id": "abc123"}'
```

## Workflow Steps

1. **User requests email action** (check inbox, send, search)
2. **Run appropriate `fgp call gmail.*` command**
3. **Parse JSON response**
4. **Present results to user**

## Response Handling

All commands return JSON with structured data:
- `emails`: Array of email objects
- `count`: Number of results
- `unread_count`: For unread command
- `sent`: Boolean for send command

## Error Handling

If command fails, check:
1. Gmail daemon is running: `fgp status gmail`
2. OAuth is configured: `~/.fgp/auth/google/gmail_token.pickle`
3. Start daemon if needed: `fgp start gmail`
