#!/usr/bin/env python3
"""
GA4 User Simulator

Simulates users for GA4 testing using a hybrid approach:
1. Playwright bootstraps real browser sessions (creates actual users)
2. Measurement Protocol sends additional events (fast)

Usage:
    python main.py --users 10 --mode hybrid
    python main.py --users 100 --mode mp --debug
    python main.py --users 5 --mode browser
"""

import argparse
import asyncio
import sys

from config import load_config
from user_simulator import SimulationMode, run_simulation


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Simulate GA4 users for testing purposes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  hybrid   - Browser bootstrap + Measurement Protocol events (recommended)
  browser  - Full browser simulation (slowest, most realistic)
  mp       - Measurement Protocol only (fastest, partial reporting)

Examples:
  %(prog)s --users 10                    # Simulate 10 users (hybrid mode)
  %(prog)s --users 50 --mode mp --debug  # Fast simulation with debug
  %(prog)s --users 5 --mode browser      # Full browser simulation
        """,
    )

    parser.add_argument(
        "-n",
        "--users",
        type=int,
        default=10,
        help="Number of users to simulate (default: 10)",
    )

    parser.add_argument(
        "-m",
        "--mode",
        type=str,
        choices=["hybrid", "browser", "mp"],
        default="hybrid",
        help="Simulation mode (default: hybrid)",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Use GA4 debug endpoint for validation",
    )

    parser.add_argument(
        "-c",
        "--concurrent",
        type=int,
        help="Override max concurrent users from config",
    )

    return parser.parse_args()


def print_banner() -> None:
    """Print application banner."""
    print(
        """
╔═══════════════════════════════════════╗
║       GA4 User Simulator v1.0         ║
║   Hybrid Browser + MP Simulation      ║
╚═══════════════════════════════════════╝
"""
    )


def print_config(config, args) -> None:
    """Print configuration summary."""
    mode_map = {
        "hybrid": SimulationMode.HYBRID,
        "browser": SimulationMode.BROWSER_ONLY,
        "mp": SimulationMode.MP_ONLY,
    }
    mode = mode_map[args.mode]

    print("Configuration:")
    print(f"  Target URL:       {config.simulation.target_url}")
    print(f"  Measurement ID:   {config.ga4.measurement_id}")
    print(f"  Mode:             {mode.value}")
    print(f"  Users to create:  {args.users}")
    print(f"  Max concurrent:   {config.simulation.max_concurrent_users}")
    print(f"  Debug mode:       {'Yes' if args.debug else 'No'}")
    print()


def print_stats(stats) -> None:
    """Print simulation statistics."""
    print()
    print("═" * 40)
    print("Simulation Complete!")
    print("═" * 40)
    print(f"  Users created:    {stats.users_created}")
    print(f"  Events sent:      {stats.events_sent}")
    print(f"  Errors:           {stats.errors}")
    print(f"  Duration:         {stats.duration_seconds:.2f}s")
    print(f"  Users/second:     {stats.users_per_second:.2f}")
    print()


async def main() -> int:
    """Main entry point."""
    args = parse_args()

    print_banner()

    try:
        config = load_config()
    except KeyError as e:
        print(f"Error: Missing environment variable {e}")
        print("Please check your .env file")
        return 1

    # Override concurrent users if specified
    if args.concurrent:
        config.simulation.max_concurrent_users = args.concurrent

    print_config(config, args)

    # Map string mode to enum
    mode_map = {
        "hybrid": SimulationMode.HYBRID,
        "browser": SimulationMode.BROWSER_ONLY,
        "mp": SimulationMode.MP_ONLY,
    }
    mode = mode_map[args.mode]

    print(f"Starting simulation with {args.users} users...")
    print()

    try:
        stats = await run_simulation(
            config=config,
            num_users=args.users,
            mode=mode,
            debug=args.debug,
        )
        print_stats(stats)

        if stats.errors > 0:
            print(f"Warning: {stats.errors} errors occurred during simulation")
            return 1

        return 0

    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
        return 130


def cli_entry() -> None:
    """Entry point for uv/pip script."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli_entry()
