from typing import Dict, List, Optional, Any
import threading


class ServiceCatalogCache:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ServiceCatalogCache, cls).__new__(cls)
                cls._instance._cache = {}  # type: Dict[int, List[Dict[str, Any]]]
            return cls._instance

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            return cls()
        return cls._instance

    def get_services_data(self, business_id: int) -> Optional[List[Dict[str, Any]]]:
        # Return a copy to ensure immutability of cache content
        data = self._cache.get(business_id)
        if data is None:
            return None
        return [d.copy() for d in data]

    def set_services_data(self, business_id: int, services_data: List[Dict[str, Any]]):
        # Store a copy
        self._cache[business_id] = [d.copy() for d in services_data]

    def invalidate(self, business_id: int):
        if business_id in self._cache:
            del self._cache[business_id]

    def clear(self):
        """Used for testing and resetting state"""
        with self._lock:
            self._cache = {}
