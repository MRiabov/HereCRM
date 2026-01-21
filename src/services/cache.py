from typing import Dict, List, Any, Optional
from threading import Lock

class ServiceCatalogCache:
    _instance = None
    _lock = Lock()

    def __init__(self):
        self._cache: Dict[int, List[Dict[str, Any]]] = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get(self, business_id: int) -> Optional[List[Dict[str, Any]]]:
        return self._cache.get(business_id)

    def set(self, business_id: int, data: List[Dict[str, Any]]):
        self._cache[business_id] = data

    def invalidate(self, business_id: int):
        if business_id in self._cache:
            del self._cache[business_id]

    def clear(self):
        self._cache.clear()
