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
from ..services.vision_engine import VisionEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["describe"])

class DescribeRequest(BaseModel):
    """Describe request model"""
    region: Optional[List[int]] = None  # [x, y, width, height]
    task: Optional[str] = None  # Optional focus/task instruction
    mode: Optional[str] = None  # 'online' or 'privacy' (overrides default)
    api_key: Optional[str] = None  # Google Vision API key (from database or OAuth)
    include_ocr: bool = True  # Include OCR text
    store_to_memory: bool = True  # Store result to user-memory service

class DescribeResponse(BaseModel):
    """Describe response model"""
    version: str = "mcp.v1"
    status: str = "success"
    data: dict

@router.post("/describe", response_model=DescribeResponse)  # MCP action: describe
async def describe_screen(request: DescribeRequest):
    """
    Describe screen content using vision engine (online or privacy mode)
    
    Args:
        request: Description configuration with optional mode parameter
        
    Returns:
        Natural language description + text extraction
    """
    try:
        logger.info(f"Describing screen (region={request.region}, mode={request.mode}, task={request.task})")
        
        # Capture screenshot
        region = tuple(request.region) if request.region else None
        img = ScreenshotService.capture(region)
        
        # Process with vision engine
        vision_engine = VisionEngine()
        
        # Build options with API key if provided
        process_options = {}
        if request.task:
            process_options['prompt'] = request.task
        if request.api_key:
            process_options['api_key'] = request.api_key
        
        vision_result = await vision_engine.process(
            img=img,
            mode=request.mode,
            task='describe',
            options=process_options
        )
        
        result = {
            "width": img.width,
            "height": img.height,
            "region": request.region,
            "text": vision_result.get('text', ''),
            "description": vision_result.get('description', ''),
            "labels": vision_result.get('labels', []),
            "objects": vision_result.get('objects', []),
            "mode": vision_result.get('mode'),
            "latency_ms": vision_result.get('latency_ms'),
            "cached": vision_result.get('cached', False)
        }
        
        # Store to user-memory service if requested
        if request.store_to_memory and result.get("description"):
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
