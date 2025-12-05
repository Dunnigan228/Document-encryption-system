

import secrets
import os


class IVGenerator:
    
    
    @staticmethod
    def generate_iv(size: int = 16) -> bytes:
        
        return secrets.token_bytes(size)
    
    @staticmethod
    def generate_nonce(size: int = 12) -> bytes:
        
        return secrets.token_bytes(size)
    
    @staticmethod
    def generate_unique_iv(size: int = 16, counter: int = 0) -> bytes:
        
        
        random_part = secrets.token_bytes(size - 8)
        counter_part = counter.to_bytes(8, 'big')
        
        return random_part + counter_part