"""
Screenshot Service
Fast cross-platform screen capture using mss
"""

import os
import base64
import logging
from io import BytesIO
from typing import Optional, Tuple
from PIL import Image
import mss

logger = logging.getLogger(__name__)

class ScreenshotService:
    """Handles screen capture operations"""
    
    @staticmethod
    def is_available() -> bool:
        """Check if screenshot capability is available"""
        try:
            with mss.mss() as sct:
                return len(sct.monitors) > 0
        except Exception as e:
            logger.error(f"Screenshot service unavailable: {e}")
            return False
    
    @staticmethod
    def capture(region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        """
        Capture screenshot
        
        Args:
            region: Optional (x, y, width, height) tuple for specific region
            
        Returns:
            PIL Image object
        """
        try:
            with mss.mss() as sct:
                # Get monitor (full screen if no region specified)
                if region:
                    x, y, w, h = region
                    monitor = {"left": x, "top": y, "width": w, "height": h}
                else:
                    monitor = sct.monitors[0]  # Full virtual screen
                
                # Capture
                screenshot = sct.grab(monitor)
                
                # Convert to PIL Image
                img = Image.frombytes(
                    'RGB',
                    (screenshot.width, screenshot.height),
                    screenshot.rgb
                )
                
                logger.info(f"Captured screenshot: {img.width}x{img.height}")
                return img
                
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            raise
    
    @staticmethod
    def encode_png(img: Image.Image) -> str:
        """
        Encode image as base64 PNG
        
        Args:
            img: PIL Image
            
        Returns:
            Base64 encoded PNG string
        """
        buf = BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    
    @staticmethod
    def save_temp(img: Image.Image, prefix: str = "thinkdrop_screen") -> str:
        """
        Save image to temp file
        
        Args:
            img: PIL Image
            prefix: Filename prefix
            
        Returns:
            Path to temp file
        """
        import uuid
        temp_dir = os.getenv('TEMP_DIR', '/tmp/thinkdrop-vision')
        os.makedirs(temp_dir, exist_ok=True)
        
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(temp_dir, filename)
        
        img.save(filepath, format='PNG')
        logger.debug(f"Saved temp screenshot: {filepath}")
        
        return filepath
    
    @staticmethod
    def cleanup_temp(filepath: str):
        """Delete temp file"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.debug(f"Cleaned up temp file: {filepath}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {filepath}: {e}")
    
    @staticmethod
    def generate_fingerprint(img: Image.Image) -> bytes:
        """
        Generate perceptual fingerprint for change detection
        
        Args:
            img: PIL Image
            
        Returns:
            Fingerprint bytes
        """
        from PIL import ImageOps
        
        # Downscale to 64x64 grayscale for fast comparison
        small = ImageOps.grayscale(img.resize((64, 64)))
        return small.tobytes()
    
    @staticmethod
    def calculate_diff(fp_a: Optional[bytes], fp_b: Optional[bytes]) -> float:
        """
        Calculate difference score between two fingerprints
        
        Args:
            fp_a: First fingerprint
            fp_b: Second fingerprint
            
        Returns:
            Difference score (0.0 = identical, 1.0 = completely different)
        """
        if fp_a is None or fp_b is None:
            return 1.0
        
        if len(fp_a) != len(fp_b):
            return 1.0
        
        # Mean absolute difference normalized to 0-1
        total = sum(abs(a - b) for a, b in zip(fp_a, fp_b))
        return total / (len(fp_a) * 255.0)
