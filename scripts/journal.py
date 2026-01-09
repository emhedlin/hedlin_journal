#!/usr/bin/env python3
"""
Convenience wrapper for Hedlin Family Journal commands.

Usage:
    python scripts/journal.py build
    python scripts/journal.py serve
    python scripts/journal.py pdf
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, description: str = None) -> int:
    """Run a command and return exit code."""
    if description:
        print(f"\n{description}...")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Hedlin Family Journal - Convenience Commands",
        add_help=False
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Build command
    build_parser = subparsers.add_parser('build', help='Build the site')
    build_parser.add_argument('--dev', '-d', action='store_true', help='Fast dev build')
    build_parser.add_argument('--force', '-f', action='store_true', help='Force rebuild')

    # Serve command
    serve_parser = subparsers.add_parser('serve', help='Start dev server')
    serve_parser.add_argument('--port', '-p', type=int, default=8000, help='Port number')

    # PDF command
    pdf_parser = subparsers.add_parser('pdf', help='Generate PDFs')
    pdf_parser.add_argument('--individual', '-i', action='store_true', help='Individual entry PDFs')

    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize environment')

    # Help command
    subparsers.add_parser('help', help='Show this help message')

    args = parser.parse_args()

    if args.command == 'build':
        cmd = ['python', 'scripts/build_all.py']
        if args.dev:
            cmd.append('--dev')
        if args.force:
            cmd.append('--force')
        return run_command(cmd, "Building site")

    elif args.command == 'serve':
        cmd = ['python', 'scripts/serve.py', '--port', str(args.port)]
        return run_command(cmd, f"Starting server on port {args.port}")

    elif args.command == 'pdf':
        cmd = ['python', 'scripts/generate_pdf.py']
        if args.individual:
            cmd.append('--individual')
        return run_command(cmd, "Generating PDFs")

    elif args.command == 'init':
        print("Initializing Hedlin Family Journal...")
        print("\n1. Creating virtual environment...")
        subprocess.run(['uv', 'venv'])
        print("\n2. Installing dependencies...")
        subprocess.run(['uv', 'pip', 'install', '-r', 'requirements.txt'])
        print("\n3. Creating directories...")
        Path('docs').mkdir(exist_ok=True)
        print("\n✓ Initialization complete!")
        print("\nNext steps:")
        print("  1. Place your DOCX files in the docs/ directory")
        print("  2. Run: python scripts/journal.py build")
        print("  3. Run: python scripts/journal.py serve")
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
