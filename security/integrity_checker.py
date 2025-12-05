

import hmac
import hashlib
from typing import Optional


class IntegrityChecker:
    
    
    @staticmethod
    def create_hmac(data: bytes, key: bytes, algorithm: str = 'sha512') -> bytes:
        
        hash_func = getattr(hashlib, algorithm)
        return hmac.new(key, data, hash_func).digest()
    
    @staticmethod
    def verify_hmac(data: bytes, hmac_signature: bytes, key: bytes,
                   algorithm: str = 'sha512') -> bool:
        
        expected_hmac = IntegrityChecker.create_hmac(data, key, algorithm)
        
        
        return hmac.compare_digest(expected_hmac, hmac_signature)
    
    @staticmethod
    def create_checksum(data: bytes, algorithm: str = 'sha256') -> bytes:
        
        hash_func = getattr(hashlib, algorithm)
        return hash_func(data).digest()
    
    @staticmethod
    def verify_checksum(data: bytes, expected_checksum: bytes,
                       algorithm: str = 'sha256') -> bool:
        
        actual_checksum = IntegrityChecker.create_checksum(data, algorithm)
        return hmac.compare_digest(actual_checksum, expected_checksum)
    
    @staticmethod
    def create_authenticated_encryption_tag(ciphertext: bytes, 
                                           associated_data: bytes,
                                           key: bytes) -> bytes:
        
        
        combined = ciphertext + associated_data
        
        return IntegrityChecker.create_hmac(combined, key)
    
    @staticmethod
    def verify_authenticated_encryption(ciphertext: bytes,
                                       associated_data: bytes,
                                       tag: bytes,
                                       key: bytes) -> bool:
        
        expected_tag = IntegrityChecker.create_authenticated_encryption_tag(
            ciphertext, associated_data, key
        )
        
        return hmac.compare_digest(expected_tag, tag)
    
    @staticmethod
    def create_cascade_checksum(data: bytes) -> bytes:
        
        
        h1 = hashlib.sha512(data).digest()
        h2 = hashlib.sha3_512(data + h1).digest()
        h3 = hashlib.blake2b(data + h2, digest_size=64).digest()
        
        
        return h1 + h2 + h3
    
    @staticmethod
    def verify_cascade_checksum(data: bytes, cascade_checksum: bytes) -> bool:
        
        expected = IntegrityChecker.create_cascade_checksum(data)
        return hmac.compare_digest(expected, cascade_checksum)