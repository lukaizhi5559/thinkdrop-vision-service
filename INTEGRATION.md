# Vision Service Integration Guide

## Overview

The vision service provides "eyes" for ThinkDrop AI through the MCP architecture. It integrates seamlessly with the existing state graph pipeline.

## Architecture

```
User Query → AgentOrchestrator → State Graph → Vision Node
                                                    ↓
                                            Vision Service (Port 3006)
                                                    ↓
                                            User Memory Service (Port 3003)
                                                    ↓
                                            Embedding Storage (No files!)
```

## Integration Points

### 1. MCPClient Configuration

Add vision service to MCP registry (already handled by MCPConfigManager):

```javascript
// In MCPConfigManager initialization
const visionService = {
  name: 'vision',
  url: 'http://localhost:3006',
  apiKey: process.env.VISION_API_KEY,
  enabled: true,
  capabilities: ['capture', 'ocr', 'describe', 'watch']
};
```

### 2. State Graph Node

Add vision node to AgentOrchestrator state graph:

```javascript
// In src/main/services/mcp/AgentOrchestrator.cjs

async processVisionQuery(state) {
  const { message, context } = state;
  
  try {
    // Call vision service via MCPClient
    const result = await this.mcpClient.callService('vision', 'describe', {
      include_ocr: true,
      store_to_memory: true,  // Auto-store as embedding
      task: message
    });
    
    return {
      ...state,
      visionResult: result.data,
      hasVisualContext: true,
      response: result.data.description
    };
    
  } catch (error) {
    console.error('Vision processing failed:', error);
    return {
      ...state,
      visionError: error.message,
      hasVisualContext: false
    };
  }
}
```

### 3. Intent Detection

Detect when user needs vision capabilities:

```javascript
// In intent classification
const visionIntents = [
  /what('s| is) on (my )?screen/i,
  /what do you see/i,
  /describe (this|what|the screen)/i,
  /read (this|the screen)/i,
  /what does (this|it) say/i,
  /help me understand this/i
];

if (visionIntents.some(pattern => pattern.test(message))) {
  intent = 'vision_query';
  requiresVision = true;
}
```

### 4. State Graph Routing

Add vision node to state graph transitions:

```javascript
// In StateGraph definition
const visionGraph = new StateGraph({
  nodes: {
    // ... existing nodes
    
    vision: async (state) => {
      return await this.processVisionQuery(state);
    }
  },
  
  edges: {
    parseIntent: (state) => {
      if (state.intent === 'vision_query') return 'vision';
      // ... other routing
    },
    
    vision: (state) => {
      // Vision result stored in memory, continue to answer
      return 'answer';
    }
  }
});
```

## Usage Examples

### Example 1: "What's on my screen?"

```
User: "What's on my screen?"
  ↓
Intent: vision_query
  ↓
State Graph: parseIntent → vision → answer
  ↓
Vision Service:
  - Capture screenshot
  - Run OCR (200ms)
  - Run VLM (600ms with GPU)
  - Generate description
  - Store to user-memory as embedding
  - Return description
  ↓
Response: "You have VS Code open with a Python file. The file contains..."
```

### Example 2: "Help me understand this page"

```
User: "Help me understand this page"
  ↓
Intent: vision_query
  ↓
Vision Service:
  - Capture
  - OCR + VLM
  - Store with task context
  ↓
User Memory:
  - Embedding: "VS Code editor showing Python file with function definitions..."
  - Metadata: {type: 'screen_capture', has_ocr: true, has_description: true}
  - NO screenshot file stored!
  ↓
Response: "This appears to be a Python development environment..."
```

### Example 3: Watch Mode (Background Monitoring)

```javascript
// Start watch when user enables "screen awareness"
await mcpClient.callService('vision', 'watch/start', {
  interval_ms: 3000,
  change_threshold: 0.10,
  run_ocr: true,
  run_vlm: false  // OCR only for performance
});

// Watch loop automatically:
// 1. Captures every 3s
// 2. Detects changes
// 3. Runs OCR on changes
// 4. Stores to user-memory
// 5. No manual intervention needed

// Stop when user disables
await mcpClient.callService('vision', 'watch/stop', {});
```

## Performance Considerations

### On-Demand Queries (User asks "what's on screen?")

**With GPU:**
- Capture: 15ms
- OCR: 300ms
- VLM: 600ms
- Store: 50ms
- **Total: ~1s** ✅ Great UX

**CPU Only:**
- Capture: 15ms
- OCR: 400ms
- VLM: 4s
- Store: 50ms
- **Total: ~4.5s** ⚠️ Show loading indicator

**OCR Only (No VLM):**
- Capture: 15ms
- OCR: 300ms
- Store: 50ms
- **Total: ~400ms** ✅ Very fast

### Watch Mode (Background)

**Recommended Config:**
```javascript
{
  interval_ms: 3000,        // Check every 3s
  change_threshold: 0.10,   // Only process meaningful changes
  run_ocr: true,            // Text extraction
  run_vlm: false            // Skip VLM for performance
}
```

**Performance:**
- No-change cycles: <50ms (fingerprint comparison)
- Change detected: ~300ms (OCR)
- Minimal CPU impact
- Embeddings stored, no disk bloat

## Storage Strategy

### Traditional Approach (Bad)
```
Screenshot → Save PNG file (2MB) → Store path in DB
Problems:
- Disk fills up quickly
- Hard to search
- Privacy concerns
- Manual cleanup needed
```

### Embedding-First Approach (Good)
```
Screenshot → OCR + VLM → Generate description → Create embedding → Store in user-memory
Benefits:
- Tiny storage (~2KB per capture)
- Semantic search works
- Auto-cleanup (old embeddings expire)
- Privacy-friendly (description, not pixels)
```

### Implementation
```javascript
// Vision service automatically handles this
const result = await mcpClient.callService('vision', 'describe', {
  store_to_memory: true  // This is the magic flag
});

// Behind the scenes:
// 1. Vision service processes screenshot
// 2. Generates description + OCR text
// 3. POSTs to user-memory service
// 4. User-memory generates embedding
// 5. Stores in database
// 6. Vision service deletes temp screenshot
// 7. Returns description to orchestrator

// Result: No files, just searchable embeddings!
```

## Testing Integration

### 1. Test Vision Service Alone
```bash
cd mcp-services/vision-service
./start.sh

# In another terminal
python3 test_service.py
```

### 2. Test via MCPClient
```javascript
// In Node.js/Electron
const MCPClient = require('./src/main/services/mcp/MCPClient.cjs');
const client = new MCPClient(MCPConfigManager);

const result = await client.callService('vision', 'describe', {
  include_ocr: true,
  store_to_memory: false  // Test without storage first
});

console.log(result);
```

### 3. Test Full Pipeline
```javascript
// In AgentOrchestrator
const state = {
  message: "What's on my screen?",
  intent: 'vision_query',
  context: {}
};

const result = await orchestrator.processVisionQuery(state);
console.log(result.response);
```

## Error Handling

### Vision Service Unavailable
```javascript
try {
  const result = await mcpClient.callService('vision', 'describe', {});
} catch (error) {
  if (error.code === 'SERVICE_UNAVAILABLE') {
    // Fallback: "I don't have visual access right now"
    return fallbackResponse(state);
  }
}
```

### VLM Not Loaded (CPU-only setup)
```javascript
// Vision service gracefully degrades to OCR-only
const result = await mcpClient.callService('vision', 'describe', {
  include_ocr: true
});

if (result.data.vlm_disabled) {
  // Response based on OCR text only
  // Still useful for reading screen content
}
```

### User Memory Storage Failed
```javascript
// Vision service logs warning but continues
// Description still returned to user
// Can retry storage later
if (result.data.memory_storage_error) {
  console.warn('Vision result not stored:', result.data.memory_storage_error);
}
```

## Next Steps

1. **Phase 1: Test in Isolation** ✅ (You are here)
   - Start vision service
   - Run test_service.py
   - Verify all endpoints work

2. **Phase 2: Add to State Graph**
   - Create vision node in AgentOrchestrator
   - Add intent detection
   - Wire up routing

3. **Phase 3: Test Integration**
   - Test via MCPClient
   - Test full pipeline
   - Verify memory storage

4. **Phase 4: UI Integration**
   - Add "What do you see?" button
   - Show visual context in responses
   - Enable watch mode toggle

## Configuration Checklist

- [ ] Vision service running on port 3006
- [ ] User-memory service running on port 3003
- [ ] API keys configured in .env files
- [ ] PaddleOCR models downloaded (~100MB)
- [ ] VLM model downloaded if enabled (~2.4GB)
- [ ] MCPConfigManager knows about vision service
- [ ] State graph has vision node
- [ ] Intent classification detects vision queries

## Questions?

See README.md for detailed API documentation and troubleshooting.
