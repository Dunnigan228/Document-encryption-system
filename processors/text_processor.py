

import os
from typing import Dict, Any
from .document_processor import DocumentProcessor


class TextProcessor(DocumentProcessor):
    
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.txt', '.md', '.csv', '.json', '.xml']
    
    def read_document(self, filepath: str) -> bytes:
        
        if not self.validate_document(filepath):
            raise ValueError(f"Невалидный текстовый документ: {filepath}")
        
        with open(filepath, 'rb') as f:
            return f.read()
    
    def extract_metadata(self, filepath: str) -> Dict[str, Any]:
        
        metadata = {
            'type': 'text',
            'size': os.path.getsize(filepath),
            'filename': os.path.basename(filepath)
        }
        
        extension = os.path.splitext(filepath)[1].lower()
        
        
        if extension == '.txt':
            metadata['content_type'] = 'plain text'
        elif extension == '.md':
            metadata['content_type'] = 'markdown'
        elif extension == '.csv':
            metadata['content_type'] = 'comma-separated values'
        elif extension == '.json':
            metadata['content_type'] = 'json'
        elif extension == '.xml':
            metadata['content_type'] = 'xml'
        
        
        try:
            with open(filepath, 'rb') as f:
                sample = f.read(1024)
                
                
                if sample.startswith(b'\xef\xbb\xbf'):
                    metadata['encoding'] = 'UTF-8 with BOM'
                elif sample.startswith(b'\xff\xfe'):
                    metadata['encoding'] = 'UTF-16 LE'
                elif sample.startswith(b'\xfe\xff'):
                    metadata['encoding'] = 'UTF-16 BE'
                else:
                    
                    try:
                        sample.decode('utf-8')
                        metadata['encoding'] = 'UTF-8'
                    except:
                        metadata['encoding'] = 'unknown'
        except:
            pass
        
        return metadata
    
    def validate_document(self, filepath: str) -> bool:
        
        if not super().validate_document(filepath):
            return False
        
        extension = os.path.splitext(filepath)[1].lower()
        return extension in self.supported_extensions