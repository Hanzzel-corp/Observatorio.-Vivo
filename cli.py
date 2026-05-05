#!/usr/bin/env python3
"""
Observatorio Vivo CLI
Command line interface for managing the Observatorio Vivo backend.
"""

import argparse
import sys
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent


def run_server(args):
    """Start the FastAPI server."""
    print("🚀 Starting Observatorio Vivo server...")
    os.chdir(REPO_ROOT)
    subprocess.run([sys.executable, "app.py"])


def run_tests(args):
    """Run the test suite."""
    print("🧪 Running tests...")
    os.chdir(REPO_ROOT)
    result = subprocess.run([sys.executable, "-m", "pytest", "test_core.py", "-v"])
    sys.exit(result.returncode)


def setup_db(args):
    """Initialize the database."""
    print("🗄️  Initializing database...")
    os.chdir(REPO_ROOT)
    from modules.database import init_db
    init_db()
    print("✅ Database initialized")


def status(args):
    """Check system status."""
    print("📊 Observatorio Vivo Status")
    print("=" * 40)

    # Check database
    db_path = REPO_ROOT / "data" / "observatorio.db"
    if db_path.exists():
        size = db_path.stat().st_size / 1024
        print(f"🗄️  Database: {size:.1f} KB")
    else:
        print("⚠️  Database: Not initialized")

    # Check modules
    modules_dir = REPO_ROOT / "modules"
    if modules_dir.exists():
        py_files = list(modules_dir.glob("*.py"))
        print(f"📦 Modules: {len(py_files)} loaded")

    print(f"📁 Repository: {REPO_ROOT}")


def shell(args):
    """Open interactive shell with app context."""
    print("🐍 Opening interactive shell...")
    os.chdir(REPO_ROOT)
    subprocess.run([sys.executable, "-i", "-c",
        "from modules.database import init_db; from modules.models import *; print('Context loaded: init_db, models')"])


def main():
    parser = argparse.ArgumentParser(
        prog='ov',
        description='Observatorio Vivo CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py server      # Start the server
  python cli.py test        # Run tests
  python cli.py init        # Setup database
  python cli.py status      # Check status
  python cli.py shell       # Interactive shell
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Server command
    server_parser = subparsers.add_parser('server', help='Start the FastAPI server')
    server_parser.set_defaults(func=run_server)

    # Test command
    test_parser = subparsers.add_parser('test', help='Run tests')
    test_parser.set_defaults(func=run_tests)

    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize database')
    init_parser.set_defaults(func=setup_db)

    # Status command
    status_parser = subparsers.add_parser('status', help='Check system status')
    status_parser.set_defaults(func=status)

    # Shell command
    shell_parser = subparsers.add_parser('shell', help='Open interactive shell')
    shell_parser.set_defaults(func=shell)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()
