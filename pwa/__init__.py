try:
    from .manager import inject_pwa
except ImportError:
    from manager import inject_pwa

__all__ = ["inject_pwa"]
