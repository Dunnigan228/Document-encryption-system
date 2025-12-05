

import os
import re
from typing import Optional
from config.settings import Settings


class Validator:
    
    
    def __init__(self):
        self.settings = Settings()
    
    def validate_file(self, filepath: str) -> bool:
        
        if not os.path.exists(filepath):
            return False
        
        if not os.path.isfile(filepath):
            return False
        
        if not os.access(filepath, os.R_OK):
            return False
        
        
        file_size = os.path.getsize(filepath)
        if file_size > self.settings.MAX_FILE_SIZE:
            raise ValueError(
                f"Файл слишком большой: {file_size} байт. "
                f"Максимум: {self.settings.MAX_FILE_SIZE} байт"
            )
        
        if file_size == 0:
            raise ValueError("Файл пустой")
        
        return True
    
    def get_file_type(self, filepath: str) -> str:
        
        extension = os.path.splitext(filepath)[1].lower()
        return self.settings.get_format_by_extension(extension)
    
    def is_supported_format(self, file_type: str) -> bool:
        
        return file_type in self.settings.SUPPORTED_FORMATS
    
    def validate_password(self, password: str) -> bool:
        
        if len(password) < self.settings.MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Пароль слишком короткий. Минимум: "
                f"{self.settings.MIN_PASSWORD_LENGTH} символов"
            )
        
        if len(password) > self.settings.MAX_PASSWORD_LENGTH:
            raise ValueError(
                f"Пароль слишком длинный. Максимум: "
                f"{self.settings.MAX_PASSWORD_LENGTH} символов"
            )
        
        
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password))
        
        strength_score = sum([has_upper, has_lower, has_digit, has_special])
        
        if strength_score < 3:
            raise ValueError(
                "Пароль недостаточно сложный. Используйте комбинацию: "
                "заглавные буквы, строчные буквы, цифры и специальные символы"
            )
        
        return True
    
    def validate_key_file(self, filepath: str) -> bool:
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Файл ключа не найден: {filepath}")
        
        if not filepath.endswith('.key'):
            raise ValueError("Файл должен иметь расширение .key")
        
        return True
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        
        
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        
        sanitized = sanitized.strip('. ')
        
        
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:255-len(ext)] + ext
        
        return sanitized
