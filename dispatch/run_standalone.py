"""
Standalone Launcher for Dispatch Board Display Automation Scraper
Runs independently inside the root /dispatch directory.
"""

import os
import sys
import asyncio
import argparse
import http.server
import socketserver
import threading
import json
from datetime import datetime

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

_dispatch_dir = os.path.dirname(os.path.abspath(__file__))
if _dispatch_dir not in sys.path:
    sys.path.insert(0, _dispatch_dir)

from dispatch_board_display_automation_scraper import DispatchBoardDisplayAutomationScraper

STATUS_DATA = {
    "status": "online",
    "service": "Dispatch Board Display Automation",
    "mode": "DRY RUN",
    "days_configured": 30,
    "last_run": None,
    "last_status": "initialized",
    "progress": {
        "current_day": 0,
        "total_days": 30,
        "current_date": None,
        "completed_days": 0,
        "remaining_days": 30,
        "percent_complete": 0.0,
        "status": "idle",
        "status_message": "Waiting for run to start..."
    },
    "port": 3000
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dispatch Board Automation Status</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Outfit', sans-serif;
            background: #0f172a;
            color: #f8fafc;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        .card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 32px;
            width: 100%;
            max-width: 540px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }
        .title { font-size: 20px; font-weight: 700; color: #38bdf8; }
        .badge {
            background: #059669;
            color: #ecfdf5;
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .progress-section { margin-bottom: 24px; }
        .progress-header {
            display: flex;
            justify-content: space-between;
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 8px;
            font-weight: 600;
        }
        .progress-bar-bg {
            background: #334155;
            height: 14px;
            border-radius: 7px;
            overflow: hidden;
        }
        .progress-bar-fill {
            background: linear-gradient(90deg, #38bdf8, #818cf8);
            height: 100%;
            transition: width 0.4s ease;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-box {
            background: #0f172a;
            border: 1px solid #334155;
            padding: 16px;
            border-radius: 12px;
            text-align: center;
        }
        .stat-val { font-size: 22px; font-weight: 700; color: #f8fafc; }
        .stat-label { font-size: 12px; color: #94a3b8; margin-top: 4px; text-transform: uppercase; }
        .status-msg {
            background: #0f172a;
            border: 1px solid #334155;
            padding: 14px;
            border-radius: 10px;
            font-size: 14px;
            color: #cbd5e1;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .pulse {
            width: 12px;
            height: 12px;
            background: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
            animation: pulse 2s infinite;
            flex-shrink: 0;
        }
        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div class="title">Dispatch Board Automation</div>
            <div class="badge" id="modeBadge">LIVE MODE</div>
        </div>
        <div class="progress-section">
            <div class="progress-header">
                <span>Batch Progress (30 Days)</span>
                <span id="percentText">0%</span>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" id="progressBar" style="width: 0%;"></div>
            </div>
        </div>
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-val" id="currentDayVal">0 / 30</div>
                <div class="stat-label">Days Processed</div>
            </div>
            <div class="stat-box">
                <div class="stat-val" id="remainingVal">30</div>
                <div class="stat-label">Days Remaining</div>
            </div>
            <div class="stat-box">
                <div class="stat-val" id="currentDateVal">-</div>
                <div class="stat-label">Active Date Creation</div>
            </div>
            <div class="stat-box">
                <div class="stat-val" id="lastRunVal">-</div>
                <div class="stat-label">Last Run Time</div>
            </div>
        </div>
        <div class="status-msg">
            <div class="pulse"></div>
            <span id="statusMessage">Connecting to automation...</span>
        </div>
    </div>
    <script>
        async function fetchStatus() {
            try {
                const res = await fetch('/?format=json');
                const data = await res.json();
                document.getElementById('modeBadge').innerText = data.mode + ' MODE';
                document.getElementById('lastRunVal').innerText = data.last_run ? data.last_run.split(' ')[1] : '-';
                
                const p = data.progress || {};
                const curDay = p.current_day || 0;
                const totalDays = p.total_days || data.days_configured || 30;
                const rem = p.remaining_days !== undefined ? p.remaining_days : totalDays;
                const pct = p.percent_complete || 0;
                
                document.getElementById('percentText').innerText = pct + '%';
                document.getElementById('progressBar').style.width = pct + '%';
                document.getElementById('currentDayVal').innerText = curDay + ' / ' + totalDays;
                document.getElementById('remainingVal').innerText = rem + ' Days Left';
                document.getElementById('currentDateVal').innerText = p.current_date || '-';
                document.getElementById('statusMessage').innerText = p.status_message || data.last_status || 'Running';
            } catch (e) {
                console.error(e);
            }
        }
        setInterval(fetchStatus, 3000);
        fetchStatus();
    </script>
</body>
</html>
"""

class StatusHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        accept_header = self.headers.get("Accept", "")
        if "application/json" in accept_header or "format=json" in self.path or "/api" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            response_data = json.dumps(STATUS_DATA, indent=2)
            self.wfile.write(response_data.encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

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

def on_progress_update(progress_dict):
    STATUS_DATA["progress"] = progress_dict

async def run_automation(args):
    STATUS_DATA["mode"] = "LIVE" if args.live else "DRY RUN"
    STATUS_DATA["days_configured"] = args.days
    STATUS_DATA["progress"]["total_days"] = args.days
    STATUS_DATA["progress"]["remaining_days"] = args.days

    scraper = DispatchBoardDisplayAutomationScraper()
    if args.loop:
        print(f"🔄 Loop Mode enabled. Running every {args.interval_hours} hours to maintain {args.days} pre-created days...")
        while True:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n⏰ [{now_str}] Starting automation run for {args.days} days...")
            STATUS_DATA["last_run"] = now_str
            STATUS_DATA["last_status"] = "running"
            try:
                await scraper.run(days=args.days, dry_run=not args.live, start_date_str=args.start_date, on_progress=on_progress_update)
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
            await scraper.run(days=args.days, dry_run=not args.live, start_date_str=args.start_date, on_progress=on_progress_update)
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
