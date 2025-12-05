

from pathlib import Path
from typing import Dict, Any, Optional
import json


class SecureVault:
    
    
    def __init__(self, vault_dir: Optional[Path] = None):
        
        self.vault_dir = vault_dir or Path('vault')
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.vault_dir / 'vault_index.json'
        self.index = self._load_index()
    
    def _load_index(self) -> Dict:
        
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_index(self):
        
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def store(self, item_id: str, data: Any, metadata: Optional[Dict] = None):
        
        item_file = self.vault_dir / f"{item_id}.vault"
        
        vault_data = {
            'data': data,
            'metadata': metadata or {}
        }
        
        with open(item_file, 'w') as f:
            json.dump(vault_data, f, indent=2)
        
        
        self.index[item_id] = {
            'file': str(item_file),
            'metadata': metadata or {}
        }
        self._save_index()
    
    def retrieve(self, item_id: str) -> Optional[Any]:
        
        if item_id not in self.index:
            return None
        
        item_file = Path(self.index[item_id]['file'])
        
        if not item_file.exists():
            return None
        
        with open(item_file, 'r') as f:
            vault_data = json.load(f)
        
        return vault_data['data']
    
    def delete(self, item_id: str):
        
        if item_id not in self.index:
            return
        
        item_file = Path(self.index[item_id]['file'])
        
        if item_file.exists():
            item_file.unlink()
        
        del self.index[item_id]
        self._save_index()
    
    def list_items(self) -> list:
        
        return list(self.index.keys())
