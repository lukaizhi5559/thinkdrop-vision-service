"""
Vision MCP Service
Provides screen capture, OCR, and VLM capabilities for ThinkDrop AI
"""

import os
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from src.middleware.validation import validate_api_key
from src.routes.capture import router as capture_router
from src.routes.ocr import router as ocr_router
from src.routes.describe import router as describe_router
from src.routes.watch import router as watch_router

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Vision Service",
    description="MCP service for screen capture, OCR, and visual understanding",
    version="1.0.0"
)

# CORS middleware
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from src.services.screenshot import ScreenshotService
    from src.services.ocr_engine import OCREngine
    
    # Check core services
    screenshot_ok = ScreenshotService.is_available()
    ocr_ok = OCREngine.is_available()
    
    return {
        "status": "ok" if (screenshot_ok and ocr_ok) else "degraded",
        "service": "vision",
        "version": "1.0.0",
        "capabilities": {
            "screenshot": screenshot_ok,
            "ocr": ocr_ok,
            "vlm": os.getenv('VLM_ENABLED', 'true').lower() == 'true'
        }
    }

# Service capabilities endpoint (for MCP discovery)
@app.get("/service.capabilities")
async def service_capabilities():
    """Return service capabilities for MCP discovery"""
    return {
        "service": "vision",
        "version": "1.0.0",
        "endpoints": [
            {
                "path": "/vision/capture",
                "method": "POST",
                "description": "Capture screenshot",
                "params": ["region", "format"]
            },
            {
                "path": "/vision/ocr",
                "method": "POST",
                "description": "Extract text from screen",
                "params": ["region", "language"]
            },
            {
                "path": "/vision/describe",
                "method": "POST",
                "description": "Describe screen content using VLM",
                "params": ["region", "task", "store_to_memory"]
            },
            {
                "path": "/vision/watch/start",
                "method": "POST",
                "description": "Start continuous screen monitoring",
                "params": ["interval_ms", "change_threshold", "run_ocr", "run_vlm"]
            },
            {
                "path": "/vision/watch/stop",
                "method": "POST",
                "description": "Stop screen monitoring"
            },
            {
                "path": "/vision/watch/status",
                "method": "GET",
                "description": "Get watch status"
            }
        ],
        "dependencies": {
            "user-memory": "http://localhost:3003"
        }
    }

# Include routers
app.include_router(capture_router)
app.include_router(ocr_router)
app.include_router(describe_router)
app.include_router(watch_router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "version": "mcp.v1",
            "status": "error",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc)
            }
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv('PORT', 3006))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"👁️  Starting Vision Service on {host}:{port}")
    
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=True,
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )
