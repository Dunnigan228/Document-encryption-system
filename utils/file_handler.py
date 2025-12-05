

import os
from pathlib import Path
from typing import Optional


class FileHandler:
    
    
    @staticmethod
    def read_file(filepath: str) -> bytes:
        
        with open(filepath, 'rb') as f:
            return f.read()
    
    @staticmethod
    def write_file(filepath: str, data: bytes, overwrite: bool = True):
        
        if not overwrite and os.path.exists(filepath):
            raise FileExistsError(f"Файл уже существует: {filepath}")
        
        
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        
        with open(filepath, 'wb') as f:
            f.write(data)
    
    @staticmethod
    def get_file_size(filepath: str) -> int:
        
        return os.path.getsize(filepath)
    
    @staticmethod
    def file_exists(filepath: str) -> bool:
        
        return os.path.isfile(filepath)
    
    @staticmethod
    def secure_delete(filepath: str, passes: int = 3):
        
        if not os.path.exists(filepath):
            return
        
        file_size = os.path.getsize(filepath)
        
        
        with open(filepath, 'rb+') as f:
            for _ in range(passes):
                f.seek(0)
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())
        
        
        os.remove(filepath)
    
    @staticmethod
    def get_file_extension(filepath: str) -> str:
        
        return os.path.splitext(filepath)[1].lower()
    
    @staticmethod
    def create_backup(filepath: str, backup_dir: Optional[str] = None) -> str:
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Файл не найден: {filepath}")
        
        base_name = os.path.basename(filepath)
        name, ext = os.path.splitext(base_name)
        
        if backup_dir:
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, f"{name}_backup{ext}")
        else:
            backup_path = f"{filepath}.backup"
        
        
        import shutil
        shutil.copy2(filepath, backup_path)
        
        return backup_path