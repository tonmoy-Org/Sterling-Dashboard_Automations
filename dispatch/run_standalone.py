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
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Public Sans', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
                    },
                    colors: {
                        sterling: {
                            DEFAULT: '#1966c0',
                            dark: '#124d93',
                            light: '#2375d8',
                            bg: '#f8fafc'
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-slate-50 text-slate-900 font-sans antialiased min-h-screen flex flex-col justify-between">

    <!-- Top Site Navbar (Matching Sterling Main Website Header) -->
    <header class="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
        <div class="max-w-6xl mx-auto px-4 sm:px-8 py-3.5 flex justify-between items-center">
            <!-- Left: Company Logo -->
            <div class="flex items-center">
                <a href="javascript:void(0)" class="flex items-center">
                    <img src="/assets/logo.png" alt="Sterling Septic & Plumbing, LLC" class="h-9 sm:h-11 w-auto object-contain" onerror="this.onerror=null; this.src='/assets/favicon.png';">
                </a>
            </div>

            <!-- Right: Menu Links & Phone Number Button (No routing) -->
            <div class="flex items-center space-x-3 sm:space-x-6">
                <a href="javascript:void(0)" class="text-xs sm:text-sm font-bold text-slate-900 hover:text-sterling transition-colors hidden md:inline-block">Services</a>
                <a href="javascript:void(0)" class="text-xs sm:text-sm font-bold text-slate-900 hover:text-sterling transition-colors hidden md:inline-block">Cities We Serve</a>
                <a href="javascript:void(0)" class="text-xs sm:text-sm font-bold text-slate-900 hover:text-sterling transition-colors hidden sm:inline-block">Contact Us</a>
                <a href="javascript:void(0)" class="text-xs sm:text-sm font-bold text-slate-900 hover:text-sterling transition-colors hidden sm:inline-block">Blog</a>
                <a href="javascript:void(0)" class="bg-[#6ba4d8] hover:bg-[#5a93c7] text-white px-3.5 py-2 rounded-md text-xs sm:text-sm font-bold shadow-sm transition-all duration-200">
                    (253) 342-4061
                </a>
            </div>
        </div>
    </header>

    <!-- Status Hero Banner (Clean White Theme) -->
    <section class="bg-white border-b border-slate-200 py-10 px-4 sm:px-8">
        <div class="max-w-3xl mx-auto text-center">
            <h1 class="text-2xl sm:text-4xl font-extrabold text-sterling tracking-tight mb-2">Sterling Services Operations Status</h1>
            <div id="bannerUpdatedText" class="text-xs sm:text-sm text-slate-500 font-medium mb-4">Updated 0s ago • PST Timezone</div>
            <p class="text-xs sm:text-sm leading-relaxed text-slate-600 font-normal">
                Welcome to the Sterling Septic & Plumbing LLC Status Page. Bookmark or subscribe to this page for the latest on service performance and any major issues affecting your plumbing needs. We'll do our best to post updates immediately, but please note there may be a delay as we diagnose problems.
            </p>
        </div>
    </section>

    <!-- Navigation Bar - LIVE UPDATES tab only -->
    <nav class="bg-white border-b border-slate-200 shadow-sm">
        <div class="max-w-6xl mx-auto flex justify-center">
            <div class="text-sterling font-bold text-xs sm:text-sm border-b-2 border-sterling py-3.5 px-6 uppercase tracking-wider">
                LIVE UPDATES
            </div>
        </div>
    </nav>

    <!-- Main Container -->
    <main class="max-w-5xl mx-auto px-4 py-8 flex-grow w-full">
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <!-- Card Header -->
            <div class="bg-sterling text-white px-6 py-4 flex justify-between items-center">
                <h2 class="text-sm sm:text-base font-bold tracking-wide">Automation Execution Logs</h2>
                <div class="text-xs text-blue-100 flex items-center gap-2">
                    <span id="cardUpdatedText">Updated 0s ago</span>
                    <button onclick="fetchStatus()" title="Refresh" class="hover:rotate-180 transition-transform duration-300">🔄</button>
                </div>
            </div>

            <!-- Controls Bar -->
            <div class="bg-slate-50 border-b border-slate-100 px-6 py-3.5 flex flex-wrap gap-3 items-center">
                <input type="text" class="px-3.5 py-1.5 border border-slate-300 rounded-md text-xs w-full sm:w-64 focus:ring-2 focus:ring-blue-500 focus:outline-none" placeholder="Filter by scraper name..." value="dispatch-board-display-automation">
                <select class="px-3 py-1.5 border border-slate-300 rounded-md text-xs bg-white text-slate-700 focus:ring-2 focus:ring-blue-500 focus:outline-none">
                    <option>All statuses</option>
                    <option>Running</option>
                    <option>Success</option>
                    <option>Error</option>
                </select>
                <select class="px-3 py-1.5 border border-slate-300 rounded-md text-xs bg-white text-slate-700 focus:ring-2 focus:ring-blue-500 focus:outline-none">
                    <option>10 per scraper</option>
                    <option>25 per scraper</option>
                    <option>50 per scraper</option>
                </select>
            </div>

            <!-- Badges Section -->
            <div class="px-6 py-3.5 border-b border-slate-100 flex flex-wrap gap-2.5 items-center bg-white">
                <span id="successBadge" class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">0 Success</span>
                <span id="errorBadge" class="px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">0 Error</span>
                <span id="partialBadge" class="px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">0 Partial</span>
                <span id="runningBadge" class="px-3 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">1 Running</span>
            </div>

            <!-- Progress Bar Section -->
            <div class="px-6 py-4 bg-slate-50/70 border-b border-slate-200">
                <div class="flex justify-between text-xs font-bold text-slate-600 mb-2">
                    <span>30-Day FieldEdge Display Pre-Creation Progress</span>
                    <span id="pctLabel">0%</span>
                </div>
                <div class="w-full bg-slate-200 rounded-full h-3.5 overflow-hidden p-0.5">
                    <div id="progressBarFill" class="bg-gradient-to-r from-blue-600 to-indigo-600 h-full rounded-full transition-all duration-500 ease-out" style="width: 0%;"></div>
                </div>
            </div>

            <!-- Table Wrap -->
            <div class="overflow-x-auto">
                <table class="w-full text-left text-xs sm:text-sm text-slate-700">
                    <thead class="bg-slate-50 text-slate-500 font-bold uppercase text-[11px] tracking-wider border-b border-slate-200">
                        <tr>
                            <th class="px-6 py-3.5">Scraper Name</th>
                            <th class="px-6 py-3.5">Active Target Date (PST)</th>
                            <th class="px-6 py-3.5">Status</th>
                            <th class="px-6 py-3.5">Batch Progress</th>
                            <th class="px-6 py-3.5">Last Sync Time (PST)</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                        <tr class="hover:bg-slate-50 transition-colors">
                            <td class="px-6 py-4 font-bold text-slate-900">dispatch-board-display-automation</td>
                            <td id="activeDateTd" class="px-6 py-4 font-medium">-</td>
                            <td id="statusPillTd" class="px-6 py-4">
                                <span class="px-2.5 py-1 rounded-md text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">RUNNING</span>
                            </td>
                            <td id="progressTd" class="px-6 py-4 font-medium">Day 0 of 30 (30 Days Left)</td>
                            <td id="lastSyncTd" class="px-6 py-4 font-medium">- <span class="text-xs font-semibold text-slate-400 ml-1">PST</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="text-center py-6 text-xs font-medium text-slate-500 border-t border-slate-200/80 bg-white">
        © 2026 Sterling Septic & Plumbing LLC • All rights reserved.
    </footer>

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
                document.getElementById('lastSyncTd').innerHTML = (data.last_run_pst || data.last_run || '-') + ' <span class="text-xs font-semibold text-slate-400 ml-1">PST</span>';

                const statusStr = p.status || data.last_status || 'running';
                const msg = p.status_message || data.last_status || 'System Active';
                
                const statusPill = document.getElementById('statusPillTd');
                const runningBadge = document.getElementById('runningBadge');

                if (statusStr.includes('paused') || statusStr.includes('concurrent') || msg.includes('logged out')) {
                    statusPill.innerHTML = '<span class="px-2.5 py-1 rounded-md text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200" title="' + msg + '">PAUSED (30m Retry)</span>';
                    runningBadge.className = 'px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200';
                    runningBadge.innerText = '1 Paused (Concurrent Login)';
                } else if (statusStr === 'completed' || data.last_status === 'success') {
                    statusPill.innerHTML = '<span class="px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">COMPLETED</span>';
                    runningBadge.className = 'px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200';
                    runningBadge.innerText = '0 Running (Finished)';
                } else if (statusStr.includes('error')) {
                    statusPill.innerHTML = '<span class="px-2.5 py-1 rounded-md text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">ERROR</span>';
                    runningBadge.className = 'px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200';
                    runningBadge.innerText = '1 Error';
                } else {
                    statusPill.innerHTML = '<span class="px-2.5 py-1 rounded-md text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">RUNNING</span>';
                    runningBadge.className = 'px-3 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200';
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

        setInterval(fetchStatus, 2000);
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
