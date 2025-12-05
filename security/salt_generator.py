

import os
import secrets
import hashlib
import time


class SaltGenerator:
    
    
    @staticmethod
    def generate_salt(size: int = 32) -> bytes:
        
        
        return secrets.token_bytes(size)
    
    @staticmethod
    def generate_enhanced_salt(size: int = 32) -> bytes:
        
        
        entropy_sources = [
            secrets.token_bytes(size),
            os.urandom(size),
            hashlib.sha256(str(time.time_ns()).encode()).digest()[:size],
            hashlib.sha256(str(os.getpid()).encode()).digest()[:size]
        ]
        
        
        combined = b''.join(entropy_sources)
        
        
        final_salt = hashlib.blake2b(combined, digest_size=size).digest()
        
        return final_salt
    
    @staticmethod
    def generate_salt_with_pepper(size: int = 32, pepper: bytes = b'') -> bytes:
        
        base_salt = secrets.token_bytes(size)
        
        if pepper:
            
            combined = base_salt + pepper
            return hashlib.blake2b(combined, digest_size=size).digest()
        
        return base_salt
