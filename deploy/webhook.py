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
import os
import subprocess
import sys
import threading

PORT = int(os.environ.get("WEBHOOK_PORT", "9000"))
SECRET = os.environ.get("WEBHOOK_SECRET", "").encode()
DEPLOY_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy.sh")
ALLOWED_BRANCHES = {"refs/heads/main"}

deploy_lock = threading.Lock()


def verify_signature(payload: bytes, signature: str) -> bool:
    """Validate X-Hub-Signature-256 header."""
    if not SECRET:
        print("[WARN] WEBHOOK_SECRET not set — skipping signature check", flush=True)
        return True
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(SECRET, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def run_deploy(branch: str) -> None:
    """Run deploy.sh in background (non-blocking, with lock)."""
    if not deploy_lock.acquire(blocking=False):
        print("[INFO] Deploy already running, skipping", flush=True)
        return
    try:
        print(f"[DEPLOY] Starting deploy for {branch}...", flush=True)
        result = subprocess.run(
            ["bash", DEPLOY_SCRIPT, branch],
            capture_output=True,
            text=True,
            timeout=300,
        )
        print(result.stdout, flush=True)
        if result.returncode != 0:
            print(f"[ERROR] Deploy failed:\n{result.stderr}", flush=True)
        else:
            print("[DEPLOY] Done.", flush=True)
    except subprocess.TimeoutExpired:
        print("[ERROR] Deploy timed out after 5 minutes", flush=True)
    finally:
        deploy_lock.release()


class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhook":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(content_length)

        # Verify signature
        signature = self.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(payload, signature):
            print("[REJECT] Invalid signature", flush=True)
            self.send_error(403, "Invalid signature")
            return

        # Parse event
        event = self.headers.get("X-GitHub-Event", "")
        if event == "ping":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"pong"}')
            print("[INFO] Ping received", flush=True)
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
            print(f"[INFO] Push to {ref} — not in allowed branches, skipping", flush=True)
            return

        branch = ref.split("/")[-1]

        # Respond immediately, deploy in background
        self.send_response(202)
        self.end_headers()
        self.wfile.write(b'{"status":"deploying"}')

        threading.Thread(target=run_deploy, args=(branch,), daemon=True).start()

    def do_GET(self):
        """Health check endpoint."""
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        print(f"[HTTP] {args[0]}", flush=True)


def main():
    if not SECRET:
        print("=" * 60)
        print("WARNING: WEBHOOK_SECRET not set!")
        print("Set it: export WEBHOOK_SECRET=your_secret_here")
        print("=" * 60)

    server = http.server.HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    print(f"Webhook listener started on port {PORT}", flush=True)
    print(f"Endpoint: POST http://0.0.0.0:{PORT}/webhook", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()
