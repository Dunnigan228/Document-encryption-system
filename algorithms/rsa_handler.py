

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from typing import Optional


class RSAHandler:
    
    
    def __init__(self, public_key=None, private_key=None):
        
        self.public_key = public_key
        self.private_key = private_key
        
        
        self.padding_config = padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    
    def encrypt(self, data: bytes) -> bytes:
        
        if not self.public_key:
            raise ValueError("Публичный ключ не установлен")
        
        
        
        max_chunk_size = 446
        
        if len(data) <= max_chunk_size:
            return self.public_key.encrypt(data, self.padding_config)
        
        
        encrypted_chunks = []
        for i in range(0, len(data), max_chunk_size):
            chunk = data[i:i + max_chunk_size]
            encrypted_chunk = self.public_key.encrypt(chunk, self.padding_config)
            encrypted_chunks.append(encrypted_chunk)
        
        
        result = b''
        for chunk in encrypted_chunks:
            
            result += len(chunk).to_bytes(2, 'big') + chunk
        
        return result
    
    def decrypt(self, data: bytes) -> bytes:
        
        if not self.private_key:
            raise ValueError("Приватный ключ не установлен")
        
        
        rsa_block_size = 512  
        
        
        if len(data) <= rsa_block_size:
            return self.private_key.decrypt(data, self.padding_config)
        
        
        decrypted_chunks = []
        offset = 0
        
        while offset < len(data):
            
            chunk_len = int.from_bytes(data[offset:offset + 2], 'big')
            offset += 2
            
            
            encrypted_chunk = data[offset:offset + chunk_len]
            decrypted_chunk = self.private_key.decrypt(encrypted_chunk, self.padding_config)
            decrypted_chunks.append(decrypted_chunk)
            
            offset += chunk_len
        
        return b''.join(decrypted_chunks)
