

import os
import zipfile
from typing import Dict, Any
from .document_processor import DocumentProcessor


class WordProcessor(DocumentProcessor):
    
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.doc', '.docx', '.docm', '.dotx', '.dotm']
    
    def read_document(self, filepath: str) -> bytes:
        
        if not self.validate_document(filepath):
            raise ValueError(f"Невалидный Word документ: {filepath}")
        
        with open(filepath, 'rb') as f:
            return f.read()
    
    def extract_metadata(self, filepath: str) -> Dict[str, Any]:
        
        metadata = {
            'type': 'word',
            'size': os.path.getsize(filepath),
            'filename': os.path.basename(filepath)
        }
        
        extension = os.path.splitext(filepath)[1].lower()
        
        if extension in ['.docx', '.docm', '.dotx', '.dotm']:
            
            try:
                metadata['format'] = 'Office Open XML'
                metadata['is_macro_enabled'] = extension in ['.docm', '.dotm']
                
                
                if zipfile.is_zipfile(filepath):
                    with zipfile.ZipFile(filepath, 'r') as zip_ref:
                        metadata['file_count'] = len(zip_ref.namelist())
                        
                        
                        if 'docProps/core.xml' in zip_ref.namelist():
                            metadata['has_metadata'] = True
            except:
                pass
        else:
            
            metadata['format'] = 'Binary'
        
        return metadata
    
    def validate_document(self, filepath: str) -> bool:
        
        if not super().validate_document(filepath):
            return False
        
        extension = os.path.splitext(filepath)[1].lower()
        
        if extension not in self.supported_extensions:
            return False
        
        
        if extension in ['.docx', '.docm', '.dotx', '.dotm']:
            try:
                return zipfile.is_zipfile(filepath)
            except:
                return False
        
        
        if extension == '.doc':
            try:
                with open(filepath, 'rb') as f:
                    header = f.read(8)
                    
                    return header[:2] == b'\xD0\xCF' or header[:4] == b'\x50\x4B\x03\x04'
            except:
                return False
        
        return True