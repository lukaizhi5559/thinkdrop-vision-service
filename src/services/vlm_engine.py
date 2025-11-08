"""
VLM Engine
Vision-Language Model for scene understanding (lazy-loaded)
"""

import os
import logging
from PIL import Image
from typing import Optional

logger = logging.getLogger(__name__)

class VLMEngine:
    """Handles VLM operations (lazy-loaded)"""
    
    _instance = None
    _model = None
    _processor = None
    _enabled = None
    
    @classmethod
    def get_instance(cls):
        """Singleton pattern for VLM engine"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize VLM engine (lazy-loaded)"""
        self._model = None
        self._processor = None
        self._enabled = os.getenv('VLM_ENABLED', 'true').lower() == 'true'
    
    def is_enabled(self) -> bool:
        """Check if VLM is enabled"""
        return self._enabled
    
    def is_loaded(self) -> bool:
        """Check if VLM model is loaded"""
        return self._model is not None
    
    def _ensure_loaded(self):
        """Load VLM model if not already loaded"""
        if not self._enabled:
            raise RuntimeError("VLM is disabled in configuration")
        
        if self._model is None:
            try:
                import torch
                from transformers import AutoProcessor, AutoModelForVision2Seq
                
                model_id = os.getenv('VLM_MODEL', 'openbmb/MiniCPM-V-2_6')
                device = os.getenv('VLM_DEVICE', 'auto')
                
                logger.info(f"Loading VLM model: {model_id}...")
                logger.info("⏳ This may take 30-60 seconds on first load...")
                
                # Load processor
                self._processor = AutoProcessor.from_pretrained(
                    model_id,
                    trust_remote_code=True
                )
                
                # Load model
                dtype = torch.float16 if torch.cuda.is_available() else torch.float32
                self._model = AutoModelForVision2Seq.from_pretrained(
                    model_id,
                    torch_dtype=dtype,
                    device_map=device,
                    trust_remote_code=True
                )
                
                logger.info(f"✅ VLM loaded successfully (device: {device}, dtype: {dtype})")
                
            except ImportError as e:
                logger.error(f"VLM dependencies not installed: {e}")
                logger.error("Install with: pip install torch transformers accelerate")
                raise
            except Exception as e:
                logger.error(f"Failed to load VLM: {e}")
                raise
    
    def describe(self, img: Image.Image, task: Optional[str] = None) -> str:
        """
        Generate description of image using VLM
        
        Args:
            img: PIL Image
            task: Optional task/focus instruction
            
        Returns:
            Natural language description
        """
        self._ensure_loaded()
        
        try:
            import torch
            
            # Build prompt
            prompt = "Describe this desktop screenshot in detail. Identify applications, windows, dialogs, errors, and actionable buttons or elements."
            if task:
                prompt += f"\n\nFocus: {task}"
            
            # Prepare inputs
            inputs = self._processor(
                images=img,
                text=prompt,
                return_tensors="pt"
            ).to(self._model.device)
            
            # Generate
            max_tokens = int(os.getenv('VLM_MAX_TOKENS', 256))
            with torch.no_grad():
                output_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=max_tokens
                )
            
            # Decode
            description = self._processor.batch_decode(
                output_ids,
                skip_special_tokens=True
            )[0]
            
            logger.info(f"Generated description: {description[:100]}...")
            return description
            
        except Exception as e:
            logger.error(f"VLM description failed: {e}")
            raise
    
    def unload(self):
        """Unload model to free memory"""
        if self._model is not None:
            logger.info("Unloading VLM model...")
            del self._model
            del self._processor
            self._model = None
            self._processor = None
            
            # Clear CUDA cache if available
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
            
            logger.info("✅ VLM model unloaded")
