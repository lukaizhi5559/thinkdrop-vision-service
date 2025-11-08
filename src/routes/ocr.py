"""
OCR text extraction endpoint
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ..services.screenshot import ScreenshotService
from ..services.ocr_engine import OCREngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vision", tags=["ocr"])

class OCRRequest(BaseModel):
    """OCR request model"""
    region: Optional[List[int]] = None  # [x, y, width, height]
    language: Optional[str] = None

class OCRResponse(BaseModel):
    """OCR response model"""
    version: str = "mcp.v1"
    status: str = "success"
    data: dict

@router.post("/ocr", response_model=OCRResponse)
async def extract_text(request: OCRRequest):
    """
    Extract text from screen using OCR
    
    Args:
        request: OCR configuration
        
    Returns:
        Extracted text items with bounding boxes and confidence scores
    """
    try:
        logger.info(f"Running OCR (region={request.region}, lang={request.language})")
        
        # Capture
        region = tuple(request.region) if request.region else None
        img = ScreenshotService.capture(region)
        
        # OCR
        ocr_engine = OCREngine.get_instance()
        items = ocr_engine.extract_text(img, request.language)
        
        # Concatenate text
        concat_text = " ".join(item["text"] for item in items)
        
        return OCRResponse(
            version="mcp.v1",
            status="success",
            data={
                "items": items,
                "concat": concat_text,
                "count": len(items),
                "region": request.region
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
