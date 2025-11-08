#!/usr/bin/env python3
"""
Vision Service Test Script
Tests all endpoints in isolation
"""

import httpx
import json
import time
import sys

BASE_URL = "http://localhost:3006"

def print_test(name):
    print(f"\n{'='*60}")
    print(f"🧪 TEST: {name}")
    print(f"{'='*60}")

def print_result(success, message, data=None):
    icon = "✅" if success else "❌"
    print(f"{icon} {message}")
    if data:
        print(f"   Data: {json.dumps(data, indent=2)[:200]}...")

async def test_health():
    """Test health endpoint"""
    print_test("Health Check")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            data = response.json()
            print_result(
                response.status_code == 200,
                f"Health check (status={data.get('status')})",
                data
            )
            return response.status_code == 200
    except Exception as e:
        print_result(False, f"Health check failed: {e}")
        return False

async def test_capabilities():
    """Test capabilities endpoint"""
    print_test("Service Capabilities")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/service.capabilities")
            data = response.json()
            print_result(
                response.status_code == 200,
                f"Capabilities ({len(data.get('endpoints', []))} endpoints)",
                data
            )
            return response.status_code == 200
    except Exception as e:
        print_result(False, f"Capabilities check failed: {e}")
        return False

async def test_capture():
    """Test screenshot capture"""
    print_test("Screenshot Capture")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            start = time.time()
            response = await client.post(
                f"{BASE_URL}/vision/capture",
                json={}
            )
            elapsed = time.time() - start
            
            data = response.json()
            result_data = data.get('data', {})
            
            print_result(
                response.status_code == 200,
                f"Capture ({result_data.get('width')}x{result_data.get('height')}, {elapsed*1000:.0f}ms)",
                {"width": result_data.get('width'), "height": result_data.get('height')}
            )
            return response.status_code == 200
    except Exception as e:
        print_result(False, f"Capture failed: {e}")
        return False

async def test_ocr():
    """Test OCR"""
    print_test("OCR Text Extraction")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.time()
            response = await client.post(
                f"{BASE_URL}/vision/ocr",
                json={}
            )
            elapsed = time.time() - start
            
            data = response.json()
            result_data = data.get('data', {})
            
            print_result(
                response.status_code == 200,
                f"OCR ({result_data.get('count', 0)} items, {elapsed*1000:.0f}ms)",
                {"count": result_data.get('count'), "sample": result_data.get('concat', '')[:100]}
            )
            return response.status_code == 200
    except Exception as e:
        print_result(False, f"OCR failed: {e}")
        return False

async def test_describe():
    """Test VLM description"""
    print_test("VLM Scene Description")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            start = time.time()
            response = await client.post(
                f"{BASE_URL}/vision/describe",
                json={
                    "include_ocr": True,
                    "store_to_memory": False,  # Don't store during test
                    "task": "Describe what you see"
                }
            )
            elapsed = time.time() - start
            
            data = response.json()
            result_data = data.get('data', {})
            
            has_description = 'description' in result_data
            has_ocr = 'ocr' in result_data
            
            print_result(
                response.status_code == 200,
                f"Describe (VLM={'✓' if has_description else '✗'}, OCR={'✓' if has_ocr else '✗'}, {elapsed*1000:.0f}ms)",
                {
                    "description": result_data.get('description', 'N/A')[:100],
                    "ocr_count": len(result_data.get('ocr', {}).get('items', []))
                }
            )
            return response.status_code == 200
    except Exception as e:
        print_result(False, f"Describe failed: {e}")
        return False

async def test_watch():
    """Test watch mode"""
    print_test("Watch Mode")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Start watch
            response = await client.post(
                f"{BASE_URL}/vision/watch/start",
                json={
                    "interval_ms": 2000,
                    "change_threshold": 0.08,
                    "run_ocr": False,
                    "run_vlm": False
                }
            )
            start_data = response.json()
            print_result(
                response.status_code == 200,
                "Watch started",
                start_data.get('data')
            )
            
            # Wait a bit
            time.sleep(3)
            
            # Check status
            response = await client.get(f"{BASE_URL}/vision/watch/status")
            status_data = response.json()
            print_result(
                response.status_code == 200,
                f"Watch status (running={status_data.get('data', {}).get('running')})",
                status_data.get('data')
            )
            
            # Stop watch
            response = await client.post(f"{BASE_URL}/vision/watch/stop")
            stop_data = response.json()
            print_result(
                response.status_code == 200,
                "Watch stopped",
                stop_data.get('data')
            )
            
            return True
    except Exception as e:
        print_result(False, f"Watch test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("👁️  VISION SERVICE TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Basic tests
    results['health'] = await test_health()
    if not results['health']:
        print("\n❌ Service not running! Start with: ./start.sh")
        return False
    
    results['capabilities'] = await test_capabilities()
    results['capture'] = await test_capture()
    results['ocr'] = await test_ocr()
    results['describe'] = await test_describe()
    results['watch'] = await test_watch()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        icon = "✅" if result else "❌"
        print(f"{icon} {test.upper()}")
    
    print(f"\n{'✅' if passed == total else '⚠️ '} {passed}/{total} tests passed")
    
    return passed == total

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
