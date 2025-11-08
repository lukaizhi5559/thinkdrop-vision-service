# Vision Service - MCP

Vision capabilities for ThinkDrop AI: screen capture, OCR, and VLM scene understanding.

## Features

- **Screenshot Capture** - Fast cross-platform screen capture
- **OCR** - Text extraction using PaddleOCR (local, multilingual)
- **VLM** - Scene understanding using MiniCPM-V 2.6 (lazy-loaded, optional)
- **Watch Mode** - Continuous monitoring with change detection
- **Memory Integration** - Auto-store to user-memory service as embeddings

## Quick Start

```bash
# 1. Copy environment config
cp .env.example .env

# 2. Edit .env (set API keys, configure VLM, etc.)
nano .env

# 3. Start service
./start.sh
```

Service will be available at `http://localhost:3006`

## Installation Options

### Minimal (OCR Only - No GPU Required)
```bash
pip install -r requirements.txt
```
- Screenshot + OCR only
- ~200-500ms per capture
- No VLM dependencies

### Full (OCR + VLM - GPU Recommended)
```bash
# Uncomment VLM dependencies in requirements.txt
pip install torch transformers accelerate

# Or with CUDA support
pip install torch --index-url https://download.pytorch.org/whl/cu118
pip install transformers accelerate
```
- Screenshot + OCR + VLM
- 600-1500ms with GPU, 2-6s with CPU
- ~2.4GB model download on first use

## API Endpoints

### Health Check
```bash
GET /health
```

### Capture Screenshot
```bash
POST /vision/capture
{
  "region": [x, y, width, height],  # Optional
  "format": "png"
}
```

### Extract Text (OCR)
```bash
POST /vision/ocr
{
  "region": [x, y, width, height],  # Optional
  "language": "en"                   # Optional
}
```

### Describe Screen (VLM)
```bash
POST /vision/describe
{
  "region": [x, y, width, height],  # Optional
  "task": "Find the Save button",   # Optional focus
  "include_ocr": true,               # Include OCR text
  "store_to_memory": true            # Auto-store to user-memory
}
```

### Start Watch Mode
```bash
POST /vision/watch/start
{
  "interval_ms": 2000,
  "change_threshold": 0.08,
  "run_ocr": true,
  "run_vlm": false,
  "task": "Monitor for errors"
}
```

### Stop Watch Mode
```bash
POST /vision/watch/stop
```

### Watch Status
```bash
GET /vision/watch/status
```

## Configuration

Key environment variables in `.env`:

```bash
# Service
PORT=3006
API_KEY=your-vision-api-key-here

# OCR
OCR_ENGINE=paddleocr
OCR_LANGUAGE=en

# VLM (lazy-loaded)
VLM_ENABLED=true
VLM_MODEL=openbmb/MiniCPM-V-2_6
VLM_DEVICE=auto  # auto, cpu, cuda

# Watch
WATCH_DEFAULT_INTERVAL_MS=2000
WATCH_CHANGE_THRESHOLD=0.08

# User Memory Integration
USER_MEMORY_SERVICE_URL=http://localhost:3003
USER_MEMORY_API_KEY=your-user-memory-api-key
```

## Performance

### OCR Only (Minimal Setup)
- **Capture**: 10-20ms
- **OCR**: 200-500ms
- **Total**: ~300-600ms per request
- **Memory**: ~500MB

### OCR + VLM (Full Setup)
- **Capture**: 10-20ms
- **OCR**: 200-500ms
- **VLM (GPU)**: 300-800ms
- **VLM (CPU)**: 2-5s
- **Total (GPU)**: ~600-1500ms
- **Total (CPU)**: ~2.5-6s
- **Memory**: ~3-4GB (model loaded)

## Watch Mode Strategy

Watch mode uses smart change detection to minimize VLM calls:

1. **Every interval**: Capture + fingerprint comparison
2. **On change**: Run OCR (if enabled)
3. **On significant change**: Run VLM (if enabled)
4. **Auto-store**: Send to user-memory service as embedding

This keeps VLM usage efficient while maintaining continuous awareness.

## Integration with ThinkDrop AI

The vision service integrates with the MCP state graph:

```javascript
// In AgentOrchestrator state graph
const visionResult = await mcpClient.callService('vision', 'describe', {
  include_ocr: true,
  store_to_memory: true,
  task: userMessage
});

// Result automatically stored as embedding in user-memory
// No screenshot files to manage!
```

## Testing

### Test Capture
```bash
curl -X POST http://localhost:3006/vision/capture \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Test OCR
```bash
curl -X POST http://localhost:3006/vision/ocr \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Test VLM (if enabled)
```bash
curl -X POST http://localhost:3006/vision/describe \
  -H "Content-Type: application/json" \
  -d '{"include_ocr": true, "store_to_memory": false}'
```

### Test Watch
```bash
# Start
curl -X POST http://localhost:3006/vision/watch/start \
  -H "Content-Type: application/json" \
  -d '{"interval_ms": 2000, "run_ocr": true}'

# Status
curl http://localhost:3006/vision/watch/status

# Stop
curl -X POST http://localhost:3006/vision/watch/stop
```

## Troubleshooting

### OCR Not Working
- Check PaddleOCR installation: `pip list | grep paddleocr`
- Models download on first use (~100MB)
- Check logs for download progress

### VLM Not Loading
- Ensure dependencies installed: `pip list | grep transformers`
- Check available memory (need 4-8GB)
- Set `VLM_ENABLED=false` to disable
- Model downloads on first use (~2.4GB)

### Performance Issues
- **CPU too slow**: Disable VLM, use OCR only
- **Memory issues**: Reduce watch interval, disable VLM
- **GPU not detected**: Check CUDA installation

## Architecture

```
vision-service/
├── server.py              # FastAPI app
├── src/
│   ├── services/
│   │   ├── screenshot.py  # mss wrapper
│   │   ├── ocr_engine.py  # PaddleOCR wrapper
│   │   ├── vlm_engine.py  # VLM wrapper (lazy)
│   │   └── watch_manager.py  # Watch loop
│   ├── routes/
│   │   ├── capture.py     # /vision/capture
│   │   ├── ocr.py         # /vision/ocr
│   │   ├── describe.py    # /vision/describe
│   │   └── watch.py       # /vision/watch/*
│   └── middleware/
│       └── validation.py  # API key validation
├── requirements.txt
├── start.sh
└── README.md
```

## License

Part of ThinkDrop AI project.
