

import os
import json
import base64
from pathlib import Path
from typing import Dict, Optional
from cryptography.fernet import Fernet


class KeyStorage:
    
    
    def __init__(self, storage_dir: Optional[Path] = None):
        
        self.storage_dir = storage_dir or Path('keys')
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def store_key(self, 
                  key_id: str, 
                  key_data: bytes, 
                  protection_password: Optional[str] = None):
        
        key_file = self.storage_dir / f"{key_id}.key"
        
        if protection_password:
            
            encrypted_data = self._encrypt_key(key_data, protection_password)
            data_to_save = {
                'encrypted': True,
                'data': base64.b64encode(encrypted_data).decode('utf-8')
            }
        else:
            data_to_save = {
                'encrypted': False,
                'data': base64.b64encode(key_data).decode('utf-8')
            }
        
        with open(key_file, 'w') as f:
            json.dump(data_to_save, f)
    
    def retrieve_key(self, 
                     key_id: str, 
                     protection_password: Optional[str] = None) -> bytes:
        
        key_file = self.storage_dir / f"{key_id}.key"
        
        if not key_file.exists():
            raise FileNotFoundError(f"Ключ не найден: {key_id}")
        
        with open(key_file, 'r') as f:
            stored_data = json.load(f)
        
        key_data = base64.b64decode(stored_data['data'])
        
        if stored_data['encrypted']:
            if not protection_password:
                raise ValueError("Требуется пароль для расшифровки ключа")
            
            return self._decrypt_key(key_data, protection_password)
        
        return key_data
    
    def delete_key(self, key_id: str):
        
        key_file = self.storage_dir / f"{key_id}.key"
        
        if key_file.exists():
            
            self._secure_delete(key_file)
    
    def _encrypt_key(self, key_data: bytes, password: str) -> bytes:
        
        from algorithms.hash_functions import HashFunctions
        
        
        salt = os.urandom(32)
        derived_key = HashFunctions.pbkdf2_hmac(
            password.encode(),
            salt,
            iterations=600000,
            dklen=32
        )
        
        
        fernet_key = base64.urlsafe_b64encode(derived_key)
        fernet = Fernet(fernet_key)
        
        encrypted = fernet.encrypt(key_data)
        
        
        return salt + encrypted
    
    def _decrypt_key(self, encrypted_data: bytes, password: str) -> bytes:
        
        from algorithms.hash_functions import HashFunctions
        
        
        salt = encrypted_data[:32]
        encrypted_key = encrypted_data[32:]
        
        
        derived_key = HashFunctions.pbkdf2_hmac(
            password.encode(),
            salt,
            iterations=600000,
            dklen=32
        )
        
        
        fernet_key = base64.urlsafe_b64encode(derived_key)
        fernet = Fernet(fernet_key)
        
        return fernet.decrypt(encrypted_key)
    
    def _secure_delete(self, filepath: Path):
        
        
        file_size = filepath.stat().st_size
        
        with open(filepath, 'rb+') as f:
            for _ in range(3):
                f.seek(0)
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())
        
        filepath.unlink()
