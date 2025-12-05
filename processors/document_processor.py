

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class DocumentProcessor(ABC):
    
    
    def __init__(self):
        self.metadata = {}
    
    @abstractmethod
    def read_document(self, filepath: str) -> bytes:
        
        pass
    
    @abstractmethod
    def extract_metadata(self, filepath: str) -> Dict[str, Any]:
        
        pass
    
    def preprocess(self, data: bytes) -> bytes:
        
        
        return data
    
    def postprocess(self, data: bytes) -> bytes:
        
        
        return data
    
    def validate_document(self, filepath: str) -> bool:
        
        import os
        return os.path.isfile(filepath) and os.path.getsize(filepath) > 0