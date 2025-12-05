

import struct
from typing import Dict, Any, Tuple

from config.constants import CryptoConstants
from config.settings import Settings
from algorithms.aes_handler import AESHandler
from algorithms.chacha_handler import ChaChaHandler
from algorithms.rsa_handler import RSAHandler
from core.crypto_layers import CryptoLayerManager
from utils.compression import CompressionHandler
from security.integrity_checker import IntegrityChecker


class DecryptionEngine:
    
    
    def __init__(self, key_bundle: dict, key_manager):
        
        self.key_bundle = key_bundle
        self.key_manager = key_manager
        self.settings = Settings()
        self.constants = CryptoConstants()
        
        
        self.master_key = key_bundle['master_key']
        self.aes_key = key_bundle['aes_key']
        self.chacha_key = key_bundle['chacha_key']
        self.hmac_key = key_bundle['hmac_key']
        self.salt = key_bundle['salt']
        self.aes_iv = key_bundle['aes_iv']
        self.chacha_nonce = key_bundle['chacha_nonce']
        
        
        self.rsa_private_key = self.key_manager.deserialize_private_key(
            key_bundle['rsa_private_key']
        )
        self.rsa_public_key = self.key_manager.deserialize_public_key(
            key_bundle['rsa_public_key']
        )
        
        
        self.aes_handler = AESHandler(self.aes_key)
        self.chacha_handler = ChaChaHandler(self.chacha_key)
        self.rsa_handler = RSAHandler(self.rsa_public_key, self.rsa_private_key)
        self.crypto_layer_manager = CryptoLayerManager()
        self.compression_handler = CompressionHandler()
        self.integrity_checker = IntegrityChecker()
    
    def decrypt(self, encrypted_file: bytes) -> Dict[str, Any]:
        
        
        parsed = self._parse_encrypted_file(encrypted_file)
        
        
        if parsed['version'] != self.key_bundle.get('version'):
            raise ValueError(
                f"Несовместимая версия: файл {parsed['version']}, "
                f"ключ {self.key_bundle.get('version')}"
            )
        
        
        self._verify_integrity(parsed)
        
        
        decrypted_keys = self.rsa_handler.decrypt(parsed['encrypted_keys'])
        self._verify_keys(decrypted_keys)
        
        
        after_custom = self.crypto_layer_manager.remove_custom_transformations(
            data=parsed['encrypted_data'],
            key=self.master_key
        )
        
        
        after_chacha = self.chacha_handler.decrypt(
            data=after_custom,
            nonce=self.chacha_nonce
        )
        
        
        decrypted_data = self.aes_handler.decrypt(
            data=after_chacha,
            iv=self.aes_iv,
            tag=parsed['aes_tag'],
            associated_data=parsed['metadata']['filename'].encode()
        )
        
        
        final_data = decrypted_data
        if parsed['flags']['compressed']:
            final_data = self.compression_handler.decompress(decrypted_data)
        
        
        if len(final_data) != parsed['metadata']['original_size']:
            raise ValueError(
                f"Несоответствие размера: ожидалось "
                f"{parsed['metadata']['original_size']}, "
                f"получено {len(final_data)}"
            )
        
        return {
            'data': final_data,
            'file_type': parsed['metadata']['file_type'],
            'original_filename': parsed['metadata']['filename'],
            'timestamp': parsed['timestamp'],
            'original_size': parsed['metadata']['original_size']
        }
    
    def _parse_encrypted_file(self, encrypted_file: bytes) -> Dict[str, Any]:
        
        offset = 0
        
        
        magic = encrypted_file[offset:offset + 6]
        if magic != self.constants.MAGIC_NUMBER:
            raise ValueError("Неверный формат файла: магическое число не совпадает")
        offset += 6
        
        
        version_bytes = encrypted_file[offset:offset + 2]
        version = f"{version_bytes[0]}.{version_bytes[1]}.0"  
        offset += 2
        
        
        flags_int = struct.unpack('<I', encrypted_file[offset:offset + 4])[0]
        flags = self.constants.parse_flags(flags_int)
        offset += 4
        
        
        timestamp = struct.unpack('<Q', encrypted_file[offset:offset + 8])[0]
        offset += 8
        
        
        offset += len(self.constants.HEADER_SEPARATOR)
        
        
        file_type_len = struct.unpack('<H', encrypted_file[offset:offset + 2])[0]
        offset += 2
        file_type = encrypted_file[offset:offset + file_type_len].decode('utf-8')
        offset += file_type_len
        
        filename_len = struct.unpack('<H', encrypted_file[offset:offset + 2])[0]
        offset += 2
        filename = encrypted_file[offset:offset + filename_len].decode('utf-8')
        offset += filename_len
        
        original_size = struct.unpack('<Q', encrypted_file[offset:offset + 8])[0]
        offset += 8
        compressed_size = struct.unpack('<Q', encrypted_file[offset:offset + 8])[0]
        offset += 8
        
        
        offset += len(self.constants.SECTION_SEPARATOR)
        
        
        salt_len = struct.unpack('<H', encrypted_file[offset:offset + 2])[0]
        offset += 2
        salt = encrypted_file[offset:offset + salt_len]
        offset += salt_len
        
        aes_tag_len = struct.unpack('<H', encrypted_file[offset:offset + 2])[0]
        offset += 2
        aes_tag = encrypted_file[offset:offset + aes_tag_len]
        offset += aes_tag_len
        
        encrypted_keys_len = struct.unpack('<H', encrypted_file[offset:offset + 2])[0]
        offset += 2
        encrypted_keys = encrypted_file[offset:offset + encrypted_keys_len]
        offset += encrypted_keys_len
        
        
        offset += len(self.constants.SECTION_SEPARATOR)
        
        
        encrypted_data_len = struct.unpack('<Q', encrypted_file[offset:offset + 8])[0]
        offset += 8
        encrypted_data = encrypted_file[offset:offset + encrypted_data_len]
        offset += encrypted_data_len
        
        
        offset += len(self.constants.SECTION_SEPARATOR)
        
        
        hmac_signature = encrypted_file[offset:offset + self.constants.HMAC_SIZE]
        
        return {
            'version': version,
            'flags': flags,
            'timestamp': timestamp,
            'metadata': {
                'file_type': file_type,
                'filename': filename,
                'original_size': original_size,
                'compressed_size': compressed_size
            },
            'salt': salt,
            'aes_tag': aes_tag,
            'encrypted_keys': encrypted_keys,
            'encrypted_data': encrypted_data,
            'hmac_signature': hmac_signature
        }
    
    def _verify_integrity(self, parsed: Dict[str, Any]):
        
        
        hmac_data = parsed['encrypted_data']
        hmac_data += parsed['metadata']['file_type'].encode()
        hmac_data += parsed['metadata']['filename'].encode()
        hmac_data += struct.pack('<Q', parsed['metadata']['original_size'])
        hmac_data += struct.pack('<Q', parsed['metadata']['compressed_size'])
        
        
        calculated_hmac = self.integrity_checker.create_hmac(
            data=hmac_data,
            key=self.hmac_key
        )
        
        
        if not self.integrity_checker.verify_hmac(
            data=hmac_data,
            hmac_signature=parsed['hmac_signature'],
            key=self.hmac_key
        ):
            raise ValueError(
                "Проверка целостности не пройдена: файл поврежден или изменен"
            )
    
    def _verify_keys(self, decrypted_keys: bytes):
        
        offset = 0
        
        
        aes_key_len = struct.unpack('<H', decrypted_keys[offset:offset + 2])[0]
        offset += 2
        aes_key = decrypted_keys[offset:offset + aes_key_len]
        offset += aes_key_len
        
        if aes_key != self.aes_key:
            raise ValueError("AES ключ не совпадает")
        
        
        chacha_key_len = struct.unpack('<H', decrypted_keys[offset:offset + 2])[0]
        offset += 2
        chacha_key = decrypted_keys[offset:offset + chacha_key_len]
        offset += chacha_key_len
        
        if chacha_key != self.chacha_key:
            raise ValueError("ChaCha ключ не совпадает")
        
        
        hmac_key_len = struct.unpack('<H', decrypted_keys[offset:offset + 2])[0]
        offset += 2
        hmac_key = decrypted_keys[offset:offset + hmac_key_len]
        offset += hmac_key_len
        
        if hmac_key != self.hmac_key:
            raise ValueError("HMAC ключ не совпадает")


class DecryptionError(Exception):
    
    
    def __init__(self, message: str, error_code: int = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)