

import os
import json
import secrets
from typing import Dict, Tuple, Optional
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend


class KeyManager:
    
    
    def __init__(self):
        self.backend = default_backend()
    
    def generate_master_password(self, length: int = 32) -> str:
        
        
        alphabet = (
            'abcdefghijklmnopqrstuvwxyz'
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            '0123456789'
            '!@#$%^&*()_+-=[]{}|;:,.<>?'
        )
        
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    def generate_rsa_keypair(self, key_size: int = 4096) -> Tuple:
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=self.backend
        )
        
        public_key = private_key.public_key()
        
        return public_key, private_key
    
    def serialize_private_key(self, private_key, password: Optional[str] = None) -> bytes:
        
        encryption_algorithm = serialization.NoEncryption()
        
        if password:
            encryption_algorithm = serialization.BestAvailableEncryption(
                password.encode()
            )
        
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption_algorithm
        )
    
    def serialize_public_key(self, public_key) -> bytes:
        
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def deserialize_private_key(self, key_bytes: bytes, password: Optional[str] = None):
        
        password_bytes = password.encode() if password else None
        
        return serialization.load_pem_private_key(
            key_bytes,
            password=password_bytes,
            backend=self.backend
        )
    
    def deserialize_public_key(self, key_bytes: bytes):
        
        return serialization.load_pem_public_key(
            key_bytes,
            backend=self.backend
        )
    
    def save_key_bundle(self, key_bundle: Dict, filepath: str, password: Optional[str] = None):
        
        
        import base64
        
        serializable_bundle = {}
        for key, value in key_bundle.items():
            if isinstance(value, bytes):
                serializable_bundle[key] = base64.b64encode(value).decode('utf-8')
            else:
                serializable_bundle[key] = value
        
        
        if password:
            from algorithms.aes_handler import AESHandler
            from security.password_derivation import PasswordDerivation
            from security.salt_generator import SaltGenerator
            
            salt_gen = SaltGenerator()
            pwd_deriv = PasswordDerivation()
            
            salt = salt_gen.generate_salt(32)
            key = pwd_deriv.derive_key(password, salt, 32, 600000)
            
            aes = AESHandler(key)
            iv = os.urandom(16)
            
            json_data = json.dumps(serializable_bundle).encode()
            encrypted_data, tag = aes.encrypt(json_data, iv, b'')
            
            
            protected_bundle = {
                'encrypted': True,
                'salt': base64.b64encode(salt).decode('utf-8'),
                'iv': base64.b64encode(iv).decode('utf-8'),
                'tag': base64.b64encode(tag).decode('utf-8'),
                'data': base64.b64encode(encrypted_data).decode('utf-8')
            }
            
            with open(filepath, 'w') as f:
                json.dump(protected_bundle, f, indent=2)
        else:
            
            with open(filepath, 'w') as f:
                json.dump(serializable_bundle, f, indent=2)
    
    def load_key_bundle(self, filepath: str, password: Optional[str] = None) -> Dict:
        
        import base64
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        
        if data.get('encrypted'):
            if not password:
                raise ValueError("Требуется пароль для расшифровки ключей")
            
            from algorithms.aes_handler import AESHandler
            from security.password_derivation import PasswordDerivation
            
            pwd_deriv = PasswordDerivation()
            
            salt = base64.b64decode(data['salt'])
            iv = base64.b64decode(data['iv'])
            tag = base64.b64decode(data['tag'])
            encrypted_data = base64.b64decode(data['data'])
            
            key = pwd_deriv.derive_key(password, salt, 32, 600000)
            aes = AESHandler(key)
            
            decrypted_json = aes.decrypt(encrypted_data, iv, tag, b'')
            serializable_bundle = json.loads(decrypted_json.decode())
        else:
            serializable_bundle = data
        
        
        key_bundle = {}
        for key, value in serializable_bundle.items():
            if key in ['master_key', 'aes_key', 'chacha_key', 'hmac_key', 
                      'salt', 'aes_iv', 'chacha_nonce', 'rsa_private_key', 'rsa_public_key']:
                key_bundle[key] = base64.b64decode(value)
            else:
                key_bundle[key] = value
        
        return key_bundle
