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
                try:
                    self._ocr = PaddleOCR(
                        use_textline_orientation=use_angle_cls,  # Updated parameter name
                        lang=lang
                    )
                    logger.info(f"PaddleOCR initialized (lang={lang})")
                except Exception as e:
                    logger.error(f"Failed to initialize PaddleOCR: {e}")
                    raise
                
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
            result = self._ocr.ocr(img_bgr)
            
            # Parse results
            items = []
            if result and result[0]:
                for line in result[0]:
                    try:
                        # Handle different result formats
                        if isinstance(line, (list, tuple)) and len(line) >= 2:
                            # line[0] = [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                            # line[1] = (text, confidence) or just text
                            bbox_points = line[0]
                            
                            # Handle text/confidence tuple or dict
                            if isinstance(line[1], (list, tuple)) and len(line[1]) >= 2:
                                text, confidence = line[1][0], line[1][1]
                            elif isinstance(line[1], dict):
                                text = line[1].get('text', '')
                                confidence = line[1].get('confidence', 0.0)
                            else:
                                text = str(line[1])
                                confidence = 1.0
                            
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
                    except Exception as e:
                        logger.warning(f"Failed to parse OCR line: {e}, line={line}")
                        continue
            
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
