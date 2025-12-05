

import json
import time
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path


class MetadataManager:
    
    
    def __init__(self, metadata_dir: Optional[Path] = None):
        
        self.metadata_dir = metadata_dir or Path('metadata')
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def create_metadata(self, 
                       file_info: Dict[str, Any],
                       crypto_info: Dict[str, Any]) -> Dict[str, Any]:
        
        metadata = {
            'version': '1.0',
            'timestamp': int(time.time()),
            'file_info': {
                'original_name': file_info.get('original_name'),
                'file_type': file_info.get('file_type'),
                'original_size': file_info.get('original_size'),
                'hash_original': self._calculate_hash(
                    file_info.get('original_data', b'')
                ) if 'original_data' in file_info else None
            },
            'encryption_info': {
                'algorithm': crypto_info.get('algorithm', 'multi-layer'),
                'key_derivation': crypto_info.get('key_derivation', 'PBKDF2'),
                'iterations': crypto_info.get('iterations'),
                'layers': crypto_info.get('layers', [
                    'compression', 'AES-256-GCM', 
                    'ChaCha20-Poly1305', 'RSA-4096'
                ])
            },
            'integrity': {
                'hmac_algorithm': 'SHA-512',
                'has_integrity_check': True
            }
        }
        
        return metadata
    
    def save_metadata(self, file_id: str, metadata: Dict[str, Any]):
        
        metadata_file = self.metadata_dir / f"{file_id}.meta.json"
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def load_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        
        metadata_file = self.metadata_dir / f"{file_id}.meta.json"
        
        if not metadata_file.exists():
            return None
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def delete_metadata(self, file_id: str):
        
        metadata_file = self.metadata_dir / f"{file_id}.meta.json"
        
        if metadata_file.exists():
            metadata_file.unlink()
    
    def _calculate_hash(self, data: bytes) -> str:
        
        return hashlib.sha256(data).hexdigest()
    
    def verify_integrity(self, file_id: str, data: bytes) -> bool:
        
        metadata = self.load_metadata(file_id)
        
        if not metadata:
            return False
        
        stored_hash = metadata.get('file_info', {}).get('hash_original')
        
        if not stored_hash:
            return False
        
        calculated_hash = self._calculate_hash(data)
        
        return stored_hash == calculated_hash
