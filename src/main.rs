//! FGP Gmail Daemon
//!
//! Fast daemon for Gmail operations. Uses a Python CLI helper for Gmail API calls.
//!
//! # Methods
//! - `inbox` - List recent inbox emails
//! - `unread` - Get unread count and summaries
//! - `search` - Search emails by query
//! - `send` - Send an email
//! - `thread` - Get email thread
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
//! ```

use anyhow::{bail, Context, Result};
use fgp_daemon::service::{HealthStatus, MethodInfo, ParamInfo};
use fgp_daemon::{FgpServer, FgpService};
use serde_json::Value;
use std::collections::HashMap;
use std::path::PathBuf;
use std::process::Command;

/// Path to the Gmail CLI helper script.
fn gmail_cli_path() -> PathBuf {
    // First check next to the binary
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()));

    if let Some(dir) = exe_dir {
        let script = dir.join("gmail-cli.py");
        if script.exists() {
            return script;
        }
        // Check in scripts/ relative to binary
        let script = dir.join("scripts").join("gmail-cli.py");
        if script.exists() {
            return script;
        }
    }

    // Check ~/.fgp/services/gmail/gmail-cli.py
    if let Some(home) = dirs::home_dir() {
        let script = home.join(".fgp/services/gmail/gmail-cli.py");
        if script.exists() {
            return script;
        }
    }

    // Fallback - assume it's in the cargo project
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("scripts/gmail-cli.py")
}

/// Gmail service using Python CLI for API calls.
struct GmailService {
    cli_path: PathBuf,
}

impl GmailService {
    fn new() -> Result<Self> {
        let cli_path = gmail_cli_path();
        if !cli_path.exists() {
            bail!(
                "Gmail CLI not found at: {}\nEnsure gmail-cli.py is installed.",
                cli_path.display()
            );
        }
        Ok(Self { cli_path })
    }

    /// Run the Gmail CLI helper and parse JSON output.
    fn run_cli(&self, args: &[&str]) -> Result<Value> {
        let output = Command::new("python3")
            .arg(&self.cli_path)
            .args(args)
            .output()
            .context("Failed to run gmail-cli.py")?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            // Try to parse JSON error from stdout
            if let Ok(error_json) = serde_json::from_slice::<Value>(&output.stdout) {
                if let Some(error) = error_json.get("error").and_then(|e| e.as_str()) {
                    bail!("Gmail API error: {}", error);
                }
            }
            bail!("gmail-cli failed: {}", stderr);
        }

        serde_json::from_slice(&output.stdout).context("Failed to parse gmail-cli output")
    }
}

impl FgpService for GmailService {
    fn name(&self) -> &str {
        "gmail"
    }

    fn version(&self) -> &str {
        "1.0.0"
    }

    fn dispatch(&self, method: &str, params: HashMap<String, Value>) -> Result<Value> {
        match method {
            "inbox" => self.inbox(params),
            "unread" => self.unread(),
            "search" => self.search(params),
            "send" => self.send(params),
            "thread" => self.thread(params),
            _ => bail!("Unknown method: {}", method),
        }
    }

    fn method_list(&self) -> Vec<MethodInfo> {
        vec![
            MethodInfo {
                name: "inbox".into(),
                description: "List recent inbox emails".into(),
                params: vec![ParamInfo {
                    name: "limit".into(),
                    param_type: "integer".into(),
                    required: false,
                    default: Some(Value::Number(10.into())),
                }],
            },
            MethodInfo {
                name: "unread".into(),
                description: "Get unread email count and summaries".into(),
                params: vec![],
            },
            MethodInfo {
                name: "search".into(),
                description: "Search emails by query".into(),
                params: vec![
                    ParamInfo {
                        name: "query".into(),
                        param_type: "string".into(),
                        required: true,
                        default: None,
                    },
                    ParamInfo {
                        name: "limit".into(),
                        param_type: "integer".into(),
                        required: false,
                        default: Some(Value::Number(10.into())),
                    },
                ],
            },
            MethodInfo {
                name: "send".into(),
                description: "Send an email".into(),
                params: vec![
                    ParamInfo {
                        name: "to".into(),
                        param_type: "string".into(),
                        required: true,
                        default: None,
                    },
                    ParamInfo {
                        name: "subject".into(),
                        param_type: "string".into(),
                        required: true,
                        default: None,
                    },
                    ParamInfo {
                        name: "body".into(),
                        param_type: "string".into(),
                        required: true,
                        default: None,
                    },
                ],
            },
            MethodInfo {
                name: "thread".into(),
                description: "Get email thread by ID".into(),
                params: vec![ParamInfo {
                    name: "thread_id".into(),
                    param_type: "string".into(),
                    required: true,
                    default: None,
                }],
            },
        ]
    }

    fn on_start(&self) -> Result<()> {
        // Verify Gmail CLI exists and Python is available
        let output = Command::new("python3")
            .arg("--version")
            .output()
            .context("Python3 not found")?;

        if !output.status.success() {
            bail!("Python3 not available");
        }

        tracing::info!(
            cli_path = %self.cli_path.display(),
            "Gmail daemon starting"
        );
        Ok(())
    }

    fn health_check(&self) -> HashMap<String, HealthStatus> {
        let mut status = HashMap::new();

        // Check if CLI exists
        if self.cli_path.exists() {
            status.insert(
                "gmail_cli".into(),
                HealthStatus {
                    ok: true,
                    latency_ms: None,
                    message: Some(format!("CLI at {}", self.cli_path.display())),
                },
            );
        } else {
            status.insert(
                "gmail_cli".into(),
                HealthStatus {
                    ok: false,
                    latency_ms: None,
                    message: Some("gmail-cli.py not found".into()),
                },
            );
        }

        status
    }
}

impl GmailService {
    /// List inbox emails.
    fn inbox(&self, params: HashMap<String, Value>) -> Result<Value> {
        let limit = params
            .get("limit")
            .and_then(|v| v.as_u64())
            .unwrap_or(10);

        self.run_cli(&["inbox", "--limit", &limit.to_string()])
    }

    /// Get unread count and summaries.
    fn unread(&self) -> Result<Value> {
        self.run_cli(&["unread"])
    }

    /// Search emails.
    fn search(&self, params: HashMap<String, Value>) -> Result<Value> {
        let query = params
            .get("query")
            .and_then(|v| v.as_str())
            .context("query parameter is required")?;

        let limit = params
            .get("limit")
            .and_then(|v| v.as_u64())
            .unwrap_or(10);

        self.run_cli(&["search", query, "--limit", &limit.to_string()])
    }

    /// Send an email.
    fn send(&self, params: HashMap<String, Value>) -> Result<Value> {
        let to = params
            .get("to")
            .and_then(|v| v.as_str())
            .context("to parameter is required")?;

        let subject = params
            .get("subject")
            .and_then(|v| v.as_str())
            .context("subject parameter is required")?;

        let body = params
            .get("body")
            .and_then(|v| v.as_str())
            .context("body parameter is required")?;

        self.run_cli(&["send", to, subject, body])
    }

    /// Get email thread.
    fn thread(&self, params: HashMap<String, Value>) -> Result<Value> {
        let thread_id = params
            .get("thread_id")
            .and_then(|v| v.as_str())
            .context("thread_id parameter is required")?;

        self.run_cli(&["thread", thread_id])
    }
}

fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter("fgp_gmail=debug,fgp_daemon=debug")
        .init();

    println!("Starting Gmail daemon...");
    println!("Socket: ~/.fgp/services/gmail/daemon.sock");
    println!();
    println!("Test with:");
    println!("  fgp call gmail.inbox -p '{{\"limit\": 5}}'");
    println!("  fgp call gmail.unread");
    println!("  fgp call gmail.search -p '{{\"query\": \"is:unread\"}}'");
    println!();

    let service = GmailService::new()?;
    let server = FgpServer::new(service, "~/.fgp/services/gmail/daemon.sock")?;
    server.serve()?;

    Ok(())
}
