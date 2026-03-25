@echo off
REM setup.bat - Install Python dependencies on Windows

echo ╔════════════════════════════════════════════════════════════╗
echo ║  AI-NEWSROOM SETUP - Installing Dependencies (Windows)    ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

echo Checking Python installation...
python --version

echo.
echo Step 1: Upgrading pip...
python -m pip install --upgrade pip setuptools wheel

echo.
echo Step 2: Installing project dependencies...
echo  This may take 5-10 minutes on first install...
echo.

pip install ^
  feedparser==6.0.11 ^
  newspaper3k==0.2.8 ^
  requests==2.31.0 ^
  beautifulsoup4==4.12.2 ^
  rapidfuzz==3.6.1 ^
  sentence-transformers==2.7.0 ^
  sqlalchemy==2.0.28 ^
  psycopg2-binary==2.9.9 ^
  python-dotenv==1.0.1 ^
  langdetect==1.0.9 ^
  pydantic==2.6.4 ^
  APScheduler==3.10.4 ^
  fastapi==0.110.0 ^
  uvicorn==0.29.0

echo.
echo Step 3: Verifying imports...
python -c "import feedparser, newspaper, requests, beautifulsoup4, rapidfuzz, sqlalchemy; print('✓ All packages installed!')" 

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║  SETUP COMPLETE!                                           ║
echo ╠════════════════════════════════════════════════════════════╣
echo ║  Next:                                                      ║
echo ║  1. Create .env file with your API keys                   ║
echo ║  2. Run: python backend/tests/test_pipeline_simple.py      ║
echo ║  3. See TESTING_GUIDE.md for examples                     ║
echo ╚════════════════════════════════════════════════════════════╝
pause
