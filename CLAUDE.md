# CLAUDE.md

Context for future Claude instances working on this project.

## What This Project Does

Simulates GA4 users for testing purposes. The key insight is that GA4's Measurement Protocol **cannot create new users** - it only augments existing sessions. So we use a hybrid approach:

1. Playwright browser visits the target site → gtag.js fires → real session created
2. Extract `client_id` from `_ga` cookie
3. Use Measurement Protocol for fast subsequent events

## Project Structure

```
send_ga4_users/
├── main.py                 # CLI entry point (argparse)
├── config.py               # Loads .env, dataclasses for config
├── measurement_protocol.py # Async HTTP client for GA4 MP
├── browser_session.py      # Playwright session management
├── user_simulator.py       # Orchestrates simulation modes
├── pyproject.toml          # uv project config
└── .env                    # User's GA4 credentials (not in git)
```

## Key Technical Decisions

### Why Hybrid Approach?
MP-only creates "partial" users that don't appear correctly in GA4 reports. Browser-only is too slow. Hybrid gets the best of both.

### Concurrency Limits
- Browser/hybrid modes: capped at 10 concurrent (browsers are heavy)
- MP mode: capped at 20 concurrent (DNS can be overwhelmed)
- User discovered 1000 users with high concurrency causes DNS resolution failures
- Solution: `--concurrent 10` flag works reliably

### Retry Logic
- MP client retries 3x with exponential backoff (0.5s, 1s, 2s)
- Browser sessions retry 3x with backoff
- Catches `ConnectError`, `TimeoutException`, `OSError`

### Page Load Strategy
Changed from `wait_until="networkidle"` to `wait_until="domcontentloaded"` - faster and more reliable, especially under load.

## Common Issues

### DNS Errors with High User Counts
`[Errno -3] Temporary failure in name resolution` - reduce concurrency with `--concurrent 10`

### Browser ERR_ABORTED
Too many concurrent browser sessions. The code now caps at 10 and uses batching.

### "Future exception was never retrieved"
Fixed by processing `asyncio.gather` results properly and using batched execution instead of launching all tasks at once.

## GA4 Measurement Protocol Notes

Required for events to appear in Realtime reports:
- `session_id` (timestamp when session started)
- `engagement_time_msec` (even 100ms works)

Client ID format: `XXXXXXXXXX.XXXXXXXXXX` (two numbers separated by dot)

Endpoint: `https://www.google-analytics.com/mp/collect?measurement_id=G-XXX&api_secret=YYY`

Debug endpoint: Same but `/debug/mp/collect` - returns validation JSON.

## Testing

```bash
# Quick test (MP only, no website needed)
uv run python main.py --users 3 --mode mp --debug

# Full test (needs website with GA4)
uv run python main.py --users 10 --mode hybrid

# Load test
uv run python main.py --users 1000 --mode mp --concurrent 10
```

## Dependencies

- `playwright` - browser automation
- `httpx` - async HTTP client
- `python-dotenv` - .env loading
- `faker` - (imported but not heavily used yet, for future user data generation)
