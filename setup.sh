#!/bin/bash

# Vision Service Setup Script

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}👁️  Vision Service Setup${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.8+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Found Python $PYTHON_VERSION${NC}"
echo ""

# Create virtual environment
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment already exists${NC}"
    read -p "Remove and recreate? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing old virtual environment..."
        rm -rf venv
    else
        echo "Keeping existing virtual environment"
        exit 0
    fi
fi

echo "Creating Python virtual environment..."
python3 -m venv venv
echo -e "${GREEN}✅ Virtual environment created${NC}"
echo ""

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --quiet --upgrade pip
echo -e "${GREEN}✅ pip upgraded${NC}"
echo ""

# Install dependencies
echo "Installing dependencies..."
echo "(This may take a few minutes for first-time setup)"

# Install in stages to avoid dependency conflicts
echo "  • Installing core dependencies..."
pip install --quiet setuptools wheel
pip install --quiet fastapi uvicorn python-dotenv httpx psutil

echo "  • Installing image processing..."
pip install --quiet "numpy>=1.24.0,<2.0.0" Pillow mss

echo "  • Installing OpenCV (headless)..."
pip install --quiet opencv-python-headless

echo "  • Installing PaddlePaddle..."
pip install --quiet paddlepaddle

echo "  • Installing PaddleOCR..."
pip install --quiet paddleocr

echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Download OCR models (first time only)
echo "Checking OCR models..."
python3 -c "from paddleocr import PaddleOCR; PaddleOCR(use_textline_orientation=True, lang='en')" 2>/dev/null && {
    echo -e "${GREEN}✅ OCR models ready${NC}"
} || {
    echo -e "${YELLOW}Downloading OCR models (~100MB, first time only)...${NC}"
    python3 -c "from paddleocr import PaddleOCR; PaddleOCR(use_textline_orientation=True, lang='en')"
    echo -e "${GREEN}✅ OCR models downloaded${NC}"
}
echo ""

# Check .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found, copying from .env.example${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ .env file created${NC}"
    echo -e "${YELLOW}💡 Edit .env to configure VLM and other settings${NC}"
else
    echo -e "${GREEN}✅ .env file exists${NC}"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Vision Service Setup Complete!${NC}"
echo ""
echo "📝 Next steps:"
echo "   1. Review/edit .env file if needed"
echo "   2. Start service: ./start.sh"
echo "   3. Test service: python3 test_service.py"
echo ""
echo "💡 Tips:"
echo "   • VLM is disabled by default (fast startup)"
echo "   • Enable VLM: Set VLM_ENABLED=true in .env"
echo "   • VLM requires ~2.4GB download on first use"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
