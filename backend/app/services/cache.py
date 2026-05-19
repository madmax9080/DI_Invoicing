import time
import threading
CACHE = {}
CACHE_TTL = 120  # 2 minutes
CACHE_LOCK = threading.Lock()

def get_cache(key: str):
    now = time.time()
    with CACHE_LOCK:
        entry = CACHE.get(key)
        if not entry:
            # print(f"[CACHE MISS] {key}")
            return None
        if now - entry["time"] > CACHE_TTL:
            # print(f"[CACHE EXPIRED] {key}")
            del CACHE[key]
            return None
        # print(f"[CACHE HIT] {key}")
        return entry["data"]
    
def set_cache(key: str, data):
    with CACHE_LOCK:
        CACHE[key] = {
            "data": data,
            "time": time.time()
        }

def clear_cache(prefix: str | None = None):
    with CACHE_LOCK:
        if prefix is None:
            CACHE.clear()
            return
        for key in list(CACHE.keys()):
            if key.startswith(prefix):
                del CACHE[key]