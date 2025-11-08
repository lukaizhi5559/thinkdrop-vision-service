"""
OCR Engine
Text extraction using PaddleOCR
"""

import os
import logging
import numpy as np
import cv2
from PIL import Image
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class OCREngine:
    """Handles OCR operations using PaddleOCR"""
    
    _instance = None
    _ocr = None
    
    @classmethod
    def get_instance(cls):
        """Singleton pattern for OCR engine"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize OCR engine (lazy-loaded)"""
        self._ocr = None
    
    def _ensure_loaded(self):
        """Load OCR model if not already loaded"""
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                
                lang = os.getenv('OCR_LANGUAGE', 'en')
                use_angle_cls = os.getenv('OCR_USE_ANGLE_CLS', 'true').lower() == 'true'
                
                logger.info(f"Loading PaddleOCR (lang={lang}, angle_cls={use_angle_cls})...")
                self._ocr = PaddleOCR(
                    use_angle_cls=use_angle_cls,
                    lang=lang,
                    show_log=False
                )
                logger.info("✅ PaddleOCR loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load PaddleOCR: {e}")
                raise
    
    @staticmethod
    def is_available() -> bool:
        """Check if OCR is available"""
        try:
            from paddleocr import PaddleOCR
            return True
        except ImportError:
            logger.warning("PaddleOCR not installed")
            return False
    
    def extract_text(self, img: Image.Image, language: str = None) -> List[Dict[str, Any]]:
        """
        Extract text from image
        
        Args:
            img: PIL Image
            language: Optional language override
            
        Returns:
            List of detected text items with bounding boxes and confidence scores
        """
        self._ensure_loaded()
        
        try:
            # Convert PIL Image to OpenCV format (BGR)
            img_array = np.array(img)
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # Run OCR
            result = self._ocr.ocr(img_bgr, cls=True)
            
            # Parse results
            items = []
            if result and result[0]:
                for line in result[0]:
                    # line[0] = [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    # line[1] = (text, confidence)
                    bbox_points = line[0]
                    text, confidence = line[1]
                    
                    # Convert to simple bbox [x1, y1, x2, y2]
                    x_coords = [p[0] for p in bbox_points]
                    y_coords = [p[1] for p in bbox_points]
                    bbox = [
                        min(x_coords),
                        min(y_coords),
                        max(x_coords),
                        max(y_coords)
                    ]
                    
                    items.append({
                        "text": text,
                        "bbox": bbox,
                        "confidence": float(confidence)
                    })
            
            logger.info(f"Extracted {len(items)} text items")
            return items
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise
    
    def extract_text_concat(self, img: Image.Image, language: str = None) -> str:
        """
        Extract text and concatenate into single string
        
        Args:
            img: PIL Image
            language: Optional language override
            
        Returns:
            Concatenated text string
        """
        items = self.extract_text(img, language)
        return " ".join(item["text"] for item in items)
