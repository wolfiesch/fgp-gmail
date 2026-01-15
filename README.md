# fgp-gmail

Fast Gmail integration for AI coding agents via the Fast Gateway Protocol (FGP).

## Features

- **10x faster** than MCP-based Gmail tools (10-30ms vs 200-500ms)
- **Multi-agent support**: Works with Claude Code, Cursor, Windsurf
- **One install**: `fgp install gmail` configures all your AI agents
- **OAuth2**: Secure authentication with Google

## Installation

```bash
fgp install gmail
```

This will:
1. Install the Gmail daemon to `~/.fgp/services/gmail/`
2. Detect your installed AI agents
3. Copy skill files to each agent's config directory
4. Configure OAuth (first run prompts for authorization)

## Manual Setup

### Prerequisites

- Python 3.8+
- Google Cloud project with Gmail API enabled
- OAuth2 credentials (Desktop app type)

### Steps

1. **Get OAuth credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project and enable Gmail API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download `credentials.json`

2. **Place credentials**:
   ```bash
   mkdir -p ~/.fgp/auth/google
   mv credentials.json ~/.fgp/auth/google/
   ```

3. **Build and run**:
   ```bash
   cargo build --release
   ./target/release/fgp-gmail
   ```

4. **Authorize** (first run only):
   - Browser opens for Google OAuth
   - Grant permissions
   - Token saved to `~/.fgp/auth/google/gmail_token.pickle`

## Usage

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

Gmail search syntax supported:
- `from:sender@example.com`
- `to:recipient@example.com`
- `subject:keyword`
- `is:unread`
- `after:2025/01/01`
- `has:attachment`

### Send Email

```bash
fgp call gmail.send -p '{"to": "user@example.com", "subject": "Hello", "body": "Message body"}'
```

### Get Thread

```bash
fgp call gmail.thread -p '{"thread_id": "abc123"}'
```

## Response Format

All methods return JSON:

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

## Performance

| Metric | fgp-gmail | Traditional MCP |
|--------|-----------|-----------------|
| Cold start | ~50ms | ~300-500ms |
| Warm call | ~10-30ms | N/A (always cold) |
| Batch support | Yes | No |

## Architecture

```
┌─────────────────────────────────────┐
│       fgp-gmail (Rust daemon)       │
│  • UNIX socket server               │
│  • NDJSON protocol                  │
│  • Method routing                   │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│       gmail-cli.py (Python)         │
│  • Gmail API calls                  │
│  • OAuth2 token management          │
│  • JSON response formatting         │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│         Gmail API (Google)          │
└─────────────────────────────────────┘
```

## Development

### Build

```bash
cargo build --release
```

### Run Tests

```bash
cargo test
```

### Run Daemon

```bash
cargo run --release
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related

- [protocol](https://github.com/fast-gateway-protocol/protocol) - Protocol specification
- [daemon](https://github.com/fast-gateway-protocol/daemon) - Rust SDK for building daemons
- [cli](https://github.com/fast-gateway-protocol/cli) - Command-line interface
