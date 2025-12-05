




class CryptoConstants:
    
    
    
    MAGIC_NUMBER = b'DOCENC'  
    VERSION_BYTES = b'\x01\x00'  
    
    
    HEADER_SEPARATOR = b'\xFF\xFE\xFD\xFC'
    SECTION_SEPARATOR = b'\xFB\xFA\xF9\xF8'
    
    
    AES_BLOCK_SIZE = 16  
    CHACHA_BLOCK_SIZE = 64  
    RSA_PADDING_SIZE = 66  
    
    
    AES_MODE = 'GCM'  
    CHACHA_MODE = 'POLY1305'  
    RSA_PADDING = 'OAEP'  
    
    
    HMAC_ALGORITHM = 'sha512'
    HMAC_SIZE = 64  
    
    
    KDF_ALGORITHM = 'pbkdf2_hmac'
    KDF_HASH = 'sha512'
    KDF_ITERATIONS = 600000
    
    
    ARGON2_TIME_COST = 4
    ARGON2_MEMORY_COST = 65536  
    ARGON2_PARALLELISM = 4
    
    
    ENCRYPTION_LAYERS = [
        'compression',    
        'padding',        
        'aes_gcm',        
        'chacha20',       
        'rsa_oaep',       
        'hmac_integrity'  
    ]
    
    
    CUSTOM_PERMUTATION_ROUNDS = 16  
    CUSTOM_SUBSTITUTION_TABLES = 8  
    
    
    KEY_TYPES = {
        'MASTER': 'master_key',
        'AES': 'aes_key',
        'CHACHA': 'chacha_key',
        'RSA_PUBLIC': 'rsa_public',
        'RSA_PRIVATE': 'rsa_private',
        'HMAC': 'hmac_key',
        'SALT': 'salt',
        'IV': 'initialization_vector',
        'NONCE': 'nonce'
    }
    
    
    ERROR_CODES = {
        'INVALID_PASSWORD': 1001,
        'CORRUPTED_DATA': 1002,
        'INTEGRITY_CHECK_FAILED': 1003,
        'UNSUPPORTED_VERSION': 1004,
        'INVALID_KEY': 1005,
        'DECRYPTION_FAILED': 1006,
        'FILE_TOO_LARGE': 1007,
        'INVALID_FORMAT': 1008
    }
    
    
    FILE_STRUCTURE = {
        'HEADER': {
            'magic': 6,      
            'version': 2,    
            'flags': 4,      
            'timestamp': 8,  
        },
        'METADATA': {
            'file_type_len': 2,      
            'file_type': 'variable',  
            'filename_len': 2,        
            'filename': 'variable',   
            'original_size': 8,       
            'compressed_size': 8,     
        },
        'CRYPTO_INFO': {
            'salt': 32,              
            'iv': 16,                
            'nonce': 12,             
            'rsa_encrypted_keys': 512,  
        },
        'DATA': {
            'encrypted_data': 'variable',  
            'hmac': 64,                    
        }
    }
    
    
    FLAGS = {
        'COMPRESSED': 0b00000001,
        'MULTI_LAYER': 0b00000010,
        'RSA_PROTECTED': 0b00000100,
        'INTEGRITY_CHECK': 0b00001000,
        'METADATA_ENCRYPTED': 0b00010000,
    }
    
    @classmethod
    def get_header_size(cls) -> int:
        
        return sum(cls.FILE_STRUCTURE['HEADER'].values())
    
    @classmethod
    def get_crypto_info_size(cls) -> int:
        
        return sum(cls.FILE_STRUCTURE['CRYPTO_INFO'].values())
    
    @classmethod
    def create_flags(cls, compressed=True, multi_layer=True, 
                    rsa_protected=True, integrity_check=True,
                    metadata_encrypted=True) -> int:
        
        flags = 0
        if compressed:
            flags |= cls.FLAGS['COMPRESSED']
        if multi_layer:
            flags |= cls.FLAGS['MULTI_LAYER']
        if rsa_protected:
            flags |= cls.FLAGS['RSA_PROTECTED']
        if integrity_check:
            flags |= cls.FLAGS['INTEGRITY_CHECK']
        if metadata_encrypted:
            flags |= cls.FLAGS['METADATA_ENCRYPTED']
        return flags
    
    @classmethod
    def parse_flags(cls, flags: int) -> dict:
        
        return {
            'compressed': bool(flags & cls.FLAGS['COMPRESSED']),
            'multi_layer': bool(flags & cls.FLAGS['MULTI_LAYER']),
            'rsa_protected': bool(flags & cls.FLAGS['RSA_PROTECTED']),
            'integrity_check': bool(flags & cls.FLAGS['INTEGRITY_CHECK']),
            'metadata_encrypted': bool(flags & cls.FLAGS['METADATA_ENCRYPTED']),
        }




__all__ = ['CryptoConstants']