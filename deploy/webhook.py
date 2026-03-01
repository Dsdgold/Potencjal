#!/usr/bin/env python3
"""
webhook.py — Lightweight GitHub webhook listener for Potencjal deploy.

Zero external dependencies (stdlib only).
Listens on port 9000, validates HMAC signature, triggers deploy.sh.

Usage:
    WEBHOOK_SECRET=your_secret python3 webhook.py
"""
import hashlib
import hmac
import http.server
import json
import logging
import os
import subprocess
import sys
import threading

PORT = int(os.environ.get("WEBHOOK_PORT", "9000"))
SECRET = os.environ.get("WEBHOOK_SECRET", "").encode()
DEPLOY_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy.sh")
ALLOWED_BRANCHES = {"refs/heads/main"}
LOG_FILE = "/var/log/potencjal-webhook.log"

deploy_lock = threading.Lock()

# File + stdout logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("webhook")


def verify_signature(payload: bytes, signature: str) -> bool:
    """Validate X-Hub-Signature-256 header."""
    if not SECRET:
        log.warning("WEBHOOK_SECRET not set — skipping signature check")
        return True
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(SECRET, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def run_deploy(branch: str) -> None:
    """Run deploy.sh in background (non-blocking, with lock)."""
    if not deploy_lock.acquire(blocking=False):
        log.info("Deploy already running, skipping")
        return
    try:
        log.info("Starting deploy for %s...", branch)
        result = subprocess.run(
            ["bash", DEPLOY_SCRIPT, branch],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.stdout:
            log.info(result.stdout)
        if result.returncode != 0:
            log.error("Deploy failed:\n%s", result.stderr)
        else:
            log.info("Deploy finished successfully")
    except subprocess.TimeoutExpired:
        log.error("Deploy timed out after 5 minutes")
    finally:
        deploy_lock.release()


class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/deploy":
            return self._handle_manual_deploy()

        if self.path != "/webhook":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(content_length)

        # Verify signature
        signature = self.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(payload, signature):
            log.warning("REJECTED — invalid signature")
            self.send_error(403, "Invalid signature")
            return

        # Parse event
        event = self.headers.get("X-GitHub-Event", "")
        if event == "ping":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"pong"}')
            log.info("Ping received from GitHub")
            return

        if event != "push":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ignored"}')
            return

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        ref = data.get("ref", "")
        if ref not in ALLOWED_BRANCHES:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f'{{"status":"skipped","ref":"{ref}"}}'.encode())
            log.info("Push to %s — not in allowed branches, skipping", ref)
            return

        branch = ref.split("/")[-1]
        pusher = data.get("pusher", {}).get("name", "unknown")
        log.info("Push to %s by %s — deploying", ref, pusher)

        # Respond immediately, deploy in background
        self.send_response(202)
        self.end_headers()
        self.wfile.write(b'{"status":"deploying"}')

        threading.Thread(target=run_deploy, args=(branch,), daemon=True).start()

    def _handle_manual_deploy(self):
        """POST /deploy — trigger deploy manually (localhost only)."""
        client_ip = self.client_address[0]
        if client_ip not in ("127.0.0.1", "::1"):
            self.send_error(403, "Manual deploy only from localhost")
            return

        log.info("Manual deploy triggered from localhost")
        self.send_response(202)
        self.end_headers()
        self.wfile.write(b'{"status":"deploying"}')
        threading.Thread(target=run_deploy, args=("main",), daemon=True).start()

    def do_GET(self):
        """Health check endpoint."""
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        log.info("[HTTP] %s", args[0])


def main():
    if not SECRET:
        log.warning("=" * 50)
        log.warning("WEBHOOK_SECRET not set!")
        log.warning("Set it: export WEBHOOK_SECRET=your_secret_here")
        log.warning("=" * 50)

    server = http.server.HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    log.info("Webhook listener started on port %d", PORT)
    log.info("Endpoints:")
    log.info("  POST /webhook  — GitHub push events")
    log.info("  POST /deploy   — Manual deploy (localhost only)")
    log.info("  GET  /health   — Health check")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
