//! FGP Gmail Daemon
//!
//! Fast daemon for Gmail operations using PyO3 for warm Python connections.
//!
//! # Architecture
//!
//! The daemon loads a Python module ONCE at startup via PyO3, keeping the
//! Gmail API connection warm. This eliminates the ~1-2s cold start overhead
//! of spawning a new Python subprocess for each request.
//!
//! Performance comparison:
//! - Subprocess per call: ~3.4s (cold Python + OAuth + API init every time)
//! - PyO3 warm connection: ~30-50ms (10-100x faster!)
//!
//! # Methods
//! - `gmail.inbox` - List recent inbox emails
//! - `gmail.unread` - Get ACCURATE unread count and summaries
//! - `gmail.search` - Search emails by query
//! - `gmail.read` - Read full email with body and attachment info
//! - `gmail.send` - Send an email with optional attachments
//! - `gmail.download_attachment` - Download attachment by ID
//! - `gmail.thread` - Get email thread
//!
//! # Setup
//! 1. Place Google OAuth credentials in ~/.fgp/auth/google/credentials.json
//! 2. Run once to complete OAuth flow
//! 3. Daemon will use cached tokens for subsequent calls
//!
//! # Run
//! ```bash
//! cargo run --release
//! ```
//!
//! # Test
//! ```bash
//! fgp call gmail.inbox -p '{"limit": 5}'
//! fgp call gmail.unread
//! fgp call gmail.search -p '{"query": "from:newsletter"}'
//! fgp call gmail.read -p '{"message_id": "abc123"}'
//! fgp call gmail.send -p '{"to": "user@example.com", "subject": "Hi", "body": "Hello!", "attachments": [{"path": "~/file.pdf"}]}'
//! fgp call gmail.download_attachment -p '{"message_id": "abc123", "attachment_id": "xyz", "save_path": "/tmp/file.pdf"}'
//! ```
//!
//! CHANGELOG (recent first, max 5 entries)
//! 01/14/2026 - Added attachment support: gmail.read, gmail.download_attachment, gmail.send with attachments (Claude)
//! 01/13/2026 - Switched to PyO3 PythonModule for warm connections (Claude)
//! 01/12/2026 - Initial implementation with subprocess per call (Claude)

use anyhow::{bail, Context, Result};
use fgp_daemon::python::PythonModule;
use fgp_daemon::FgpServer;
use std::path::PathBuf;

/// Find the Gmail Python module.
///
/// Searches in order:
/// 1. Next to the binary: ./module/gmail.py
/// 2. FGP services directory: ~/.fgp/services/gmail/module/gmail.py
/// 3. Cargo manifest directory (development): ./module/gmail.py
fn find_module_path() -> Result<PathBuf> {
    // Check next to the binary
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            let module_path = exe_dir.join("module").join("gmail.py");
            if module_path.exists() {
                return Ok(module_path);
            }
        }
    }

    // Check FGP services directory
    if let Some(home) = dirs::home_dir() {
        let module_path = home
            .join(".fgp")
            .join("services")
            .join("gmail")
            .join("module")
            .join("gmail.py");
        if module_path.exists() {
            return Ok(module_path);
        }
    }

    // Fallback to cargo manifest directory (development)
    let cargo_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("module")
        .join("gmail.py");
    if cargo_path.exists() {
        return Ok(cargo_path);
    }

    bail!(
        "Gmail module not found. Searched:\n\
         - <exe_dir>/module/gmail.py\n\
         - ~/.fgp/services/gmail/module/gmail.py\n\
         - {}/module/gmail.py",
        env!("CARGO_MANIFEST_DIR")
    )
}

fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter("fgp_gmail=debug,fgp_daemon=debug")
        .init();

    println!("Starting Gmail daemon (PyO3 warm connection)...");
    println!();

    // Find and load the Python module
    let module_path = find_module_path()?;
    println!("Loading Python module: {}", module_path.display());

    let module = PythonModule::load(&module_path, "GmailModule")
        .context("Failed to load GmailModule")?;

    println!("Gmail service initialized (warm connection ready)");
    println!();
    println!("Socket: ~/.fgp/services/gmail/daemon.sock");
    println!();
    println!("Test with:");
    println!("  fgp call gmail.inbox -p '{{\"limit\": 5}}'");
    println!("  fgp call gmail.unread");
    println!("  fgp call gmail.search -p '{{\"query\": \"is:unread\"}}'");
    println!();

    let server = FgpServer::new(module, "~/.fgp/services/gmail/daemon.sock")?;
    server.serve()?;

    Ok(())
}
