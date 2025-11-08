"""
Screenshot capture endpoint
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ..services.screenshot import ScreenshotService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["capture"])

class CaptureRequest(BaseModel):
    """Capture request model"""
    region: Optional[List[int]] = None  # [x, y, width, height]
    format: str = "png"  # png or base64

class CaptureResponse(BaseModel):
    """Capture response model"""
    version: str = "mcp.v1"
    status: str = "success"
    data: dict

@router.post("/capture", response_model=CaptureResponse)  # MCP action: capture
async def capture_screenshot(request: CaptureRequest):
    """
    Capture screenshot
    
    Args:
        request: Capture configuration
        
    Returns:
        Screenshot data (base64 PNG + dimensions)
    """
    try:
        logger.info(f"Capturing screenshot (region={request.region})")
        
        # Capture
        region = tuple(request.region) if request.region else None
        img = ScreenshotService.capture(region)
        
        # Encode
        png_base64 = ScreenshotService.encode_png(img)
        
        return CaptureResponse(
            version="mcp.v1",
            status="success",
            data={
                "png_base64": png_base64,
                "width": img.width,
                "height": img.height,
                "region": request.region
            }
        )
        
    except Exception as e:
        logger.error(f"Capture failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "version": "mcp.v1",
                "status": "error",
                "error": {
                    "code": "CAPTURE_FAILED",
                    "message": str(e)
                }
            }
        )
