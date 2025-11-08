"""
Unified Vision Engine - Dual Mode Support
Supports both online (Google Vision API) and privacy (local Qwen2-VL) modes
"""

import os
import logging
import time
import hashlib
from typing import Dict, Any, Optional, List
from PIL import Image, ImageOps
import io

logger = logging.getLogger(__name__)


class VisionEngine:
    """
    Unified vision processing engine with dual-mode support
    
    Modes:
        - online: Google Vision API (fast, 200-500ms, no privacy)
        - privacy: Local Qwen2-VL (slower, 1-2s, private)
    """
    
    def __init__(self):
        self.default_mode = os.getenv('VISION_MODE', 'online')
        self.google_client = None
        self.qwen_model = None
        self._cache = {}
        
        logger.info(f"VisionEngine initialized (default mode: {self.default_mode})")
    
    async def process(
        self,
        img: Image.Image,
        mode: Optional[str] = None,
        task: str = "describe",
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process image with specified mode
        
        Args:
            img: PIL Image
            mode: 'online' or 'privacy' (defaults to VISION_MODE env var)
            task: 'describe', 'extract_text', or 'analyze'
            options: Additional processing options
            
        Returns:
            {
                'text': str,
                'description': str,
                'labels': List[str],
                'mode': str,
                'latency_ms': float,
                'cached': bool
            }
        """
        start_time = time.time()
        options = options or {}
        mode = mode or self.default_mode
        
        # Generate fingerprint for caching
        fingerprint = self._generate_fingerprint(img)
        cache_key = f"{mode}:{task}:{fingerprint}"
        
        # Check cache
        if cache_key in self._cache:
            cached_result = self._cache[cache_key].copy()
            cached_result['cached'] = True
            cached_result['latency_ms'] = 0
            logger.info(f"Cache hit for {mode}:{task}")
            return cached_result
        
        # Route to appropriate processor
        if mode == 'online':
            result = await self._process_online(img, task, options)
        elif mode == 'privacy':
            result = await self._process_privacy(img, task, options)
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'online' or 'privacy'")
        
        # Add metadata
        result['mode'] = mode
        result['latency_ms'] = (time.time() - start_time) * 1000
        result['cached'] = False
        
        # Cache result
        self._cache[cache_key] = result
        
        logger.info(f"Processed with {mode} mode in {result['latency_ms']:.0f}ms")
        return result
    
    async def _process_online(
        self,
        img: Image.Image,
        task: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process using Google Vision API"""
        try:
            # Get API key from options (passed from request)
            api_key = options.get('api_key')
            
            # Lazy load Google Vision client with API key
            if not self.google_client:
                self._load_google_client(api_key)
            
            # Convert image to bytes
            img_bytes = self._image_to_bytes(img)
            
            # Call Google Vision API
            result = await self._call_google_vision(img_bytes, task, options)
            
            return result
            
        except Exception as e:
            logger.error(f"Google Vision API error: {e}")
            # Only fallback to privacy mode if Qwen is enabled
            if os.getenv('QWEN_ENABLED', 'false').lower() == 'true':
                logger.warning("Falling back to privacy mode")
                return await self._process_privacy(img, task, options)
            else:
                # No fallback available - return error
                raise ValueError(
                    "Google Vision API failed and privacy mode (Qwen) is disabled. "
                    "Please connect Google Vision API via OAuth or enable QWEN_ENABLED=true in .env"
                )
    
    async def _process_privacy(
        self,
        img: Image.Image,
        task: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process using local Qwen2-VL model"""
        try:
            # Lazy load Qwen model
            if not self.qwen_model:
                self._load_qwen_model()
            
            # Process with Qwen2-VL
            result = await self._call_qwen_vision(img, task, options)
            
            return result
            
        except Exception as e:
            logger.error(f"Local vision processing error: {e}")
            raise
    
    def _load_google_client(self, api_key: Optional[str] = None):
        """
        Lazy load Google Vision API client
        
        Args:
            api_key: Optional API key (from request or database)
                    Falls back to GOOGLE_VISION_API_KEY env var
        """
        try:
            from google.cloud import vision
            
            # Priority: request api_key > env var
            key = api_key or os.getenv('GOOGLE_VISION_API_KEY')
            
            if not key:
                raise ValueError(
                    "GOOGLE_VISION_API_KEY not provided. "
                    "Pass api_key in request or set GOOGLE_VISION_API_KEY in .env"
                )
            
            # Initialize client with API key
            self.google_client = vision.ImageAnnotatorClient(
                client_options={"api_key": key}
            )
            
            logger.info("Google Vision API client loaded")
            
        except Exception as e:
            logger.error(f"Failed to load Google Vision client: {e}")
            raise
    
    def _load_qwen_model(self):
        """Lazy load Qwen2-VL model"""
        try:
            # Check if model is enabled
            if os.getenv('QWEN_ENABLED', 'false').lower() != 'true':
                raise ValueError("Qwen model not enabled. Set QWEN_ENABLED=true in .env")
            
            # Import Qwen dependencies
            import torch
            from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
            
            model_path = os.getenv('QWEN_MODEL_PATH', 'Qwen/Qwen2-VL-2B-Instruct')
            device = os.getenv('QWEN_DEVICE', 'auto')
            quantization = os.getenv('QWEN_QUANTIZATION', '4bit')
            
            logger.info(f"Loading Qwen2-VL model: {model_path} ({quantization}, device: {device})")
            
            # Load model with quantization (only if CUDA available)
            quantization_config = None
            if quantization == '4bit' and torch.cuda.is_available():
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16
                )
                logger.info("Using 4-bit quantization (CUDA)")
            elif quantization == '8bit' and torch.cuda.is_available():
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True
                )
                logger.info("Using 8-bit quantization (CUDA)")
            else:
                logger.info("No quantization (CPU mode)")
            
            # Determine dtype
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            
            self.qwen_model = {
                'model': Qwen2VLForConditionalGeneration.from_pretrained(
                    model_path,
                    quantization_config=quantization_config,
                    torch_dtype=dtype,
                    device_map=device,
                    trust_remote_code=True
                ),
                'processor': AutoProcessor.from_pretrained(
                    model_path,
                    trust_remote_code=True
                )
            }
            
            logger.info("Qwen2-VL model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Qwen model: {e}")
            raise
    
    async def _call_google_vision(
        self,
        img_bytes: bytes,
        task: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call Google Vision API"""
        from google.cloud import vision
        
        image = vision.Image(content=img_bytes)
        
        result = {
            'text': '',
            'description': '',
            'labels': [],
            'objects': []
        }
        
        # Text detection
        if task in ['describe', 'extract_text', 'analyze']:
            response = self.google_client.text_detection(image=image)
            if response.text_annotations:
                result['text'] = response.text_annotations[0].description
        
        # Label detection
        if task in ['describe', 'analyze']:
            response = self.google_client.label_detection(image=image)
            result['labels'] = [label.description for label in response.label_annotations]
        
        # Object detection
        if task in ['describe', 'analyze']:
            response = self.google_client.object_localization(image=image)
            result['objects'] = [obj.name for obj in response.localized_object_annotations]
        
        # Generate description from labels and objects
        if task == 'describe':
            result['description'] = self._generate_description_from_labels(
                result['labels'],
                result['objects'],
                result['text']
            )
        
        return result
    
    async def _call_qwen_vision(
        self,
        img: Image.Image,
        task: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call local Qwen2-VL model"""
        import torch
        
        model = self.qwen_model['model']
        processor = self.qwen_model['processor']
        
        # Prepare prompt based on task
        if task == 'extract_text':
            prompt = "Extract all text visible in this image. List each text element."
        elif task == 'describe':
            prompt = options.get('prompt', "Describe what you see in this image in detail.")
        else:
            prompt = "Analyze this image and provide detailed information."
        
        # Process image with Qwen2-VL
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": img},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        # Generate response using processor
        text = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = processor(
            text=[text],
            images=[img],
            return_tensors="pt"
        ).to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=False
            )
        
        response = processor.batch_decode(outputs, skip_special_tokens=True)[0]
        
        # Parse response
        result = {
            'text': response if task == 'extract_text' else '',
            'description': response if task == 'describe' else '',
            'labels': [],
            'objects': [],
            'visual_tokens': outputs[0].tolist()
        }
        
        return result
    
    def _generate_description_from_labels(
        self,
        labels: List[str],
        objects: List[str],
        text: str
    ) -> str:
        """Generate natural language description from labels and objects"""
        parts = []
        
        if objects:
            parts.append(f"The image contains: {', '.join(objects[:5])}")
        
        if labels:
            parts.append(f"Key elements: {', '.join(labels[:5])}")
        
        if text:
            text_preview = text[:100] + "..." if len(text) > 100 else text
            parts.append(f"Visible text: {text_preview}")
        
        return ". ".join(parts) if parts else "Image processed successfully"
    
    def _image_to_bytes(self, img: Image.Image) -> bytes:
        """Convert PIL Image to bytes"""
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_fingerprint(self, img: Image.Image) -> str:
        """Generate fingerprint for caching"""
        # Downscale to 64x64 grayscale for fast hashing
        small = ImageOps.grayscale(img.resize((64, 64)))
        img_bytes = small.tobytes()
        return hashlib.md5(img_bytes).hexdigest()
    
    @staticmethod
    def is_available() -> bool:
        """Check if vision engine is available"""
        return True
