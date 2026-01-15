#!/usr/bin/env python3
"""
Gmail Daemon - Basic Operations Example

Demonstrates common Gmail operations using the FGP Gmail daemon.
Requires: Gmail daemon running (`fgp start gmail`)
"""

import json
import socket
import uuid
from pathlib import Path

SOCKET_PATH = Path.home() / ".fgp/services/gmail/daemon.sock"


def call_daemon(method: str, params: dict = None) -> dict:
    """Send a request to the Gmail daemon and return the response."""
    request = {
        "id": str(uuid.uuid4()),
        "v": 1,
        "method": method,
        "params": params or {}
    }

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(str(SOCKET_PATH))
        sock.sendall((json.dumps(request) + "\n").encode())

        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if b"\n" in response:
                break

        return json.loads(response.decode().strip())


def list_inbox(max_results: int = 10):
    """List recent emails from inbox."""
    print(f"\n📬 Listing {max_results} recent emails...")

    result = call_daemon("gmail.inbox", {"max_results": max_results})

    if result.get("ok"):
        emails = result["result"].get("emails", [])
        for email in emails:
            print(f"  • {email.get('subject', '(no subject)')}")
            print(f"    From: {email.get('from', 'unknown')}")
            print(f"    Date: {email.get('date', 'unknown')}")
            print()
    else:
        print(f"  ❌ Error: {result.get('error')}")


def search_emails(query: str, max_results: int = 5):
    """Search for emails matching a query."""
    print(f"\n🔍 Searching for: {query}")

    result = call_daemon("gmail.search", {
        "query": query,
        "max_results": max_results
    })

    if result.get("ok"):
        emails = result["result"].get("emails", [])
        print(f"  Found {len(emails)} matching emails")
        for email in emails:
            print(f"  • {email.get('subject', '(no subject)')}")
    else:
        print(f"  ❌ Error: {result.get('error')}")


def get_unread_count():
    """Get count of unread emails."""
    print("\n📊 Checking unread emails...")

    result = call_daemon("gmail.unread", {})

    if result.get("ok"):
        count = result["result"].get("count", 0)
        print(f"  You have {count} unread emails")
    else:
        print(f"  ❌ Error: {result.get('error')}")


def read_thread(thread_id: str):
    """Read a specific email thread."""
    print(f"\n📖 Reading thread: {thread_id}")

    result = call_daemon("gmail.thread", {"thread_id": thread_id})

    if result.get("ok"):
        thread = result["result"]
        messages = thread.get("messages", [])
        print(f"  Thread has {len(messages)} messages")
        for msg in messages:
            print(f"  • {msg.get('snippet', '')[:100]}...")
    else:
        print(f"  ❌ Error: {result.get('error')}")


def send_email(to: str, subject: str, body: str):
    """Send an email."""
    print(f"\n✉️ Sending email to: {to}")

    result = call_daemon("gmail.send", {
        "to": to,
        "subject": subject,
        "body": body
    })

    if result.get("ok"):
        print(f"  ✅ Email sent! Message ID: {result['result'].get('message_id')}")
    else:
        print(f"  ❌ Error: {result.get('error')}")


if __name__ == "__main__":
    print("Gmail Daemon Examples")
    print("=" * 40)

    # Check daemon health first
    health = call_daemon("health")
    if not health.get("ok"):
        print("❌ Gmail daemon not running. Start with: fgp start gmail")
        exit(1)

    print("✅ Gmail daemon is healthy")

    # Run examples
    get_unread_count()
    list_inbox(max_results=5)
    search_emails("is:unread", max_results=3)

    # Uncomment to send a test email:
    # send_email("test@example.com", "Test from FGP", "Hello from the Gmail daemon!")
