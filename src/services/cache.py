from typing import Dict, List, Any, Optional
from threading import Lock

class ServiceCatalogCache:
    _instance = None
    _lock = Lock()

    def __init__(self):
        self._cache: Dict[int, List[Dict[str, Any]]] = {}
        self._versions: Dict[int, int] = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get(self, business_id: int) -> Optional[List[Dict[str, Any]]]:
        return self._cache.get(business_id)

    def set(self, business_id: int, data: List[Dict[str, Any]], version: int):
        """
        Only set the cache if the current version matches the expected version.
        This prevents overwriting invalidations that happened during the fetch.
        """
        current_version = self._versions.get(business_id, 0)
        if current_version == version:
            self._cache[business_id] = data

    def invalidate(self, business_id: int):
        if business_id in self._cache:
            del self._cache[business_id]
        # Increment version to prevent pending writes from stale reads
        self._versions[business_id] = self._versions.get(business_id, 0) + 1

    def get_version(self, business_id: int) -> int:
        return self._versions.get(business_id, 0)

    def clear(self):
        self._cache.clear()
        self._versions.clear()
