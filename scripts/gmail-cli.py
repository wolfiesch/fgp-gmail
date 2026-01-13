#!/usr/bin/env python3
"""
Gmail CLI - Simple wrapper for Gmail API operations.

Used by the fgp-gmail daemon for Gmail API calls.
Handles OAuth2 authentication using tokens from ~/.fgp/auth/google/

Usage:
    gmail-cli.py inbox [--limit N]
    gmail-cli.py unread
    gmail-cli.py search QUERY [--limit N]
    gmail-cli.py send TO SUBJECT BODY
    gmail-cli.py thread THREAD_ID
"""

import argparse
import base64
import json
import os
import pickle
import sys
from email.mime.text import MIMEText
from pathlib import Path

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print(json.dumps({
        "error": "Google API libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib"
    }))
    sys.exit(1)

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Auth paths - try FGP first, then legacy
FGP_AUTH_DIR = Path.home() / ".fgp" / "auth" / "google"
LEGACY_AUTH_DIR = Path.home() / ".wolfie-gateway" / "auth" / "google"


def get_credentials():
    """Get OAuth2 credentials, refreshing if needed."""
    creds = None

    # Try FGP auth first
    token_file = FGP_AUTH_DIR / "gmail_token.pickle"
    credentials_file = FGP_AUTH_DIR / "credentials.json"

    # Fallback to legacy
    if not token_file.exists():
        token_file = LEGACY_AUTH_DIR / "gmail_token.pickle"
        credentials_file = LEGACY_AUTH_DIR / "credentials.json"

    # Try to load existing token
    if token_file.exists():
        with open(token_file, 'rb') as f:
            creds = pickle.load(f)

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif credentials_file.exists():
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            raise FileNotFoundError(
                f"No credentials found. Place credentials.json in {FGP_AUTH_DIR} or {LEGACY_AUTH_DIR}"
            )

        # Save refreshed token
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, 'wb') as f:
            pickle.dump(creds, f)

    return creds


def get_service():
    """Build Gmail API service."""
    creds = get_credentials()
    return build('gmail', 'v1', credentials=creds)


def cmd_inbox(args):
    """List recent emails from inbox."""
    service = get_service()
    limit = args.limit or 10

    results = service.users().messages().list(
        userId='me',
        labelIds=['INBOX'],
        maxResults=limit
    ).execute()

    messages = results.get('messages', [])
    emails = []

    for msg in messages:
        detail = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='metadata',
            metadataHeaders=['From', 'Subject', 'Date']
        ).execute()

        headers = {h['name']: h['value'] for h in detail.get('payload', {}).get('headers', [])}
        emails.append({
            'id': msg['id'],
            'thread_id': detail.get('threadId'),
            'from': headers.get('From', ''),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
            'snippet': detail.get('snippet', '')[:100]
        })

    print(json.dumps({
        'emails': emails,
        'count': len(emails)
    }))


def cmd_unread(args):
    """Get unread email count and summaries."""
    service = get_service()

    results = service.users().messages().list(
        userId='me',
        labelIds=['INBOX', 'UNREAD'],
        maxResults=20
    ).execute()

    messages = results.get('messages', [])
    emails = []

    for msg in messages[:10]:  # Only fetch details for first 10
        detail = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='metadata',
            metadataHeaders=['From', 'Subject']
        ).execute()

        headers = {h['name']: h['value'] for h in detail.get('payload', {}).get('headers', [])}
        emails.append({
            'id': msg['id'],
            'from': headers.get('From', ''),
            'subject': headers.get('Subject', ''),
            'snippet': detail.get('snippet', '')[:80]
        })

    print(json.dumps({
        'unread_count': results.get('resultSizeEstimate', len(messages)),
        'emails': emails
    }))


def cmd_search(args):
    """Search emails."""
    service = get_service()
    query = args.query
    limit = args.limit or 10

    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=limit
    ).execute()

    messages = results.get('messages', [])
    emails = []

    for msg in messages:
        detail = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='metadata',
            metadataHeaders=['From', 'Subject', 'Date']
        ).execute()

        headers = {h['name']: h['value'] for h in detail.get('payload', {}).get('headers', [])}
        emails.append({
            'id': msg['id'],
            'from': headers.get('From', ''),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
            'snippet': detail.get('snippet', '')[:100]
        })

    print(json.dumps({
        'query': query,
        'emails': emails,
        'count': len(emails)
    }))


def cmd_send(args):
    """Send an email."""
    service = get_service()

    message = MIMEText(args.body)
    message['to'] = args.to
    message['subject'] = args.subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    result = service.users().messages().send(
        userId='me',
        body={'raw': raw}
    ).execute()

    print(json.dumps({
        'sent': True,
        'message_id': result.get('id'),
        'thread_id': result.get('threadId')
    }))


def cmd_thread(args):
    """Get email thread."""
    service = get_service()
    thread_id = args.thread_id

    thread = service.users().threads().get(
        userId='me',
        id=thread_id,
        format='metadata',
        metadataHeaders=['From', 'To', 'Subject', 'Date']
    ).execute()

    messages = []
    for msg in thread.get('messages', []):
        headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
        messages.append({
            'id': msg['id'],
            'from': headers.get('From', ''),
            'to': headers.get('To', ''),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
            'snippet': msg.get('snippet', '')
        })

    print(json.dumps({
        'thread_id': thread_id,
        'messages': messages,
        'count': len(messages)
    }))


def main():
    parser = argparse.ArgumentParser(description='Gmail CLI for FGP daemon')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # inbox
    p_inbox = subparsers.add_parser('inbox', help='List inbox emails')
    p_inbox.add_argument('--limit', type=int, default=10)
    p_inbox.set_defaults(func=cmd_inbox)

    # unread
    p_unread = subparsers.add_parser('unread', help='Get unread count')
    p_unread.set_defaults(func=cmd_unread)

    # search
    p_search = subparsers.add_parser('search', help='Search emails')
    p_search.add_argument('query', help='Search query')
    p_search.add_argument('--limit', type=int, default=10)
    p_search.set_defaults(func=cmd_search)

    # send
    p_send = subparsers.add_parser('send', help='Send email')
    p_send.add_argument('to', help='Recipient email')
    p_send.add_argument('subject', help='Email subject')
    p_send.add_argument('body', help='Email body')
    p_send.set_defaults(func=cmd_send)

    # thread
    p_thread = subparsers.add_parser('thread', help='Get thread')
    p_thread.add_argument('thread_id', help='Thread ID')
    p_thread.set_defaults(func=cmd_thread)

    args = parser.parse_args()

    try:
        args.func(args)
    except HttpError as e:
        print(json.dumps({'error': f'Gmail API error: {e.reason}'}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)


if __name__ == '__main__':
    main()
