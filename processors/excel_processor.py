

import os
import zipfile
from typing import Dict, Any
from .document_processor import DocumentProcessor


class ExcelProcessor(DocumentProcessor):
    
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = [
            '.xls', '.xlsx', '.xlsm', '.xlsb', '.xltx', '.xltm'
        ]
    
    def read_document(self, filepath: str) -> bytes:
        
        if not self.validate_document(filepath):
            raise ValueError(f"Невалидный Excel документ: {filepath}")
        
        with open(filepath, 'rb') as f:
            return f.read()
    
    def extract_metadata(self, filepath: str) -> Dict[str, Any]:
        
        metadata = {
            'type': 'excel',
            'size': os.path.getsize(filepath),
            'filename': os.path.basename(filepath)
        }
        
        extension = os.path.splitext(filepath)[1].lower()
        
        if extension in ['.xlsx', '.xlsm', '.xltx', '.xltm']:
            
            try:
                metadata['format'] = 'Office Open XML'
                metadata['is_macro_enabled'] = extension in ['.xlsm', '.xltm']
                metadata['is_binary'] = False
                
                if zipfile.is_zipfile(filepath):
                    with zipfile.ZipFile(filepath, 'r') as zip_ref:
                        filelist = zip_ref.namelist()
                        metadata['file_count'] = len(filelist)
                        
                        
                        sheet_files = [f for f in filelist if f.startswith('xl/worksheets/')]
                        metadata['estimated_sheets'] = len(sheet_files)
                        
                        
                        if 'docProps/core.xml' in filelist:
                            metadata['has_metadata'] = True
            except:
                pass
                
        elif extension == '.xlsb':
            
            metadata['format'] = 'Excel Binary Workbook'
            metadata['is_binary'] = True
            
        else:
            
            metadata['format'] = 'Excel 97-2003'
            metadata['is_binary'] = True
        
        return metadata
    
    def validate_document(self, filepath: str) -> bool:
        
        if not super().validate_document(filepath):
            return False
        
        extension = os.path.splitext(filepath)[1].lower()
        
        if extension not in self.supported_extensions:
            return False
        
        
        if extension in ['.xlsx', '.xlsm', '.xltx', '.xltm']:
            try:
                return zipfile.is_zipfile(filepath)
            except:
                return False
        
        
        if extension in ['.xls', '.xlsb']:
            try:
                with open(filepath, 'rb') as f:
                    header = f.read(8)
                    
                    return (header[:2] == b'\xD0\xCF' or  
                           header[:4] == b'\x09\x08\x10\x00' or  
                           header[:4] == b'\x50\x4B\x03\x04')  
            except:
                return False
        
        return True
