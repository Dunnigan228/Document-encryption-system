from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.backends import default_backend


class ChaChaHandler:    
    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError(f"ChaCha20 требует ключ размером 32 байта, получено {len(key)}")
        
        self.cipher = ChaCha20Poly1305(key)
    
    def encrypt(self, data: bytes, nonce: bytes, associated_data: bytes = b'') -> bytes:
        if len(nonce) != 12:
            raise ValueError(f"Nonce должен быть 12 байт, получено {len(nonce)}")
        
        return self.cipher.encrypt(nonce, data, associated_data)
    
    def decrypt(self, data: bytes, nonce: bytes, associated_data: bytes = b'') -> bytes:
        if len(nonce) != 12:
            raise ValueError(f"Nonce должен быть 12 байт, получено {len(nonce)}")
        
        try:
            return self.cipher.decrypt(nonce, data, associated_data)
        except Exception as e:
            raise ValueError(f"ChaCha20-Poly1305 расшифровка не удалась: {str(e)}")
