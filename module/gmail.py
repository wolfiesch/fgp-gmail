"""
Gmail Module for FGP daemon (PyO3 interface).

This module is loaded by the Rust daemon via PyO3 and keeps the Gmail service warm.
Each method call reuses the warm connection instead of spawning new processes.

CHANGELOG:
01/14/2026 - Added attachment support: gmail.read, gmail.download_attachment, gmail.send with attachments (Claude)
01/13/2026 - Created PyO3-compatible module for warm connections (Claude)
"""

import base64
import mimetypes
import pickle
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, Any, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Auth paths
FGP_AUTH_DIR = Path.home() / ".fgp" / "auth" / "google"
LEGACY_AUTH_DIR = Path.home() / ".wolfie-gateway" / "auth" / "google"


class GmailModule:
    """Gmail service module following FGP PyO3 interface."""

    # Required attributes for FGP
    name = "gmail"
    version = "1.0.0"

    def __init__(self):
        """Initialize Gmail service - this runs ONCE at daemon startup."""
        self.service = None
        self._init_service()

    def _get_credentials(self) -> Credentials:
        """Get OAuth2 credentials, refreshing if needed."""
        creds = None

        # Try FGP auth first
        token_file = FGP_AUTH_DIR / "gmail_token.pickle"
        credentials_file = FGP_AUTH_DIR / "credentials.json"

        # Fallback to legacy
        if not credentials_file.exists():
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
                    f"No credentials found. Place credentials.json in {FGP_AUTH_DIR}"
                )

            # Save refreshed token
            token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(token_file, 'wb') as f:
                pickle.dump(creds, f)

        return creds

    def _init_service(self):
        """Build Gmail API service (runs once at startup)."""
        creds = self._get_credentials()
        self.service = build('gmail', 'v1', credentials=creds, cache_discovery=False)

    def dispatch(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route method calls to handlers.

        This is called by the Rust daemon for each request.
        The service is already warm, so we just execute the method.
        """
        handlers = {
            "gmail.inbox": self._cmd_inbox,
            "gmail.unread": self._cmd_unread,
            "gmail.search": self._cmd_search,
            "gmail.send": self._cmd_send,
            "gmail.thread": self._cmd_thread,
            "gmail.read": self._cmd_read,
            "gmail.download_attachment": self._cmd_download_attachment,
        }

        handler = handlers.get(method)
        if handler is None:
            raise ValueError(f"Unknown method: {method}")

        return handler(params)

    def method_list(self) -> List[Dict[str, Any]]:
        """Return list of available methods."""
        return [
            {
                "name": "gmail.inbox",
                "description": "List recent inbox emails",
                "params": [{"name": "limit", "type": "integer", "required": False, "default": 10}]
            },
            {
                "name": "gmail.unread",
                "description": "Get accurate unread count and summaries",
                "params": [{"name": "limit", "type": "integer", "required": False, "default": 10}]
            },
            {
                "name": "gmail.search",
                "description": "Search emails by query",
                "params": [
                    {"name": "query", "type": "string", "required": True},
                    {"name": "limit", "type": "integer", "required": False, "default": 10}
                ]
            },
            {
                "name": "gmail.read",
                "description": "Read full email with body and attachment info",
                "params": [{"name": "message_id", "type": "string", "required": True}]
            },
            {
                "name": "gmail.send",
                "description": "Send an email with optional attachments",
                "params": [
                    {"name": "to", "type": "string", "required": True},
                    {"name": "subject", "type": "string", "required": True},
                    {"name": "body", "type": "string", "required": True},
                    {"name": "cc", "type": "string", "required": False},
                    {"name": "bcc", "type": "string", "required": False},
                    {"name": "attachments", "type": "array", "required": False, "description": "List of {filename, data (base64)} or {path}"}
                ]
            },
            {
                "name": "gmail.download_attachment",
                "description": "Download an attachment from an email",
                "params": [
                    {"name": "message_id", "type": "string", "required": True},
                    {"name": "attachment_id", "type": "string", "required": True},
                    {"name": "save_path", "type": "string", "required": False, "description": "Path to save file (returns base64 if not specified)"}
                ]
            },
            {
                "name": "gmail.thread",
                "description": "Get email thread by ID",
                "params": [{"name": "thread_id", "type": "string", "required": True}]
            }
        ]

    def on_start(self):
        """Called when daemon starts."""
        # Service already initialized in __init__
        pass

    def on_stop(self):
        """Called when daemon stops."""
        pass

    def health_check(self) -> Dict[str, Any]:
        """Return health status."""
        return {
            "gmail_service": {
                "ok": self.service is not None,
                "message": "Gmail service initialized" if self.service else "Service not initialized"
            }
        }

    # =========================================================================
    # Method Handlers
    # =========================================================================

    def _cmd_inbox(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List recent emails from inbox."""
        limit = params.get("limit", 10)

        results = self.service.users().messages().list(
            userId='me',
            labelIds=['INBOX'],
            maxResults=limit
        ).execute()

        messages = results.get('messages', [])
        emails = []

        for msg in messages:
            detail = self.service.users().messages().get(
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

        return {
            'emails': emails,
            'count': len(emails)
        }

    def _cmd_unread(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get ACCURATE unread count and summaries."""
        limit = params.get("limit", 10)

        # Get ACCURATE unread count from labels API (not estimate!)
        label_info = self.service.users().labels().get(
            userId='me',
            id='UNREAD'
        ).execute()
        accurate_unread_count = label_info.get('messagesUnread', 0)

        # Get recent unread messages for summaries
        results = self.service.users().messages().list(
            userId='me',
            labelIds=['INBOX', 'UNREAD'],
            maxResults=limit
        ).execute()

        messages = results.get('messages', [])
        emails = []

        for msg in messages:
            detail = self.service.users().messages().get(
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

        return {
            'unread_count': accurate_unread_count,  # Accurate, not estimate!
            'emails': emails
        }

    def _cmd_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search emails by query."""
        query = params.get("query")
        if not query:
            raise ValueError("query parameter is required")

        limit = params.get("limit", 10)

        results = self.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=limit
        ).execute()

        messages = results.get('messages', [])
        emails = []

        for msg in messages:
            detail = self.service.users().messages().get(
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

        return {
            'query': query,
            'emails': emails,
            'count': len(emails)
        }

    def _cmd_send(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send an email with optional attachments."""
        to = params.get("to")
        subject = params.get("subject")
        body = params.get("body")
        cc = params.get("cc")
        bcc = params.get("bcc")
        attachments = params.get("attachments", [])

        if not all([to, subject, body]):
            raise ValueError("to, subject, and body parameters are required")

        # Build message - multipart if we have attachments
        if attachments:
            message = MIMEMultipart()
            message.attach(MIMEText(body, 'plain'))
        else:
            message = MIMEText(body)

        message['to'] = to
        message['subject'] = subject
        if cc:
            message['cc'] = cc
        if bcc:
            message['bcc'] = bcc

        # Process attachments
        attached_files = []
        for attachment in attachments:
            if isinstance(attachment, dict):
                filename = attachment.get('filename') or attachment.get('name')
                data = attachment.get('data')
                file_path = attachment.get('path')

                if file_path:
                    # Load from file path
                    path = Path(file_path).expanduser()
                    if not path.exists():
                        raise FileNotFoundError(f"Attachment not found: {file_path}")
                    filename = filename or path.name
                    with open(path, 'rb') as f:
                        file_data = f.read()
                elif data:
                    # Use provided base64 data
                    file_data = base64.b64decode(data)
                else:
                    raise ValueError("Attachment must have 'path' or 'data' field")

                if not filename:
                    raise ValueError("Attachment must have 'filename' or 'name' field")

                # Guess MIME type
                mime_type, _ = mimetypes.guess_type(filename)
                if mime_type is None:
                    mime_type = 'application/octet-stream'
                main_type, sub_type = mime_type.split('/', 1)

                # Create attachment part
                part = MIMEBase(main_type, sub_type)
                part.set_payload(file_data)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment', filename=filename)
                message.attach(part)
                attached_files.append({'filename': filename, 'size': len(file_data)})

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        result = self.service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()

        return {
            'sent': True,
            'message_id': result.get('id'),
            'thread_id': result.get('threadId'),
            'attachments': attached_files if attached_files else None
        }

    def _cmd_thread(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get email thread by ID."""
        thread_id = params.get("thread_id")
        if not thread_id:
            raise ValueError("thread_id parameter is required")

        thread = self.service.users().threads().get(
            userId='me',
            id=thread_id,
            format='metadata',
            metadataHeaders=['From', 'Subject', 'Date']
        ).execute()

        messages = []
        for msg in thread.get('messages', []):
            headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
            messages.append({
                'id': msg['id'],
                'from': headers.get('From', ''),
                'subject': headers.get('Subject', ''),
                'date': headers.get('Date', ''),
                'snippet': msg.get('snippet', '')[:100]
            })

        return {
            'thread_id': thread_id,
            'messages': messages,
            'count': len(messages)
        }

    def _cmd_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read full email with body and attachment info."""
        message_id = params.get("message_id")
        if not message_id:
            raise ValueError("message_id parameter is required")

        # Get full message
        msg = self.service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()

        # Extract headers
        headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}

        # Extract body and attachments
        body_text = None
        body_html = None
        attachments = []

        def process_parts(parts, parent_mime_type=None):
            nonlocal body_text, body_html
            for part in parts:
                mime_type = part.get('mimeType', '')
                part_body = part.get('body', {})
                filename = part.get('filename', '')

                if mime_type == 'text/plain' and not filename:
                    data = part_body.get('data')
                    if data:
                        body_text = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                elif mime_type == 'text/html' and not filename:
                    data = part_body.get('data')
                    if data:
                        body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                elif filename or part_body.get('attachmentId'):
                    # This is an attachment
                    attachments.append({
                        'id': part_body.get('attachmentId'),
                        'filename': filename or 'untitled',
                        'mime_type': mime_type,
                        'size': part_body.get('size', 0)
                    })

                # Recursively process nested parts
                if 'parts' in part:
                    process_parts(part['parts'], mime_type)

        payload = msg.get('payload', {})

        # Handle simple messages (no parts)
        if payload.get('body', {}).get('data'):
            mime_type = payload.get('mimeType', 'text/plain')
            data = payload['body']['data']
            if 'text/plain' in mime_type:
                body_text = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
            elif 'text/html' in mime_type:
                body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')

        # Handle multipart messages
        if 'parts' in payload:
            process_parts(payload['parts'])

        return {
            'id': msg['id'],
            'thread_id': msg.get('threadId'),
            'from': headers.get('From', ''),
            'to': headers.get('To', ''),
            'cc': headers.get('Cc'),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
            'body_text': body_text,
            'body_html': body_html,
            'snippet': msg.get('snippet', ''),
            'labels': msg.get('labelIds', []),
            'attachments': attachments if attachments else None,
            'has_attachments': len(attachments) > 0
        }

    def _cmd_download_attachment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Download an attachment from an email."""
        message_id = params.get("message_id")
        attachment_id = params.get("attachment_id")
        save_path = params.get("save_path")

        if not message_id:
            raise ValueError("message_id parameter is required")
        if not attachment_id:
            raise ValueError("attachment_id parameter is required")

        # Get attachment data
        attachment = self.service.users().messages().attachments().get(
            userId='me',
            messageId=message_id,
            id=attachment_id
        ).execute()

        data = attachment.get('data', '')
        file_data = base64.urlsafe_b64decode(data)
        size = len(file_data)

        if save_path:
            # Save to file
            path = Path(save_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'wb') as f:
                f.write(file_data)
            return {
                'saved': True,
                'path': str(path),
                'size': size
            }
        else:
            # Return base64 encoded data
            return {
                'data': base64.b64encode(file_data).decode('ascii'),
                'size': size
            }
