import pytest
from src.security_utils import validate_redirect_url

def test_validate_redirect_url_safe_relative():
    assert validate_redirect_url("/dashboard") == "/dashboard"
    assert validate_redirect_url("dashboard") == "/dashboard"
    assert validate_redirect_url("/path/to/resource?query=1") == "/path/to/resource?query=1"

def test_validate_redirect_url_safe_localhost():
    assert validate_redirect_url("http://localhost:3000/callback") == "http://localhost:3000/callback"
    assert validate_redirect_url("http://127.0.0.1:8000/callback") == "http://127.0.0.1:8000/callback"

def test_validate_redirect_url_unsafe_external():
    with pytest.raises(ValueError):
        validate_redirect_url("http://evil.com")
    with pytest.raises(ValueError):
        validate_redirect_url("https://google.com")
    with pytest.raises(ValueError):
        validate_redirect_url("//evil.com")
    with pytest.raises(ValueError):
        validate_redirect_url("javascript:alert(1)")

def test_validate_redirect_url_empty():
    assert validate_redirect_url("") == "/"
    assert validate_redirect_url(None) == "/"

def test_validate_redirect_url_malformed():
    # protocol relative with spaces
    with pytest.raises(ValueError):
         validate_redirect_url(" //evil.com")
