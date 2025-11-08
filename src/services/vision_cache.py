"""
Vision Cache - Smart caching for vision results
"""

import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class VisionCache:
    """
    Multi-level caching for vision results
    
    Features:
        - In-memory caching with TTL
        - Fingerprint-based deduplication
        - Automatic cleanup of expired entries
    """
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 100):
        """
        Initialize cache
        
        Args:
            ttl_seconds: Time-to-live for cached entries (default: 5 minutes)
            max_size: Maximum number of cached entries
        """
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"VisionCache initialized (TTL: {ttl_seconds}s, max_size: {max_size})")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached result
        
        Args:
            key: Cache key (usually fingerprint)
            
        Returns:
            Cached result or None if not found/expired
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        if time.time() - entry['timestamp'] > self.ttl:
            del self._cache[key]
            logger.debug(f"Cache entry expired: {key}")
            return None
        
        logger.debug(f"Cache hit: {key}")
        return entry['result']
    
    def set(self, key: str, result: Dict[str, Any]):
        """
        Cache result
        
        Args:
            key: Cache key
            result: Result to cache
        """
        # Cleanup if cache is full
        if len(self._cache) >= self.max_size:
            self._cleanup_oldest()
        
        self._cache[key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        logger.debug(f"Cached result: {key}")
    
    def clear(self):
        """Clear all cached entries"""
        self._cache.clear()
        logger.info("Cache cleared")
    
    def _cleanup_oldest(self):
        """Remove oldest entries when cache is full"""
        if not self._cache:
            return
        
        # Sort by timestamp and remove oldest 20%
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1]['timestamp']
        )
        
        num_to_remove = max(1, len(sorted_entries) // 5)
        
        for key, _ in sorted_entries[:num_to_remove]:
            del self._cache[key]
        
        logger.debug(f"Cleaned up {num_to_remove} old cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = time.time()
        active_entries = sum(
            1 for entry in self._cache.values()
            if now - entry['timestamp'] <= self.ttl
        )
        
        return {
            'total_entries': len(self._cache),
            'active_entries': active_entries,
            'max_size': self.max_size,
            'ttl_seconds': self.ttl
        }
