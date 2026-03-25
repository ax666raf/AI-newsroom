#!/usr/bin/env python3
"""
setup.py - Cross-platform setup script for AI-Newsroom dependencies

Usage:
    python3 setup.py
or:
    python setup.py (on Windows)
"""

import subprocess
import sys
import os

PACKAGES = [
    "feedparser==6.0.11",
    "newspaper3k==0.2.8",
    "requests==2.31.0",
    "beautifulsoup4==4.12.2",
    "rapidfuzz==3.6.1",
    "sentence-transformers==2.7.0",
    "sqlalchemy==2.0.28",
    "psycopg2-binary==2.9.9",
    "python-dotenv==1.0.1",
    "langdetect==1.0.9",
    "pydantic==2.6.4",
    "APScheduler==3.10.4",
    "fastapi==0.110.0",
    "uvicorn==0.29.0",
]


def print_header(text):
    """Print formatted header."""
    print("\n╔" + "═" * 60 + "╗")
    print("║ " + text.center(58) + " ║")
    print("╚" + "═" * 60 + "╝\n")


def run_command(cmd):
    """Run shell command and return success status."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def main():
    print_header("AI-NEWSROOM Setup")
    
    # Check Python version
    print("✓ Python version:", sys.version.split()[0])
    
    # Upgrade pip
    print("\nStep 1: Upgrading pip...")
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"]
    success, _, err = run_command(cmd)
    
    if success:
        print("✓ pip upgraded successfully")
    else:
        print("⚠ pip upgrade warning (continuing anyway):", err[:100])
    
    # Try with --break-system-packages if on Ubuntu
    extra_args = []
    if sys.platform == "linux" and os.path.exists("/etc/os-release"):
        extra_args = ["--break-system-packages"]
    
    # Install packages
    print("\nStep 2: Installing dependencies...")
    print(f"  Installing {len(PACKAGES)} packages (this may take 5-10 minutes)...\n")
    
    cmd = [sys.executable, "-m", "pip", "install"] + extra_args + PACKAGES
    
    # Run with output to show progress
    try:
        subprocess.run(cmd, check=False)
    except Exception as e:
        print(f"✗ Installation failed: {e}")
        return False
    
    # Verify imports
    print("\n\nStep 3: Verifying installation...")
    test_imports = [
        "feedparser",
        "requests",
        "bs4",  # beautifulsoup4
        "rapidfuzz",
        "sqlalchemy",
        "fastapi",
    ]
    
    failed = []
    for pkg in test_imports:
        try:
            __import__(pkg)
            print(f"  ✓ {pkg}")
        except ImportError:
            print(f"  ✗ {pkg} - FAILED")
            failed.append(pkg)
    
    if failed:
        print(f"\n✗ Some packages failed to import: {', '.join(failed)}")
        print("Try running: pip install --upgrade --force-reinstall " + " ".join(failed))
        return False
    
    # Success
    print_header("Setup Complete!")
    
    print("NEXT STEPS:")
    print("───────────────────────────────────────────────")
    print("")
    print("1. Create your .env file with API keys:")
    print("   $ cp backend/.env.example .env")
    print("   $ edit .env  (add NEWSAPI_KEY, APIFY_TOKEN, etc)")
    print("")
    print("2. Run the test suite:")
    print("   $ python3 backend/tests/test_pipeline_simple.py")
    print("")
    print("3. Test data collection:")
    print("   $ python3 -c 'from backend.collector.rss_collector import fetch_all_rss'")
    print("   $ python3 -c 'articles = fetch_all_rss(limit_per_source=2); print(len(articles))'")
    print("")
    print("See TESTING_GUIDE.md for more examples and troubleshooting.")
    print("")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
