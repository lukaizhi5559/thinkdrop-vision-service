#!/bin/bash

# Vision Service Startup Script

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}👁️  Starting Vision Service...${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found, copying from .env.example${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env with your configuration${NC}"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check if PaddleOCR models need to be downloaded
echo -e "${GREEN}Checking OCR models...${NC}"
python3 -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='en', show_log=False)" 2>/dev/null || {
    echo -e "${YELLOW}Downloading OCR models (first time only, ~100MB)...${NC}"
}

# Start server
echo -e "${GREEN}Starting FastAPI server...${NC}"
python3 server.py
