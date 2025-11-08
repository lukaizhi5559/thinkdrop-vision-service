"""
Watch (continuous monitoring) endpoints
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ..services.watch_manager import WatchManager, WatchConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vision/watch", tags=["watch"])

class WatchStartRequest(BaseModel):
    """Watch start request model"""
    interval_ms: int = 2000
    change_threshold: float = 0.08
    run_ocr: bool = False
    run_vlm: bool = False
    task: Optional[str] = None
    region: Optional[List[int]] = None

class WatchResponse(BaseModel):
    """Watch response model"""
    version: str = "mcp.v1"
    status: str = "success"
    data: dict

@router.post("/start", response_model=WatchResponse)
async def start_watch(request: WatchStartRequest):
    """
    Start continuous screen monitoring
    
    Args:
        request: Watch configuration
        
    Returns:
        Watch status
    """
    try:
        logger.info(f"Starting watch (interval={request.interval_ms}ms)")
        
        # Create config
        config = WatchConfig(
            interval_ms=request.interval_ms,
            change_threshold=request.change_threshold,
            run_ocr=request.run_ocr,
            run_vlm=request.run_vlm,
            task=request.task,
            region=tuple(request.region) if request.region else None
        )
        
        # Start watch
        watch_manager = WatchManager.get_instance()
        watch_manager.start(config)
        
        return WatchResponse(
            version="mcp.v1",
            status="success",
            data=watch_manager.get_status()
        )
        
    except Exception as e:
        logger.error(f"Failed to start watch: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "version": "mcp.v1",
                "status": "error",
                "error": {
                    "code": "WATCH_START_FAILED",
                    "message": str(e)
                }
            }
        )

@router.post("/stop", response_model=WatchResponse)
async def stop_watch():
    """
    Stop screen monitoring
    
    Returns:
        Watch status
    """
    try:
        logger.info("Stopping watch")
        
        watch_manager = WatchManager.get_instance()
        watch_manager.stop()
        
        return WatchResponse(
            version="mcp.v1",
            status="success",
            data={"stopped": True}
        )
        
    except Exception as e:
        logger.error(f"Failed to stop watch: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "version": "mcp.v1",
                "status": "error",
                "error": {
                    "code": "WATCH_STOP_FAILED",
                    "message": str(e)
                }
            }
        )

@router.get("/status", response_model=WatchResponse)
async def get_watch_status():
    """
    Get current watch status
    
    Returns:
        Watch status and configuration
    """
    try:
        watch_manager = WatchManager.get_instance()
        status = watch_manager.get_status()
        
        return WatchResponse(
            version="mcp.v1",
            status="success",
            data=status
        )
        
    except Exception as e:
        logger.error(f"Failed to get watch status: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "version": "mcp.v1",
                "status": "error",
                "error": {
                    "code": "WATCH_STATUS_FAILED",
                    "message": str(e)
                }
            }
        )
