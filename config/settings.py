import os
from pathlib import Path


class Settings:
    
    
    
    BASE_DIR = Path(__file__).resolve().parent.parent
    ENCRYPTED_DIR = BASE_DIR / 'encrypted_files'
    DECRYPTED_DIR = BASE_DIR / 'decrypted_files'
    KEYS_DIR = BASE_DIR / 'keys'
    LOGS_DIR = BASE_DIR / 'logs'
    
    
    ENCRYPTION_VERSION = '1.0.0'
    DEFAULT_KEY_SIZE = 256  
    RSA_KEY_SIZE = 4096  
    CHACHA_KEY_SIZE = 256  
    
    
    HASH_ALGORITHM = 'sha512'
    PBKDF2_ITERATIONS = 600000  
    SALT_SIZE = 32  
    IV_SIZE = 16  
    NONCE_SIZE = 12  
    
    
    COMPRESSION_ENABLED = True
    COMPRESSION_LEVEL = 9  
    
    
    SUPPORTED_FORMATS = {
        'pdf': ['.pdf'],
        'word': ['.doc', '.docx', '.docm', '.dotx', '.dotm'],
        'excel': ['.xls', '.xlsx', '.xlsm', '.xlsb', '.xltx', '.xltm'],
        'text': ['.txt', '.md', '.csv', '.json', '.xml']
    }
    
    
    MAX_FILE_SIZE = 500 * 1024 * 1024  
    MIN_PASSWORD_LENGTH = 12
    MAX_PASSWORD_LENGTH = 256
    
    
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    
    METADATA_VERSION = '1.0'
    INCLUDE_TIMESTAMP = True
    INCLUDE_FILE_HASH = True
    
    
    SECURE_DELETE_PASSES = 3  
    MEMORY_WIPE_ENABLED = True  
    
    def __init__(self):
        
        
        for directory in [self.LOGS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_supported_extensions(cls) -> list:
        
        extensions = []
        for format_list in cls.SUPPORTED_FORMATS.values():
            extensions.extend(format_list)
        return extensions
    
    @classmethod
    def get_format_by_extension(cls, extension: str) -> str:
        
        extension = extension.lower()
        if not extension.startswith('.'):
            extension = '.' + extension
        
        for format_name, extensions in cls.SUPPORTED_FORMATS.items():
            if extension in extensions:
                return format_name
        
        return 'unknown'


