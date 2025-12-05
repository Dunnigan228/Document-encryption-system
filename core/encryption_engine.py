

import os
import struct
import time
from typing import Dict, Any, Optional

from config.constants import CryptoConstants
from config.settings import Settings
from algorithms.aes_handler import AESHandler
from algorithms.chacha_handler import ChaChaHandler
from algorithms.rsa_handler import RSAHandler
from algorithms.hash_functions import HashFunctions
from core.crypto_layers import CryptoLayerManager
from utils.compression import CompressionHandler
from security.salt_generator import SaltGenerator
from security.iv_generator import IVGenerator
from security.password_derivation import PasswordDerivation
from security.integrity_checker import IntegrityChecker


class EncryptionEngine:
    
    
    def __init__(self, password: str, key_manager):
        
        self.password = password
        self.key_manager = key_manager
        self.settings = Settings()
        self.constants = CryptoConstants()
        
        
        self.salt_generator = SaltGenerator()
        self.iv_generator = IVGenerator()
        self.hash_functions = HashFunctions()
        self.password_derivation = PasswordDerivation()
        self.integrity_checker = IntegrityChecker()
        
        
        self.compression_handler = CompressionHandler()
        self.crypto_layer_manager = CryptoLayerManager()
        
        
        self._initialize_crypto_parameters()
    
    def _initialize_crypto_parameters(self):
        
        
        self.salt = self.salt_generator.generate_salt(self.settings.SALT_SIZE)
        self.aes_iv = self.iv_generator.generate_iv(self.settings.IV_SIZE)
        self.chacha_nonce = self.iv_generator.generate_nonce(self.settings.NONCE_SIZE)
        
        
        self.master_key = self.password_derivation.derive_key(
            password=self.password,
            salt=self.salt,
            key_length=self.settings.DEFAULT_KEY_SIZE // 8,
            iterations=self.settings.PBKDF2_ITERATIONS
        )
        
        
        self.aes_key = self.password_derivation.derive_subkey(
            master_key=self.master_key,
            context=b'AES-256-GCM-KEY',
            key_length=32  
        )
        
        self.chacha_key = self.password_derivation.derive_subkey(
            master_key=self.master_key,
            context=b'CHACHA20-KEY',
            key_length=32  
        )
        
        self.hmac_key = self.password_derivation.derive_subkey(
            master_key=self.master_key,
            context=b'HMAC-SHA512-KEY',
            key_length=64  
        )
        
        
        self.rsa_public_key, self.rsa_private_key = self.key_manager.generate_rsa_keypair(
            key_size=self.settings.RSA_KEY_SIZE
        )
        
        
        self.aes_handler = AESHandler(self.aes_key)
        self.chacha_handler = ChaChaHandler(self.chacha_key)
        self.rsa_handler = RSAHandler(self.rsa_public_key, self.rsa_private_key)
    
    def encrypt(self, data: bytes, file_type: str, original_filename: str) -> bytes:
        
        
        original_size = len(data)
        compressed_data = data
        compressed = False
        
        if self.settings.COMPRESSION_ENABLED:
            compressed_data = self.compression_handler.compress(
                data, 
                level=self.settings.COMPRESSION_LEVEL
            )
            compressed = len(compressed_data) < len(data)
            
            if not compressed:
                compressed_data = data
        
        compressed_size = len(compressed_data)
        
        
        aes_encrypted, aes_tag = self.aes_handler.encrypt(
            data=compressed_data,
            iv=self.aes_iv,
            associated_data=original_filename.encode()
        )
        
        
        chacha_encrypted = self.chacha_handler.encrypt(
            data=aes_encrypted,
            nonce=self.chacha_nonce
        )
        
        
        final_encrypted = self.crypto_layer_manager.apply_custom_transformations(
            data=chacha_encrypted,
            key=self.master_key
        )
        
        
        keys_bundle = self._create_keys_bundle()
        encrypted_keys = self.rsa_handler.encrypt(keys_bundle)
        
        
        hmac_data = self._prepare_hmac_data(
            encrypted_data=final_encrypted,
            metadata={
                'file_type': file_type,
                'filename': original_filename,
                'original_size': original_size,
                'compressed_size': compressed_size
            }
        )
        
        hmac_signature = self.integrity_checker.create_hmac(
            data=hmac_data,
            key=self.hmac_key
        )
        
        
        encrypted_file = self._build_encrypted_file(
            encrypted_data=final_encrypted,
            encrypted_keys=encrypted_keys,
            hmac_signature=hmac_signature,
            aes_tag=aes_tag,
            metadata={
                'file_type': file_type,
                'filename': original_filename,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compressed': compressed
            }
        )
        
        return encrypted_file
    
    def _create_keys_bundle(self) -> bytes:
        
        keys_bundle = b''
        keys_bundle += struct.pack('<H', len(self.aes_key)) + self.aes_key
        keys_bundle += struct.pack('<H', len(self.chacha_key)) + self.chacha_key
        keys_bundle += struct.pack('<H', len(self.hmac_key)) + self.hmac_key
        keys_bundle += struct.pack('<H', len(self.aes_iv)) + self.aes_iv
        keys_bundle += struct.pack('<H', len(self.chacha_nonce)) + self.chacha_nonce
        
        return keys_bundle
    
    def _prepare_hmac_data(self, encrypted_data: bytes, metadata: dict) -> bytes:
        
        hmac_data = encrypted_data
        hmac_data += metadata['file_type'].encode()
        hmac_data += metadata['filename'].encode()
        hmac_data += struct.pack('<Q', metadata['original_size'])
        hmac_data += struct.pack('<Q', metadata['compressed_size'])
        
        return hmac_data
    
    def _build_encrypted_file(self,
                             encrypted_data: bytes,
                             encrypted_keys: bytes,
                             hmac_signature: bytes,
                             aes_tag: bytes,
                             metadata: dict) -> bytes:
        
        result = bytearray()
        
        
        result.extend(self.constants.MAGIC_NUMBER)  
        result.extend(self.constants.VERSION_BYTES)  
        
        
        flags = self.constants.create_flags(
            compressed=metadata['compressed'],
            multi_layer=True,
            rsa_protected=True,
            integrity_check=True,
            metadata_encrypted=False
        )
        result.extend(struct.pack('<I', flags))
        
        
        result.extend(struct.pack('<Q', int(time.time())))
        
        result.extend(self.constants.HEADER_SEPARATOR)
        
        
        file_type_bytes = metadata['file_type'].encode('utf-8')
        result.extend(struct.pack('<H', len(file_type_bytes)))
        result.extend(file_type_bytes)
        
        filename_bytes = metadata['filename'].encode('utf-8')
        result.extend(struct.pack('<H', len(filename_bytes)))
        result.extend(filename_bytes)
        
        result.extend(struct.pack('<Q', metadata['original_size']))
        result.extend(struct.pack('<Q', metadata['compressed_size']))
        
        result.extend(self.constants.SECTION_SEPARATOR)
        
        
        result.extend(struct.pack('<H', len(self.salt)))
        result.extend(self.salt)
        
        result.extend(struct.pack('<H', len(aes_tag)))
        result.extend(aes_tag)
        
        result.extend(struct.pack('<H', len(encrypted_keys)))
        result.extend(encrypted_keys)
        
        result.extend(self.constants.SECTION_SEPARATOR)
        
        
        result.extend(struct.pack('<Q', len(encrypted_data)))
        result.extend(encrypted_data)
        
        result.extend(self.constants.SECTION_SEPARATOR)
        
        
        result.extend(hmac_signature)
        
        return bytes(result)
    
    def get_key_bundle(self) -> dict:
        
        return {
            'master_key': self.master_key,
            'aes_key': self.aes_key,
            'chacha_key': self.chacha_key,
            'hmac_key': self.hmac_key,
            'salt': self.salt,
            'aes_iv': self.aes_iv,
            'chacha_nonce': self.chacha_nonce,
            'rsa_private_key': self.key_manager.serialize_private_key(self.rsa_private_key),
            'rsa_public_key': self.key_manager.serialize_public_key(self.rsa_public_key),
            'version': self.settings.ENCRYPTION_VERSION
        }