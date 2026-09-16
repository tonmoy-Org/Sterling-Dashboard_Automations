# Dispatch Board Display Automation (Standalone)

This directory contains an independent, self-contained copy of the **Dispatch Board Display Automation Scraper**.

## Directory Contents
- `dispatch_board_display_automation_scraper.py` - Main automation scraper script
- `base_scraper.py` - Standalone BaseScraper class with Playwright integration
- `api_client.py` - Standalone API client helper
- `run_standalone.py` - Launcher script for running the automation
- `config/dispatch_board_template.json` - Configuration template mapping technicians and visual work orders
- `config/scraper_rules.json` - FieldEdge browser selectors and XPath configuration
- `.env` - Environment configuration file (credentials, URLs, and paths)
- `requirements.txt` - Python dependencies

## How to Run Independently

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install
```

### 2. Run Dry Run (Default: 2 days)
```bash
python dispatch_board_display_automation_scraper.py
# OR
python run_standalone.py
```

### 3. Run Live Mode on FieldEdge
```bash
python dispatch_board_display_automation_scraper.py --live --days 5
# OR
python run_standalone.py --live --days 5
```

### 4. Run specifying a Start Date
```bash
python run_standalone.py --live --days 7 --start-date "09/20/2026"
```
