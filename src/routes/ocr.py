"""
OCR text extraction endpoint
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ..services.screenshot import ScreenshotService
from ..services.vision_engine import VisionEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ocr"])

class OCRRequest(BaseModel):
    """OCR request model"""
    region: Optional[List[int]] = None  # [x, y, width, height]
    language: Optional[str] = None
    mode: Optional[str] = None  # 'online' or 'privacy' (overrides default)
    api_key: Optional[str] = None  # Google Vision API key (from database or OAuth)

class OCRResponse(BaseModel):
    """OCR response model"""
    version: str = "mcp.v1"
    status: str = "success"
    data: dict

@router.post("/ocr", response_model=OCRResponse)  # MCP action: ocr
async def extract_text(request: OCRRequest):
    """
    Extract text from screen using OCR
    
    Args:
        request: OCR configuration
        
    Returns:
        Extracted text items with bounding boxes and confidence scores
    """
    try:
        logger.info(f"Running OCR (region={request.region}, mode={request.mode})")
        
        # Capture screenshot
        region = tuple(request.region) if request.region else None
        img = ScreenshotService.capture(region)
        
        # Process with vision engine (extract_text task)
        vision_engine = VisionEngine()
        
        # Build options with API key if provided
        process_options = {}
        if request.api_key:
            process_options['api_key'] = request.api_key
        
        vision_result = await vision_engine.process(
            img=img,
            mode=request.mode,
            task='extract_text',
            options=process_options
        )
        
        # Extract text from result
        text = vision_result.get('text', '')
        
        return OCRResponse(
            version="mcp.v1",
            status="success",
            data={
                "text": text,
                "concat": text,
                "region": request.region,
                "mode": vision_result.get('mode'),
                "latency_ms": vision_result.get('latency_ms'),
                "cached": vision_result.get('cached', False)
            }
        )
        
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "version": "mcp.v1",
                "status": "error",
                "error": {
                    "code": "OCR_FAILED",
                    "message": str(e)
                }
            }
        )
