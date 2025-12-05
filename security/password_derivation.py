

import hashlib
import hmac
from typing import Optional


class PasswordDerivation:
    
    
    @staticmethod
    def derive_key(password: str, salt: bytes, key_length: int, 
                   iterations: int = 600000, algorithm: str = 'sha512') -> bytes:
        
        password_bytes = password.encode('utf-8')
        
        return hashlib.pbkdf2_hmac(
            algorithm,
            password_bytes,
            salt,
            iterations,
            key_length
        )
    
    @staticmethod
    def derive_key_scrypt(password: str, salt: bytes, key_length: int,
                         n: int = 2**14, r: int = 8, p: int = 1) -> bytes:
        
        password_bytes = password.encode('utf-8')
        
        return hashlib.scrypt(
            password_bytes,
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=key_length
        )
    
    @staticmethod
    def derive_subkey(master_key: bytes, context: bytes, 
                     key_length: int) -> bytes:
        
        
        prk = hmac.new(b'', master_key, hashlib.sha512).digest()
        
        
        okm = b''
        counter = 1
        
        while len(okm) < key_length:
            okm += hmac.new(
                prk,
                okm[-64:] + context + bytes([counter]),
                hashlib.sha512
            ).digest()
            counter += 1
        
        return okm[:key_length]
    
    @staticmethod
    def derive_multiple_keys(password: str, salt: bytes, 
                            key_lengths: list, iterations: int = 600000) -> list:
        
        
        total_length = sum(key_lengths)
        master_key = PasswordDerivation.derive_key(
            password, salt, total_length, iterations
        )
        
        
        keys = []
        offset = 0
        
        for length in key_lengths:
            keys.append(master_key[offset:offset + length])
            offset += length
        
        return keys