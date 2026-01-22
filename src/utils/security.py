import hmac
import hashlib

class Signer:
    @staticmethod
    def sign(data: str, secret: str) -> str:
        """Sign data using HMAC-SHA256."""
        return hmac.new(
            secret.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify(data: str, signature: str, secret: str) -> bool:
        """Verify the signature of the data."""
        expected_signature = Signer.sign(data, secret)
        return hmac.compare_digest(signature, expected_signature)
