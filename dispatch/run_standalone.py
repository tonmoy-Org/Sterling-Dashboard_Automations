"""
Standalone Launcher for Dispatch Board Display Automation Scraper
Runs independently inside the root /dispatch directory.
"""

import os
import sys
import asyncio
import argparse

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

_dispatch_dir = os.path.dirname(os.path.abspath(__file__))
if _dispatch_dir not in sys.path:
    sys.path.insert(0, _dispatch_dir)

import http.server
import socketserver
import threading
import json
from datetime import datetime
from dispatch_board_display_automation_scraper import DispatchBoardDisplayAutomationScraper

STATUS_DATA = {
    "status": "online",
    "service": "Dispatch Board Display Automation",
    "mode": "DRY RUN",
    "days_configured": 30,
    "last_run": None,
    "last_status": "initialized",
    "port": 3000
}

class StatusHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        response_data = json.dumps(STATUS_DATA, indent=2)
        self.wfile.write(response_data.encode("utf-8"))

    def log_message(self, format, *args):
        pass

def start_status_server(port: int):
    STATUS_DATA["port"] = port
    def run_server():
        try:
            handler = StatusHTTPRequestHandler
            with socketserver.TCPServer(("", port), handler) as httpd:
                print(f"🌐 Status & Health Server listening on port {port} (http://0.0.0.0:{port})")
                httpd.serve_forever()
        except Exception as e:
            print(f"⚠️ Could not start HTTP server on port {port}: {e}")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

async def run_automation(args):
    STATUS_DATA["mode"] = "LIVE" if args.live else "DRY RUN"
    STATUS_DATA["days_configured"] = args.days

    scraper = DispatchBoardDisplayAutomationScraper()
    if args.loop:
        print(f"🔄 Loop Mode enabled. Running every {args.interval_hours} hours to maintain {args.days} pre-created days...")
        while True:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n⏰ [{now_str}] Starting automation run for {args.days} days...")
            STATUS_DATA["last_run"] = now_str
            STATUS_DATA["last_status"] = "running"
            try:
                await scraper.run(days=args.days, dry_run=not args.live, start_date_str=args.start_date)
                STATUS_DATA["last_status"] = "success"
            except Exception as e:
                print(f"❌ Error during scheduled run: {e}")
                STATUS_DATA["last_status"] = f"error: {str(e)}"

            sleep_seconds = int(args.interval_hours * 3600)
            print(f"\n😴 Run complete. Waiting {args.interval_hours} hours until next run. (Press Ctrl+C to stop)")
            await asyncio.sleep(sleep_seconds)
    else:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATUS_DATA["last_run"] = now_str
        STATUS_DATA["last_status"] = "running"
        try:
            await scraper.run(days=args.days, dry_run=not args.live, start_date_str=args.start_date)
            STATUS_DATA["last_status"] = "success"
        except Exception as e:
            STATUS_DATA["last_status"] = f"error: {str(e)}"
            raise e

def main():
    parser = argparse.ArgumentParser(description="Run Dispatch Board Display Automation Scraper (Standalone)")
    parser.add_argument("--days", type=int, default=30, help="Number of days to process (default: 30)")
    parser.add_argument("--live", action="store_true", help="Run live on FieldEdge (skips dry-run)")
    parser.add_argument("--start-date", type=str, help="Starting date (e.g. 'August 15', '08/15/2026'). Defaults to today.")
    parser.add_argument("--loop", action="store_true", help="Run continuously on a scheduled interval (e.g. daily)")
    parser.add_argument("--interval-hours", type=float, default=24.0, help="Interval between runs in hours when --loop is set (default: 24)")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "3000")), help="HTTP status server port (default: 3000)")
    args = parser.parse_args()

    start_status_server(args.port)

    print(f"🚀 Starting Dispatch Board Display Automation Scraper (Standalone)...")
    print(f"   Mode: {'LIVE' if args.live else 'DRY RUN'}")
    print(f"   Days: {args.days}")
    print(f"   HTTP Status Port: {args.port}")
    if args.start_date:
        print(f"   Start Date: {args.start_date}")
    if args.loop:
        print(f"   Loop Schedule: Every {args.interval_hours} hours")

    asyncio.run(run_automation(args))

if __name__ == "__main__":
    main()
