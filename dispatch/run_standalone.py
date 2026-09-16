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

from base_scraper import PST_TZ, get_pst_now
from dispatch_board_display_automation_scraper import DispatchBoardDisplayAutomationScraper

STATUS_DATA = {
    "status": "online",
    "service": "Dispatch Board Display Automation",
    "mode": "DRY RUN",
    "days_configured": 30,
    "last_run": None,
    "last_run_pst": None,
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
    <title>Sterling Septic & Plumbing LLC Status</title>
    <link rel="icon" type="image/png" href="/assets/favicon.png">
    <link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Public Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
            -webkit-font-smoothing: antialiased;
        }

        /* Top Hero Banner matching exact Sterling design */
        .hero-banner {
            background: #1966c0;
            color: #ffffff;
            padding: 24px 32px 48px 32px;
            text-align: center;
        }
        .banner-top-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 1100px;
            margin: 0 auto 28px auto;
        }
        .logo-box {
            background: transparent;
            display: flex;
            align-items: center;
        }
        .logo-box img {
            max-height: 46px;
            object-fit: contain;
        }
        .btn-subscribe {
            background: #2375d8;
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 9px 24px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 14px;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.12);
            transition: background 0.2s;
        }
        .btn-subscribe:hover { background: #1d65c1; }

        .banner-title {
            font-size: 32px;
            font-weight: 800;
            margin-bottom: 6px;
            letter-spacing: -0.6px;
        }
        .banner-updated {
            font-size: 13px;
            color: #dbeafe;
            margin-bottom: 18px;
            font-weight: 500;
        }
        .banner-desc {
            max-width: 760px;
            margin: 0 auto;
            font-size: 13.5px;
            line-height: 1.6;
            color: #eff6ff;
            font-weight: 400;
        }

        /* Navigation Tabs Bar - Only LIVE UPDATES as requested */
        .nav-tabs-bar {
            background: #ffffff;
            border-bottom: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .nav-tabs-container {
            display: flex;
            justify-content: center;
            max-width: 1100px;
            margin: 0 auto;
        }
        .tab-btn {
            padding: 16px 20px;
            font-size: 13px;
            font-weight: 700;
            color: #1966c0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            cursor: pointer;
            border-bottom: 3px solid #1966c0;
        }

        /* Main Container */
        .main-container {
            max-width: 1080px;
            margin: 36px auto;
            padding: 0 16px;
        }

        /* Automation Log Card */
        .card {
            background: #ffffff;
            border-radius: 10px;
            border: 1px solid #cbd5e1;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
            overflow: hidden;
        }
        .card-header {
            background: #1966c0;
            color: #ffffff;
            padding: 14px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .card-header h2 { font-size: 15px; font-weight: 700; }
        .header-updated {
            font-size: 12.5px;
            color: #e2e8f0;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .spin-icon { cursor: pointer; transition: transform 0.4s ease; }
        .spin-icon:hover { transform: rotate(180deg); }

        /* Filter Controls Bar */
        .controls-bar {
            padding: 16px 24px;
            background: #fafafa;
            border-bottom: 1px solid #f1f5f9;
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }
        .input-search {
            padding: 8px 14px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            font-size: 13px;
            width: 250px;
            outline: none;
            font-family: inherit;
        }
        .select-filter {
            padding: 8px 14px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            font-size: 13px;
            background: #ffffff;
            outline: none;
            font-family: inherit;
        }

        /* Badges Section */
        .badges-bar {
            padding: 16px 24px;
            display: flex;
            gap: 12px;
            align-items: center;
            border-bottom: 1px solid #f1f5f9;
            flex-wrap: wrap;
        }
        .badge {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12.5px;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .badge-success { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }
        .badge-error { background: #ffe4e6; color: #be123c; border: 1px solid #fecdd3; }
        .badge-partial { background: #fef9c3; color: #a16207; border: 1px solid #fef08a; }
        .badge-running { background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }
        .badge-warning { background: #ffedd5; color: #c2410c; border: 1px solid #fed7aa; }

        /* Progress Bar Section */
        .progress-box {
            padding: 20px 24px;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
        }
        .progress-header-row {
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            font-weight: 700;
            color: #475569;
            margin-bottom: 8px;
        }
        .progress-bar-bg {
            background: #e2e8f0;
            height: 14px;
            border-radius: 7px;
            overflow: hidden;
        }
        .progress-bar-fill {
            background: linear-gradient(90deg, #1966c0, #2563eb);
            height: 100%;
            transition: width 0.5s ease;
        }

        /* Data Table */
        .table-wrap { width: 100%; overflow-x: auto; }
        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 13px;
        }
        th {
            background: #f8fafc;
            color: #64748b;
            font-weight: 700;
            padding: 14px 24px;
            border-bottom: 1px solid #e2e8f0;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }
        td {
            padding: 16px 24px;
            border-bottom: 1px solid #f1f5f9;
            color: #334155;
            font-weight: 500;
        }
        tr:hover td { background: #f8fafc; }
        .pst-tag { color: #64748b; font-size: 12px; font-weight: 600; margin-left: 4px; }

        /* Footer */
        .site-footer {
            text-align: center;
            padding: 32px 16px;
            color: #64748b;
            font-size: 13px;
            font-weight: 500;
        }
    </style>
</head>
<body>

    <div class="hero-banner">
        <div class="banner-top-bar">
            <div class="logo-box">
                <img src="/assets/logo.png" alt="Sterling Septic & Plumbing LLC" onerror="this.onerror=null; this.src='/assets/favicon.png';">
            </div>
            <button class="btn-subscribe">Subscribe</button>
        </div>
        <h1 class="banner-title">Sterling Services Operations Status</h1>
        <div class="banner-updated" id="bannerUpdatedText">Updated 0s ago • PST Timezone</div>
        <p class="banner-desc">
            Welcome to the Sterling Septic & Plumbing LLC Status Page. Bookmark or subscribe to this page for the latest on service performance and any major issues affecting your plumbing needs. We'll do our best to post updates immediately, but please note there may be a delay as we diagnose problems.
        </p>
    </div>

    <div class="nav-tabs-bar">
        <div class="nav-tabs-container">
            <div class="tab-btn">LIVE UPDATES</div>
        </div>
    </div>

    <div class="main-container">
        <div class="card">
            <div class="card-header">
                <h2>Automation Execution Logs</h2>
                <div class="header-updated">
                    <span id="cardUpdatedText">Updated 0s ago</span>
                    <span class="spin-icon" onclick="fetchStatus()">🔄</span>
                </div>
            </div>

            <div class="controls-bar">
                <input type="text" class="input-search" placeholder="Filter by scraper name..." value="dispatch-board-display-automation">
                <select class="select-filter">
                    <option>All statuses</option>
                    <option>Running</option>
                    <option>Success</option>
                    <option>Error</option>
                </select>
                <select class="select-filter">
                    <option>10 per scraper</option>
                    <option>25 per scraper</option>
                    <option>50 per scraper</option>
                </select>
            </div>

            <div class="badges-bar">
                <span class="badge badge-success" id="successBadge">0 Success</span>
                <span class="badge badge-error" id="errorBadge">0 Error</span>
                <span class="badge badge-partial" id="partialBadge">0 Partial</span>
                <span class="badge badge-running" id="runningBadge">1 Running</span>
            </div>

            <div class="progress-box">
                <div class="progress-header-row">
                    <span>30-Day FieldEdge Display Pre-Creation Progress</span>
                    <span id="pctLabel">0%</span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="progressBarFill" style="width: 0%;"></div>
                </div>
            </div>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Scraper Name</th>
                            <th>Active Target Date (PST)</th>
                            <th>Status</th>
                            <th>Batch Progress</th>
                            <th>Last Sync Time (PST)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>dispatch-board-display-automation</strong></td>
                            <td id="activeDateTd">-</td>
                            <td id="statusPillTd"><span class="badge badge-running">RUNNING</span></td>
                            <td id="progressTd">Day 0 of 30 (30 Days Left)</td>
                            <td id="lastSyncTd">- <span class="pst-tag">PST</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="site-footer">
        © 2026 Sterling Septic & Plumbing LLC • All rights reserved.
    </div>

    <script>
        let lastFetchTime = Date.now();
        
        async function fetchStatus() {
            try {
                const res = await fetch('/?json=1');
                const data = await res.json();
                lastFetchTime = Date.now();
                
                const p = data.progress || {};
                const curDay = p.current_day || 0;
                const total = p.total_days || data.days_configured || 30;
                const rem = p.remaining_days !== undefined ? p.remaining_days : (total - curDay);
                const pct = p.percent_complete !== undefined ? p.percent_complete : 0;
                
                document.getElementById('successBadge').innerText = curDay + ' Success';
                document.getElementById('pctLabel').innerText = pct + '%';
                document.getElementById('progressBarFill').style.width = pct + '%';
                
                document.getElementById('activeDateTd').innerText = p.current_date || 'Today';
                document.getElementById('progressTd').innerText = 'Day ' + curDay + ' of ' + total + ' (' + rem + ' Days Left)';
                document.getElementById('lastSyncTd').innerHTML = (data.last_run_pst || data.last_run || '-') + ' <span class="pst-tag">PST</span>';

                const statusStr = p.status || data.last_status || 'running';
                const msg = p.status_message || data.last_status || 'System Active';
                
                const statusPill = document.getElementById('statusPillTd');
                const runningBadge = document.getElementById('runningBadge');

                if (statusStr.includes('paused') || statusStr.includes('concurrent') || msg.includes('logged out')) {
                    statusPill.innerHTML = '<span class="badge badge-warning" title="' + msg + '">PAUSED (30m Retry)</span>';
                    runningBadge.className = 'badge badge-warning';
                    runningBadge.innerText = '1 Paused (Concurrent Login)';
                } else if (statusStr === 'completed' || data.last_status === 'success') {
                    statusPill.innerHTML = '<span class="badge badge-success">COMPLETED</span>';
                    runningBadge.className = 'badge badge-success';
                    runningBadge.innerText = '0 Running (Finished)';
                } else if (statusStr.includes('error')) {
                    statusPill.innerHTML = '<span class="badge badge-error">ERROR</span>';
                    runningBadge.className = 'badge badge-error';
                    runningBadge.innerText = '1 Error';
                } else {
                    statusPill.innerHTML = '<span class="badge badge-running">RUNNING</span>';
                    runningBadge.className = 'badge badge-running';
                    runningBadge.innerText = '1 Running';
                }

            } catch (err) {
                console.error('Failed to fetch status:', err);
            }
        }

        function updateRelativeTime() {
            const elapsedSec = Math.floor((Date.now() - lastFetchTime) / 1000);
            const text = 'Updated ' + elapsedSec + 's ago';
            document.getElementById('bannerUpdatedText').innerText = text + ' • PST Timezone';
            document.getElementById('cardUpdatedText').innerText = text;
        }

        setInterval(fetchStatus, 3000);
        setInterval(updateRelativeTime, 1000);
        fetchStatus();
    </script>
</body>
</html>
"""

class StatusHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/assets/") or self.path in ("/favicon.ico", "/logo.png", "/favicon.png"):
            asset_name = os.path.basename(self.path)
            asset_path = os.path.join(_dispatch_dir, "assets", asset_name)
            if not os.path.exists(asset_path):
                asset_path = os.path.join(_dispatch_dir, "assets", "logo.png" if "logo" in asset_name else "favicon.png")
            
            if os.path.exists(asset_path):
                self.send_response(200)
                content_type = "image/png" if asset_path.endswith(".png") else "image/x-icon"
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                with open(asset_path, "rb") as f:
                    self.wfile.write(f.read())
                return

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
    STATUS_DATA["last_run_pst"] = get_pst_now().strftime("%Y-%m-%d %I:%M:%S %p PST")

async def run_automation(args):
    STATUS_DATA["mode"] = "LIVE" if args.live else "DRY RUN"
    STATUS_DATA["days_configured"] = args.days
    STATUS_DATA["progress"]["total_days"] = args.days
    STATUS_DATA["progress"]["remaining_days"] = args.days

    scraper = DispatchBoardDisplayAutomationScraper()
    if args.loop:
        print(f"🔄 Loop Mode enabled. Running every {args.interval_hours} hours to maintain {args.days} pre-created days...")
        while True:
            now_pst = get_pst_now().strftime("%Y-%m-%d %I:%M:%S %p PST")
            print(f"\n⏰ [{now_pst}] Starting automation run for {args.days} days...")
            STATUS_DATA["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            STATUS_DATA["last_run_pst"] = now_pst
            STATUS_DATA["last_status"] = "running"
            try:
                await scraper.run(days=args.days, dry_run=not args.live, start_date_str=args.start_date, on_progress=on_progress_update)
                STATUS_DATA["last_status"] = "success"
            except Exception as e:
                err_str = str(e)
                print(f"❌ Error during scheduled run: {err_str}")
                STATUS_DATA["last_status"] = f"error: {err_str}"
                
                # Check for session logout / concurrent login
                if "login" in err_str.lower() or "session" in err_str.lower():
                    print("⚠️ FieldEdge single account concurrent login detected. Pausing for 30 minutes before auto-retry...")
                    for m in range(30, 0, -1):
                        msg = f"⚠️ Session logged out (Concurrent login detected). Retrying automatic login in {m} min (PST)..."
                        STATUS_DATA["progress"]["status"] = "paused_concurrent_login"
                        STATUS_DATA["progress"]["status_message"] = msg
                        await asyncio.sleep(60)

            sleep_seconds = int(args.interval_hours * 3600)
            print(f"\n😴 Run complete. Waiting {args.interval_hours} hours until next run. (Press Ctrl+C to stop)")
            await asyncio.sleep(sleep_seconds)
    else:
        now_pst = get_pst_now().strftime("%Y-%m-%d %I:%M:%S %p PST")
        STATUS_DATA["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATUS_DATA["last_run_pst"] = now_pst
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
