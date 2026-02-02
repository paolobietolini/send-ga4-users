# GA4 User Simulator

Simulate GA4 users for testing purposes using a hybrid approach that combines browser automation with the Measurement Protocol.

## Why Hybrid?

The GA4 Measurement Protocol alone **cannot create new users** - it's designed to augment existing data collected via gtag.js. This tool solves that by:

1. **Playwright** visits your site → creates a real GA4 session (triggers `session_start`, `first_visit`, `page_view` via gtag.js)
2. **Extracts** `client_id` from the `_ga` cookie
3. **Measurement Protocol** sends additional events using that `client_id` (fast HTTP calls)

Result: Users appear correctly in all GA4 reports.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- A website with GA4 installed

## Setup

```bash
# Clone the repository
git clone https://github.com/paolobietolini/send-ga4-users.git
cd send-ga4-users

# Install dependencies
uv sync

# Install Playwright browser (one-time)
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

# Override concurrent users
uv run python main.py --users 50 --concurrent 10
```

## CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `-n, --users` | Number of users to simulate | 10 |
| `-m, --mode` | Simulation mode: `hybrid`, `browser`, `mp` | hybrid |
| `-d, --debug` | Use GA4 debug endpoint for validation | false |
| `-c, --concurrent` | Override max concurrent users | from .env |

## Simulation Modes

| Mode | Speed | Data Quality | Use Case |
|------|-------|--------------|----------|
| `hybrid` | Medium | Full | Recommended for most testing |
| `browser` | Slow | Full | Most realistic simulation |
| `mp` | Fast | Partial | Load testing, event debugging |

## Configuration

Edit `.env` to customize:

```bash
# GA4 Configuration
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
GA4_MP_SECRET=your_secret_here

# Target Website
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

## License

MIT
