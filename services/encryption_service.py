"""
Encryption Service for KingdomPay
Handles encryption and decryption operations
"""

import os
import base64
from cryptography.fernet import Fernet


class EncryptionService:
    """Service for handling encryption operations"""

    def __init__(self):
        self.encryption_key = os.environ.get("ENCRYPTION_KEY")
        if self.encryption_key:
            key_bytes = None
            # Allow key as base64 urlsafe 32-byte, hex 32-byte, or raw 32-byte
            try:
                # Try base64 first (recommended)
                key_bytes = base64.urlsafe_b64decode(self.encryption_key)
            except Exception:
                pass
            if not key_bytes:
                if len(self.encryption_key) == 64:
                    # 32 bytes hex
                    key_bytes = bytes.fromhex(self.encryption_key)
                elif len(self.encryption_key) == 32:
                    key_bytes = self.encryption_key.encode()
            if key_bytes and len(key_bytes) == 32:
                # Fernet requires a 32-byte key, base64-urlsafe encoded
                fernet_key = base64.urlsafe_b64encode(key_bytes)
                self.fernet = Fernet(fernet_key)
            else:
                # Misconfigured key
                self.fernet = None
        else:
            self.fernet = None

    def encrypt_data(self, data):
        """Encrypt sensitive data"""
        if not self.fernet:
            return data
        if isinstance(data, str):
            data = data.encode()
        return self.fernet.encrypt(data)

    def decrypt_data(self, encrypted_data):
        """Decrypt sensitive data"""
        if not self.fernet:
            return encrypted_data
        return self.fernet.decrypt(encrypted_data)
