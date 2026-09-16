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
    <title>Sterling Dispatch Automation Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: #0b0f19;
            background-image: 
                radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.12) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(99, 102, 241, 0.12) 0px, transparent 50%);
            color: #f8fafc;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 24px;
        }
        .container {
            width: 100%;
            max-width: 580px;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 24px;
        }
        .brand-icon {
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, #0284c7, #6366f1);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            box-shadow: 0 8px 20px -4px rgba(2, 132, 199, 0.4);
        }
        .brand-text h1 { font-size: 19px; font-weight: 800; letter-spacing: -0.5px; color: #ffffff; }
        .brand-text p { font-size: 13px; color: #94a3b8; font-weight: 500; }
        
        .card {
            background: rgba(30, 41, 59, 0.75);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 32px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }

        .status-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 28px;
            padding-bottom: 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        .status-title { font-size: 15px; font-weight: 600; color: #cbd5e1; }
        .badge-live {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #34d399;
            padding: 6px 16px;
            border-radius: 9999px;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .pulse-dot {
            width: 8px;
            height: 8px;
            background: #34d399;
            border-radius: 50%;
            box-shadow: 0 0 10px #34d399;
            animation: pulse 1.8s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(0.95); opacity: 0.8; }
            50% { transform: scale(1.25); opacity: 1; }
            100% { transform: scale(0.95); opacity: 0.8; }
        }

        .progress-block { margin-bottom: 32px; }
        .progress-labels {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 10px;
        }
        .progress-title { font-size: 14px; font-weight: 600; color: #94a3b8; }
        .progress-pct { font-size: 32px; font-weight: 800; color: #38bdf8; letter-spacing: -1px; }

        .progress-track {
            background: #0f172a;
            height: 16px;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 2px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #38bdf8, #818cf8, #a855f7);
            border-radius: 6px;
            transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.4);
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-bottom: 28px;
        }
        .metric-card {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 14px;
            padding: 20px;
            transition: transform 0.2s ease;
        }
        .metric-card:hover { transform: translateY(-2px); }
        .metric-value {
            font-size: 24px;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -0.5px;
        }
        .metric-label {
            font-size: 11px;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-top: 6px;
        }

        .live-log-bar {
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .log-icon { font-size: 18px; }
        .log-text { font-size: 14px; font-weight: 500; color: #cbd5e1; }
        .footer-note { text-align: center; margin-top: 20px; font-size: 12px; color: #475569; }
    </style>
</head>
<body>
    <div class="container">
        <div class="brand">
            <div class="brand-icon">⚡</div>
            <div class="brand-text">
                <h1>Sterling Septic & Plumbing</h1>
                <p>Dispatch Board Display Automation</p>
            </div>
        </div>

        <div class="card">
            <div class="status-header">
                <span class="status-title">System Execution Status</span>
                <div class="badge-live" id="modeBadge">
                    <div class="pulse-dot"></div>
                    <span id="badgeText">LIVE AUTOMATION</span>
                </div>
            </div>

            <div class="progress-block">
                <div class="progress-labels">
                    <span class="progress-title">30-Day Pre-Creation Progress</span>
                    <span class="progress-pct" id="pctText">0%</span>
                </div>
                <div class="progress-track">
                    <div class="progress-fill" id="progressFill" style="width: 0%;"></div>
                </div>
            </div>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value" id="daysProcessedVal">0 / 30</div>
                    <div class="metric-label">Completed Days</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="daysRemainingVal">30 Days</div>
                    <div class="metric-label">Remaining to Create</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="activeDateVal">-</div>
                    <div class="metric-label">Active Target Date</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="lastSyncVal">-</div>
                    <div class="metric-label">Last Synchronization</div>
                </div>
            </div>

            <div class="live-log-bar">
                <span class="log-icon">⚙️</span>
                <span class="log-text" id="statusMsg">Initializing automation engine...</span>
            </div>
        </div>
        <div class="footer-note">Auto-refreshing live metrics every 2s • Connected to VPS</div>
    </div>

    <script>
        async function updateDashboard() {
            try {
                const res = await fetch('/?json=1');
                const data = await res.json();
                
                document.getElementById('badgeText').innerText = (data.mode || 'LIVE') + ' RUNNING';
                
                const p = data.progress || {};
                const curDay = p.current_day || 0;
                const total = p.total_days || data.days_configured || 30;
                const rem = p.remaining_days !== undefined ? p.remaining_days : (total - curDay);
                const pct = p.percent_complete !== undefined ? p.percent_complete : 0;
                
                document.getElementById('pctText').innerText = pct + '%';
                document.getElementById('progressFill').style.width = pct + '%';
                
                document.getElementById('daysProcessedVal').innerText = curDay + ' / ' + total;
                document.getElementById('daysRemainingVal').innerText = rem + ' Days Left';
                document.getElementById('activeDateVal').innerText = p.current_date || '-';
                document.getElementById('lastSyncVal').innerText = data.last_run ? data.last_run.split(' ')[1] : '-';
                document.getElementById('statusMsg').innerText = p.status_message || data.last_status || 'System Active';
            } catch (err) {
                console.error('Error updating status:', err);
            }
        }
        setInterval(updateDashboard, 2000);
        updateDashboard();
    </script>
</body>
</html>
"""

class StatusHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if "json=1" in self.path or "/api" in self.path or "application/json" in self.headers.get("Accept", ""):
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
