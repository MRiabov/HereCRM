import os
import pytest

# Inject dummy keys BEFORE standard imports can fail
os.environ["GOOGLE_API_KEY"] = "dummy_test_key"
os.environ["WHATSAPP_APP_SECRET"] = "dummy_secret"
os.environ["WA_TOKEN"] = "dummy_token"
os.environ["WA_PHONE_ID"] = "dummy_phone_id"


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    # This fixture ensures these remain set, though the top-level
    # execution is what really saves us from import errors.
    os.environ["GOOGLE_API_KEY"] = "dummy_test_key"
    os.environ["WHATSAPP_APP_SECRET"] = "dummy_secret"
    os.environ["WA_TOKEN"] = "dummy_token"
    os.environ["WA_PHONE_ID"] = "dummy_phone_id"
    yield
