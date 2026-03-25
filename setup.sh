#!/bin/bash
# setup.sh - Install Python dependencies and prepare AI-Newsroom for testing

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  AI-NEWSROOM SETUP - Installing Dependencies              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "✓ Checking Python installation..."
python3 --version

echo ""
echo "Step 1: Upgrading pip..."
python3 -m pip install --upgrade pip setuptools wheel --break-system-packages

echo ""
echo "Step 2: Installing project dependencies..."
echo "  This may take 5-10 minutes on first install..."
echo ""

pip3 install --break-system-packages \
  feedparser==6.0.11 \
  newspaper3k==0.2.8 \
  requests==2.31.0 \
  beautifulsoup4==4.12.2 \
  rapidfuzz==3.6.1 \
  sentence-transformers==2.7.0 \
  sqlalchemy==2.0.28 \
  psycopg2-binary==2.9.9 \
  python-dotenv==1.0.1 \
  langdetect==1.0.9 \
  pydantic==2.6.4 \
  APScheduler==3.10.4 \
  fastapi==0.110.0 \
  uvicorn==0.29.0

echo ""
echo "✓ Installation complete!"
echo ""
echo "Step 3: Verifying imports..."
python3 -c "
import feedparser
import newspaper
import requests
import beautifulsoup4
import rapidfuzz
import sqlalchemy
print('✓ All packages imported successfully!')
" && echo "✓ Setup successful!" || echo "✗ Some packages failed to import"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  NEXT STEPS:                                               ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  1. Create .env file with your API keys:                   ║"
echo "║     cp backend/.env.example .env                           ║"
echo "║     (Edit .env with NEWSAPI_KEY, etc.)                    ║"
echo "║                                                             ║"
echo "║  2. Run tests:                                             ║"
echo "║     python3 backend/tests/test_pipeline_simple.py          ║"
echo "║                                                             ║"
echo "║  3. Test individual collectors:                           ║"
echo "║     See TESTING_GUIDE.md for examples                     ║"
echo "║                                                             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
