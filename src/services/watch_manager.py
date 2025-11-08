"""
Watch Manager
Continuous screen monitoring with change detection
"""

import os
import time
import logging
import threading
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

from .screenshot import ScreenshotService
from .ocr_engine import OCREngine
from .vlm_engine import VLMEngine

logger = logging.getLogger(__name__)

@dataclass
class WatchConfig:
    """Watch configuration"""
    interval_ms: int = 2000
    change_threshold: float = 0.08
    run_ocr: bool = False
    run_vlm: bool = False
    task: Optional[str] = None
    region: Optional[tuple] = None

class WatchManager:
    """Manages continuous screen monitoring"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize watch manager"""
        self._thread = None
        self._stop_event = threading.Event()
        self._config = WatchConfig()
        self._last_fingerprint = None
        self._is_running = False
        self._lock = threading.RLock()
        self._callback = None
    
    def is_running(self) -> bool:
        """Check if watch is active"""
        with self._lock:
            return self._is_running
    
    def get_status(self) -> Dict[str, Any]:
        """Get current watch status"""
        with self._lock:
            return {
                "running": self._is_running,
                "interval_ms": self._config.interval_ms,
                "change_threshold": self._config.change_threshold,
                "run_ocr": self._config.run_ocr,
                "run_vlm": self._config.run_vlm,
                "task": self._config.task,
                "region": self._config.region
            }
    
    def start(self, config: WatchConfig, callback: Optional[Callable] = None):
        """
        Start watching
        
        Args:
            config: Watch configuration
            callback: Optional callback for events (tick, change, error)
        """
        with self._lock:
            if self._is_running:
                # Update config if already running
                self._config = config
                self._callback = callback
                logger.info("Updated watch configuration")
                return
            
            self._config = config
            self._callback = callback
            self._stop_event.clear()
            self._last_fingerprint = None
            
            # Start watch thread
            self._thread = threading.Thread(target=self._watch_loop, daemon=True)
            self._is_running = True
            self._thread.start()
            
            logger.info(f"Started watch (interval={config.interval_ms}ms, threshold={config.change_threshold})")
    
    def stop(self):
        """Stop watching"""
        with self._lock:
            if not self._is_running:
                return
            
            self._stop_event.set()
            if self._thread:
                self._thread.join(timeout=2.0)
            
            self._thread = None
            self._is_running = False
            self._last_fingerprint = None
            
            logger.info("Stopped watch")
    
    def _watch_loop(self):
        """Main watch loop (runs in separate thread)"""
        ocr_engine = OCREngine.get_instance() if self._config.run_ocr else None
        vlm_engine = VLMEngine.get_instance() if self._config.run_vlm else None
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:
                # Capture screenshot
                img = ScreenshotService.capture(self._config.region)
                fingerprint = ScreenshotService.generate_fingerprint(img)
                
                # Calculate change
                delta = ScreenshotService.calculate_diff(self._last_fingerprint, fingerprint)
                
                # Build event payload
                payload = {
                    "timestamp": time.time(),
                    "delta": round(delta, 5),
                    "width": img.width,
                    "height": img.height,
                    "region": self._config.region
                }
                
                # Run OCR if enabled
                if self._config.run_ocr and ocr_engine:
                    try:
                        items = ocr_engine.extract_text(img)
                        payload["ocr"] = {
                            "items": items,
                            "concat": " ".join(item["text"] for item in items)
                        }
                    except Exception as e:
                        payload["ocr_error"] = str(e)
                        logger.error(f"OCR failed: {e}")
                
                # Run VLM if enabled (only on changes to save compute)
                if self._config.run_vlm and vlm_engine and vlm_engine.is_enabled():
                    if self._last_fingerprint is None or delta >= self._config.change_threshold:
                        try:
                            description = vlm_engine.describe(img, self._config.task)
                            payload["description"] = description
                        except Exception as e:
                            payload["vlm_error"] = str(e)
                            logger.error(f"VLM failed: {e}")
                
                # Emit tick event
                if self._callback:
                    try:
                        self._callback("tick", payload)
                    except Exception as e:
                        logger.error(f"Callback error (tick): {e}")
                
                # Emit change event if threshold exceeded
                if self._last_fingerprint is None or delta >= self._config.change_threshold:
                    if self._callback:
                        try:
                            self._callback("change", payload)
                        except Exception as e:
                            logger.error(f"Callback error (change): {e}")
                    
                    logger.debug(f"Screen changed (delta={delta:.4f})")
                
                self._last_fingerprint = fingerprint
                
            except Exception as e:
                logger.error(f"Watch loop error: {e}")
                if self._callback:
                    try:
                        self._callback("error", {"message": str(e)})
                    except:
                        pass
            
            # Sleep for remainder of interval
            elapsed_ms = int((time.time() - start_time) * 1000)
            sleep_ms = max(1, self._config.interval_ms - elapsed_ms)
            self._stop_event.wait(timeout=sleep_ms / 1000.0)
