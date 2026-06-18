#!/usr/bin/env python3
"""
Unit tests for Redis Cache layer with fallback verification.
"""

import sys
import os

# Add cv_customizer to python path if not already
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from cv_customizer.utils.redis_cache import redis_cache, RedisCache

def print_status(message: str, success: bool = True):
    status = "\033[92m[OK]\033[0m" if success else "\033[91m[FAIL]\033[0m"
    print(f"{status} {message}")

def test_cache_key_generation():
    print("\n--- Test 1: Cache Key Generation ---")
    prompt = "Translate this CV to English."
    key = redis_cache.generate_key(prompt)
    print(f"Generated key for prompt: {key}")
    
    assert key.startswith("cv_cache:")
    assert len(key) == 9 + 32  # cv_cache: + 32 hex chars
    print_status("Deterministic MD5 hashing key generation passes")

def test_cache_operations_with_offline_fallback():
    print("\n--- Test 2: Set/Get and Offline Fallback ---")
    cache = RedisCache()
    
    print(f"Redis Cache enabled configuration: {cache.enabled}")
    print(f"Redis Cache connection status: {cache.is_connected}")
    
    key = "cv_cache:test_key_12345"
    value = '{"content": "mock content data", "tokens_used": {"input": 12, "output": 34, "total": 46}}'
    
    if cache.is_connected:
        print("Redis is online. Testing active caching operations...")
        success_set = cache.set(key, value, ex=10)
        print_status(f"Cache set operation: {'Success' if success_set else 'Failed'}", success_set)
        
        cached_val = cache.get(key)
        print(f"Cached val: {cached_val}")
        assert cached_val == value
        print_status("Cache retrieval matches set value")
    else:
        print("Redis is offline (expected for sandbox/local environments without running Redis server).")
        print("Verifying offline fallback to local JSON file caching...")
        
        # Should return True for set because of local JSON fallback
        success_set = cache.set(key, value)
        print(f"Cache set returned: {success_set}")
        assert success_set is True
        print_status("Cache set succeeds via local JSON fallback when offline")
        
        # Should return cached value because of local JSON fallback
        cached_val = cache.get(key)
        print(f"Cache get returned: {cached_val}")
        assert cached_val == value
        print_status("Cache get successfully retrieves value from local JSON fallback when offline")

def main():
    print("============================================================")
    print("  FresherFlow Redis Cache - Test Suite")
    print("============================================================\n")
    try:
        test_cache_key_generation()
        test_cache_operations_with_offline_fallback()
        print("\n============================================================")
        print("  Redis Cache tests complete: ALL PASSED")
        print("============================================================")
    except AssertionError as e:
        print(f"\nAssertion error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
