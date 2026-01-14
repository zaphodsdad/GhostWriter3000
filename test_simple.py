#!/usr/bin/env python3
"""
Simple test script that doesn't require any pip installations.
Just uses Python standard library to serve the frontend.
"""

import http.server
import socketserver
import webbrowser
from pathlib import Path
import threading
import time

PORT = 8000
DIRECTORY = Path(__file__).parent / "frontend"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def log_message(self, format, *args):
        # Custom log format
        print(f"[{self.log_date_time_string()}] {format % args}")

def open_browser():
    """Open browser after a short delay"""
    time.sleep(1)
    webbrowser.open(f'http://localhost:{PORT}')

if __name__ == "__main__":
    print("=" * 50)
    print("  Prose Pipeline - Simple Test Server")
    print("=" * 50)
    print()
    print(f"Serving frontend from: {DIRECTORY}")
    print(f"Server running at: http://localhost:{PORT}")
    print()
    print("Note: This is just the frontend HTML.")
    print("The backend API is not running, so the health check will show 'Offline'.")
    print()
    print("To see the full application with API:")
    print("  1. Install: sudo apt install python3-pip python3-venv")
    print("  2. Run: ./run_server.sh")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    print()

    # Open browser in background
    threading.Thread(target=open_browser, daemon=True).start()

    # Start server
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nShutting down server...")
            print("Goodbye!")
