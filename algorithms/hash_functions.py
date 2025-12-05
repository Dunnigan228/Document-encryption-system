import hashlib
import hmac
from typing import Optional


class HashFunctions:
  
    @staticmethod
    def sha256(data: bytes) -> bytes:
        return hashlib.sha256(data).digest()
    
    @staticmethod
    def sha512(data: bytes) -> bytes:
        return hashlib.sha512(data).digest()
    
    @staticmethod
    def sha3_256(data: bytes) -> bytes:
        return hashlib.sha3_256(data).digest()
    
    @staticmethod
    def sha3_512(data: bytes) -> bytes:
        return hashlib.sha3_512(data).digest()
    
    @staticmethod
    def blake2b(data: bytes, digest_size: int = 64) -> bytes:
        return hashlib.blake2b(data, digest_size=digest_size).digest()
    
    @staticmethod
    def blake2s(data: bytes, digest_size: int = 32) -> bytes:
        return hashlib.blake2s(data, digest_size=digest_size).digest()
    
    @staticmethod
    def hmac_sha256(data: bytes, key: bytes) -> bytes:
        return hmac.new(key, data, hashlib.sha256).digest()
    
    @staticmethod
    def hmac_sha512(data: bytes, key: bytes) -> bytes:
        return hmac.new(key, data, hashlib.sha512).digest()
    
    @staticmethod
    def pbkdf2_hmac(password: bytes, salt: bytes, iterations: int, 
                    dklen: int, hash_name: str = 'sha512') -> bytes:
        return hashlib.pbkdf2_hmac(hash_name, password, salt, iterations, dklen)
    
    @staticmethod
    def scrypt(password: bytes, salt: bytes, n: int = 2**14, 
               r: int = 8, p: int = 1, dklen: int = 32) -> bytes:
        
        return hashlib.scrypt(password, salt=salt, n=n, r=r, p=p, dklen=dklen)
    
    @staticmethod
    def compare_digest(a: bytes, b: bytes) -> bool:
        
        return hmac.compare_digest(a, b)
    
    @staticmethod
    def cascade_hash(data: bytes) -> bytes:
        
        
        h1 = hashlib.sha512(data).digest()
        h2 = hashlib.sha3_512(h1).digest()
        h3 = hashlib.blake2b(h2, digest_size=64).digest()
        
        return h3
    
    @staticmethod
    def multi_round_hash(data: bytes, rounds: int = 10000, 
                        algorithm: str = 'sha512') -> bytes:
        
        result = data
        hash_func = getattr(hashlib, algorithm)
        
        for _ in range(rounds):
            result = hash_func(result).digest()
        
        return result
