# GA4 User Simulator
![License](https://img.shields.io/github/license/paolobietolini/send-ga4-users)
![Python](https://img.shields.io/badge/python-≥3.11-blue)

Simulate GA4 users for testing purposes using a hybrid approach that combines browser automation with the Measurement Protocol.

Works on **Windows**, **macOS**, and **Linux**.

## Table of Contents

- [Why Hybrid?](#why-hybrid)
- [Requirements](#requirements)
- [Setup](#setup)
  - [Getting GA4 Credentials](#getting-ga4-credentials)
- [Usage](#usage)
- [CLI Options](#cli-options)
- [Simulation Modes](#simulation-modes)
  - [Which Mode Should I Use?](#which-mode-should-i-use)
- [Configuration](#configuration)
- [Events Sent Per User](#events-sent-per-user)
- [Troubleshooting](#troubleshooting)
  - [DNS Errors with High User Counts](#dns-errors-with-high-user-counts)
  - [Running Large Batches](#running-large-batches)
- [License](#license)

## Why Hybrid?

The GA4 Measurement Protocol alone **cannot create new users** - it's designed to augment existing data collected via gtag.js. This tool solves that by:

1. **Playwright** visits your site → creates a real GA4 session (triggers `session_start`, `first_visit`, `page_view` via gtag.js)
2. **Extracts** `client_id` from the `_ga` cookie
3. **Measurement Protocol** sends additional events using that `client_id` (fast HTTP calls)

Result: Users appear correctly in all GA4 reports.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- A GA4 property with Measurement Protocol API access
- **For hybrid/browser modes**: A website with GA4 installed (see [Which Mode Should I Use?](#which-mode-should-i-use))

## Setup

```bash
# Clone the repository
git clone https://github.com/paolobietolini/send-ga4-users.git
cd send-ga4-users

# Install dependencies
uv sync

# Install Playwright browser (one-time, required for hybrid/browser modes)
uv run playwright install chromium

# Configure your GA4 credentials
cp .env.example .env
# Edit .env with your values
```

### Getting GA4 Credentials

1. **Measurement ID**: Go to GA4 → Admin → Data Streams → Select your stream → Copy the Measurement ID (e.g., `G-XXXXXXXXXX`)

2. **MP Secret**: Go to GA4 → Admin → Data Streams → Select your stream → Measurement Protocol API secrets → Create

## Usage

```bash
# Simulate 10 users (hybrid mode - recommended)
uv run python main.py --users 10

# Fast MP-only mode (partial reporting, but very fast)
uv run python main.py --users 100 --mode mp

# Full browser simulation (slowest, most realistic)
uv run python main.py --users 5 --mode browser

# Use debug endpoint to validate events
uv run python main.py --users 10 --debug

# Override concurrent users (recommended for large batches)
uv run python main.py --users 1000 --mode mp --concurrent 10
```

## CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `-n, --users` | Number of users to simulate | 10 |
| `-m, --mode` | Simulation mode: `hybrid`, `browser`, `mp` | hybrid |
| `-d, --debug` | Use GA4 debug endpoint for validation | false |
| `-c, --concurrent` | Override max concurrent users | from .env |

## Simulation Modes

| Mode | Speed | Data Quality | Website Required |
|------|-------|--------------|------------------|
| `hybrid` | Medium | Full | ✅ Yes |
| `browser` | Slow | Full | ✅ Yes |
| `mp` | Fast | Partial | ❌ No |

### Which Mode Should I Use?

**`hybrid` (recommended)**
- Requires: A website with GA4 (gtag.js) installed
- How it works: Browser visits your site to create real sessions, then Measurement Protocol sends additional events
- Result: Users appear correctly in all GA4 reports with full data (geo, device, etc.)
- Best for: Testing GA4 setups, validating reports, realistic load testing

**`browser`**
- Requires: A website with GA4 (gtag.js) installed
- How it works: Full browser simulation for each user, all events fired via gtag.js
- Result: Most realistic data, identical to real users
- Best for: End-to-end testing, when you need 100% realistic behavior
- Downside: Slowest mode, resource intensive

**`mp` (Measurement Protocol only)**
- Requires: Only GA4 credentials (Measurement ID + API secret), no website needed
- How it works: Sends events directly to GA4 servers via HTTP
- Result: Events are recorded, but users may not appear correctly in all reports. Missing: geo data, device info, and some user metrics
- Best for: Quick event testing, debugging event payloads, when you don't have a website yet
- Downside: "Partial" users - GA4 documentation states MP is meant to augment existing data, not replace client-side tracking

**TL;DR**: If you have a website with GA4 installed, use `hybrid`. If you just want to test event payloads or don't have a website, use `mp` (but expect limited reporting).

## Configuration

Edit `.env` to customize:

```bash
# GA4 Configuration
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
GA4_MP_SECRET=your_secret_here

# Target Website (required for hybrid/browser modes)
TARGET_URL=https://your-website.com

# Simulation Settings
MAX_CONCURRENT_USERS=50      # Max parallel users
MAX_DAILY_USERS=1000         # Daily limit

# Session Settings
MIN_SESSION_DURATION_MS=5000
MAX_SESSION_DURATION_MS=120000
MIN_PAGES_PER_SESSION=1
MAX_PAGES_PER_SESSION=5
```

## Events Sent Per User

- `session_start` - Session begins
- `first_visit` - New user indicator
- `page_view` - Page navigation (multiple per session in hybrid mode)
- `user_engagement` - Time spent on site

## Troubleshooting

### DNS Errors with High User Counts

If you see errors like `[Errno -3] Temporary failure in name resolution` when simulating many users (500+), your DNS resolver is being overwhelmed by concurrent connections.

**Solution**: Reduce concurrency with the `--concurrent` flag:

```bash
# Instead of this (may fail with DNS errors):
uv run python main.py --users 1000 --mode mp

# Use this (works reliably):
uv run python main.py --users 1000 --mode mp --concurrent 10
```

**Recommended concurrency settings:**
- `--concurrent 10` - Safe for most systems (1000 users in ~25s)
- `--concurrent 20` - Faster, but may cause issues on some networks
- `--concurrent 50` - Only if you have a robust network/DNS setup

### Running Large Batches

For very large simulations, consider running in batches:

```bash
# Run 10 batches of 100 users each
for i in {1..10}; do
  uv run python main.py --users 100 --mode mp --concurrent 10
  sleep 5
done
```

## License

[BSD 3-Clause License](LICENSE)

