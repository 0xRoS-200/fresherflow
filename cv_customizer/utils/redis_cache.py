"""Redis caching utility with MD5 hashing and local JSON fallback."""

import os
import hashlib
import json
import logging
import time
import threading
from typing import Any, Optional, Union, List

logger = logging.getLogger(__name__)

# Try to import redis, fail silently if not installed
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis-py package is not installed. Caching will use local fallback.")


class RedisCache:
    """Smart caching layer using Redis with graceful offline local fallback."""

    def __init__(self):
        self.enabled = os.getenv("REDIS_CACHE_ENABLED", "true").lower() == "true"
        self.host = os.getenv("REDIS_HOST", "localhost")
        if self.host.lower() == "localhost":
            self.host = "127.0.0.1"
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.db = int(os.getenv("REDIS_DB", "0"))
        self.password = os.getenv("REDIS_PASSWORD") or None
        self.client: Optional[redis.Redis] = None
        self.is_connected = False
        self.last_connect_time = 0.0
        self.connect_cooldown = 30.0  # seconds
        self.lock = threading.Lock()

        # Local cache file setup
        # Locate it relative to this file under fresherflow/data/llm_cache.json
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.local_cache_path = os.path.join(base_dir, "data", "llm_cache.json")
        os.makedirs(os.path.dirname(self.local_cache_path), exist_ok=True)
        self.local_cache = {}
        self._load_local_cache()

        if not REDIS_AVAILABLE:
            # We still keep caching enabled using the local JSON cache fallback!
            return

        if self.enabled:
            self._connect()

    def _connect(self):
        """Establish connection to Redis server (called within lock)."""
        self.last_connect_time = time.time()
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                socket_timeout=1.0,  # fail fast
                socket_connect_timeout=1.0,
                decode_responses=True
            )
            # Test connection
            self.client.ping()
            self.is_connected = True
            logger.info(f"Connected to Redis cache at {self.host}:{self.port}")
        except Exception as e:
            self.is_connected = False
            # Log as debug to prevent console spam
            logger.debug(f"Redis connection failed: {e}")

    def _ensure_connection(self) -> bool:
        """Check if cache is enabled and connected. Re-try connection once if lost with thread-safety."""
        if not self.enabled:
            return False
        if not REDIS_AVAILABLE:
            return False
        if self.is_connected and self.client:
            return True

        # Quick non-blocking check for cooldown to avoid lock overhead
        now = time.time()
        if now - self.last_connect_time < self.connect_cooldown:
            return False

        with self.lock:
            # Double-check connection status inside lock
            if self.is_connected and self.client:
                return True
            now = time.time()
            if now - self.last_connect_time < self.connect_cooldown:
                return False
            
            logger.info(f"Redis cache offline. Re-checking connection to {self.host}:{self.port}...")
            self._connect()
            return self.is_connected

    def _load_local_cache(self):
        """Load local JSON cache file."""
        if os.path.exists(self.local_cache_path):
            try:
                with open(self.local_cache_path, "r", encoding="utf-8") as f:
                    self.local_cache = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load local cache file: {e}")

    def _save_local_cache(self):
        """Save local JSON cache file."""
        try:
            with open(self.local_cache_path, "w", encoding="utf-8") as f:
                json.dump(self.local_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save local cache file: {e}")

    def get(self, key: str) -> Optional[str]:
        """Retrieve a value from the cache, falling back to local JSON cache if Redis is down."""
        if not self.enabled:
            return None

        # 1. Try Redis
        if self._ensure_connection():
            try:
                return self.client.get(key)
            except Exception as e:
                logger.warning(f"Failed to retrieve key '{key}' from Redis cache: {e}")

        # 2. Local fallback
        with self.lock:
            if key in self.local_cache:
                item = self.local_cache[key]
                if isinstance(item, dict) and "expire_at" in item:
                    if time.time() > item["expire_at"]:
                        del self.local_cache[key]
                        self._save_local_cache()
                        return None
                    return item["value"]
                return str(item)
        return None

    def set(self, key: str, value: str, ex: int = 86400) -> bool:
        """Store a value in the cache, saving to both Redis (if active) and local JSON file."""
        if not self.enabled:
            return False

        redis_success = False
        # 1. Try Redis
        if self._ensure_connection():
            try:
                self.client.set(key, value, ex=ex)
                redis_success = True
            except Exception as e:
                logger.warning(f"Failed to set key '{key}' in Redis cache: {e}")

        # 2. Write to local fallback
        with self.lock:
            self.local_cache[key] = {
                "value": value,
                "expire_at": time.time() + ex
            }
            self._save_local_cache()

        return redis_success or not self.is_connected

    def generate_key(self, prompt: str) -> str:
        """Generate a deterministic MD5 hash key for a prompt string."""
        return "cv_cache:" + hashlib.md5(prompt.encode("utf-8")).hexdigest()

    def generate_messages_key(self, messages: List[Any]) -> str:
        """Generate a deterministic MD5 hash key for a list of messages."""
        serialized = []
        for msg in messages:
            if hasattr(msg, "content"):
                serialized.append(f"{msg.__class__.__name__}:{msg.content}")
            elif isinstance(msg, dict):
                serialized.append(f"dict:{json.dumps(msg, sort_keys=True)}")
            else:
                serialized.append(f"str:{str(msg)}")
        
        combined = "||".join(serialized)
        return "cv_cache:" + hashlib.md5(combined.encode("utf-8")).hexdigest()


# Global cache instance
redis_cache = RedisCache()
