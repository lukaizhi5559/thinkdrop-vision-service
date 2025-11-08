"""
VLM scene description endpoint
"""

import os
import logging
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ..services.screenshot import ScreenshotService
from ..services.ocr_engine import OCREngine
from ..services.vlm_engine import VLMEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vision", tags=["describe"])

class DescribeRequest(BaseModel):
    """Describe request model"""
    region: Optional[List[int]] = None  # [x, y, width, height]
    task: Optional[str] = None  # Optional focus/task instruction
    include_ocr: bool = True  # Include OCR text
    store_to_memory: bool = True  # Store result to user-memory service

class DescribeResponse(BaseModel):
    """Describe response model"""
    version: str = "mcp.v1"
    status: str = "success"
    data: dict

@router.post("/describe", response_model=DescribeResponse)
async def describe_screen(request: DescribeRequest):
    """
    Describe screen content using VLM
    
    Args:
        request: Description configuration
        
    Returns:
        Natural language description + optional OCR text
    """
    try:
        logger.info(f"Describing screen (region={request.region}, task={request.task})")
        
        # Capture
        region = tuple(request.region) if request.region else None
        img = ScreenshotService.capture(region)
        
        # Save temp file for processing
        temp_file = ScreenshotService.save_temp(img)
        
        try:
            result = {
                "width": img.width,
                "height": img.height,
                "region": request.region
            }
            
            # OCR
            if request.include_ocr:
                try:
                    ocr_engine = OCREngine.get_instance()
                    items = ocr_engine.extract_text(img)
                    ocr_text = " ".join(item["text"] for item in items)
                    result["ocr"] = {
                        "items": items,
                        "concat": ocr_text
                    }
                except Exception as e:
                    logger.warning(f"OCR failed: {e}")
                    result["ocr_error"] = str(e)
            
            # VLM description
            try:
                vlm_engine = VLMEngine.get_instance()
                if vlm_engine.is_enabled():
                    description = vlm_engine.describe(img, request.task)
                    result["description"] = description
                else:
                    result["description"] = None
                    result["vlm_disabled"] = True
                    logger.info("VLM disabled, using OCR only")
            except Exception as e:
                logger.error(f"VLM failed: {e}")
                result["vlm_error"] = str(e)
                # Fallback to OCR-only description
                if "ocr" in result:
                    result["description"] = f"Screen content (OCR): {result['ocr']['concat'][:500]}"
            
            # Store to user-memory service
            if request.store_to_memory and "description" in result:
                try:
                    await store_to_user_memory(result)
                    result["stored_to_memory"] = True
                except Exception as e:
                    logger.warning(f"Failed to store to memory: {e}")
                    result["memory_storage_error"] = str(e)
            
            return DescribeResponse(
                version="mcp.v1",
                status="success",
                data=result
            )
            
        finally:
            # Cleanup temp file
            ScreenshotService.cleanup_temp(temp_file)
        
    except Exception as e:
        logger.error(f"Describe failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "version": "mcp.v1",
                "status": "error",
                "error": {
                    "code": "DESCRIBE_FAILED",
                    "message": str(e)
                }
            }
        )

async def store_to_user_memory(vision_data: dict):
    """
    Store vision result to user-memory service as embedding
    
    Args:
        vision_data: Vision processing result
    """
    user_memory_url = os.getenv('USER_MEMORY_SERVICE_URL', 'http://localhost:3003')
    api_key = os.getenv('USER_MEMORY_API_KEY', '')
    
    # Build content from description + OCR
    content = vision_data.get('description', '')
    if 'ocr' in vision_data and vision_data['ocr'].get('concat'):
        content += f"\n\nExtracted text: {vision_data['ocr']['concat']}"
    
    # Prepare payload
    payload = {
        "content": content,
        "metadata": {
            "type": "screen_capture",
            "source": "vision-service",
            "width": vision_data.get('width'),
            "height": vision_data.get('height'),
            "region": vision_data.get('region'),
            "has_ocr": 'ocr' in vision_data,
            "has_description": 'description' in vision_data
        }
    }
    
    # POST to user-memory service
    async with httpx.AsyncClient(timeout=10.0) as client:
        headers = {}
        if api_key:
            headers['x-api-key'] = api_key
        
        response = await client.post(
            f"{user_memory_url}/memory/store",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        
        logger.info("Stored vision result to user-memory service")
        return response.json()
