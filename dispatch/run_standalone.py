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

from datetime import datetime
from dispatch_board_display_automation_scraper import DispatchBoardDisplayAutomationScraper

async def run_automation(args):
    scraper = DispatchBoardDisplayAutomationScraper()
    if args.loop:
        print(f"🔄 Loop Mode enabled. Running every {args.interval_hours} hours to maintain {args.days} pre-created days...")
        while True:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n⏰ [{now_str}] Starting automation run for {args.days} days...")
            try:
                await scraper.run(days=args.days, dry_run=not args.live, start_date_str=args.start_date)
            except Exception as e:
                print(f"❌ Error during scheduled run: {e}")

            sleep_seconds = int(args.interval_hours * 3600)
            print(f"\n😴 Run complete. Waiting {args.interval_hours} hours until next run. (Press Ctrl+C to stop)")
            await asyncio.sleep(sleep_seconds)
    else:
        await scraper.run(days=args.days, dry_run=not args.live, start_date_str=args.start_date)

def main():
    parser = argparse.ArgumentParser(description="Run Dispatch Board Display Automation Scraper (Standalone)")
    parser.add_argument("--days", type=int, default=30, help="Number of days to process (default: 30)")
    parser.add_argument("--live", action="store_true", help="Run live on FieldEdge (skips dry-run)")
    parser.add_argument("--start-date", type=str, help="Starting date (e.g. 'August 15', '08/15/2026'). Defaults to today.")
    parser.add_argument("--loop", action="store_true", help="Run continuously on a scheduled interval (e.g. daily)")
    parser.add_argument("--interval-hours", type=float, default=24.0, help="Interval between runs in hours when --loop is set (default: 24)")
    args = parser.parse_args()

    print(f"🚀 Starting Dispatch Board Display Automation Scraper (Standalone)...")
    print(f"   Mode: {'LIVE' if args.live else 'DRY RUN'}")
    print(f"   Days: {args.days}")
    if args.start_date:
        print(f"   Start Date: {args.start_date}")
    if args.loop:
        print(f"   Loop Schedule: Every {args.interval_hours} hours")

    asyncio.run(run_automation(args))

if __name__ == "__main__":
    main()
