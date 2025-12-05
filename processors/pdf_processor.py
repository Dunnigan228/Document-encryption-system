

import os
from typing import Dict, Any
from .document_processor import DocumentProcessor


class PDFProcessor(DocumentProcessor):
    
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.pdf']
    
    def read_document(self, filepath: str) -> bytes:
        
        if not self.validate_document(filepath):
            raise ValueError(f"Невалидный PDF документ: {filepath}")
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        
        if not data.startswith(b'%PDF-'):
            raise ValueError("Файл не является PDF документом")
        
        return data
    
    def extract_metadata(self, filepath: str) -> Dict[str, Any]:
        
        metadata = {
            'type': 'pdf',
            'size': os.path.getsize(filepath),
            'filename': os.path.basename(filepath)
        }
        
        try:
            
            with open(filepath, 'rb') as f:
                header = f.read(10)
                if header.startswith(b'%PDF-'):
                    version = header[5:8].decode('ascii', errors='ignore')
                    metadata['pdf_version'] = version
        except:
            pass
        
        return metadata
    
    def validate_document(self, filepath: str) -> bool:
        
        if not super().validate_document(filepath):
            return False
        
        
        if not filepath.lower().endswith('.pdf'):
            return False
        
        
        try:
            with open(filepath, 'rb') as f:
                header = f.read(5)
                return header == b'%PDF-'
        except:
            return False