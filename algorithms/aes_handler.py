from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from typing import Tuple


class AESHandler:
    
    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError(f"AES-256 требует ключ размером 32 байта, получено {len(key)}")
        
        self.key = key
        self.backend = default_backend()
    
    def encrypt(self, data: bytes, iv: bytes, associated_data: bytes = b'') -> Tuple[bytes, bytes]:
        if len(iv) != 16:
            raise ValueError(f"IV должен быть 16 байт, получено {len(iv)}")

        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv),
            backend=self.backend
        )
        
        encryptor = cipher.encryptor()

        if associated_data:
            encryptor.authenticate_additional_data(associated_data)

        ciphertext = encryptor.update(data) + encryptor.finalize()

        tag = encryptor.tag
        
        return ciphertext, tag
    
    def decrypt(self, data: bytes, iv: bytes, tag: bytes, 
                associated_data: bytes = b'') -> bytes:
        if len(iv) != 16:
            raise ValueError(f"IV должен быть 16 байт, получено {len(iv)}")
        
        if len(tag) != 16:
            raise ValueError(f"Tag должен быть 16 байт, получено {len(tag)}")

        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv, tag),
            backend=self.backend
        )
        
        decryptor = cipher.decryptor()

        if associated_data:
            decryptor.authenticate_additional_data(associated_data)

        try:
            plaintext = decryptor.update(data) + decryptor.finalize()
            return plaintext
        except Exception as e:
            raise ValueError(f"AES-GCM расшифровка не удалась: {str(e)}")