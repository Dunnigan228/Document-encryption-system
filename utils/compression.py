

import zlib
import lzma
from typing import Optional


class CompressionHandler:
    
    
    @staticmethod
    def compress(data: bytes, level: int = 9, method: str = 'lzma') -> bytes:
        
        if method == 'zlib':
            return zlib.compress(data, level=level)
        elif method == 'lzma':
            return lzma.compress(
                data,
                format=lzma.FORMAT_XZ,
                preset=level
            )
        else:
            raise ValueError(f"Неподдерживаемый метод сжатия: {method}")
    
    @staticmethod
    def decompress(data: bytes, method: str = 'lzma') -> bytes:
        
        try:
            if method == 'lzma':
                return lzma.decompress(data)
            elif method == 'zlib':
                return zlib.decompress(data)
            else:
                raise ValueError(f"Неподдерживаемый метод сжатия: {method}")
        except Exception as e:
            raise ValueError(f"Ошибка декомпрессии: {str(e)}")
    
    @staticmethod
    def get_compression_ratio(original_size: int, compressed_size: int) -> float:
        
        if compressed_size == 0:
            return 0.0
        
        return original_size / compressed_size
    
    @staticmethod
    def should_compress(data: bytes, threshold: float = 0.9) -> bool:
        
        
        sample_size = min(len(data), 10000)
        sample = data[:sample_size]
        
        compressed_sample = zlib.compress(sample, level=1)
        
        ratio = len(compressed_sample) / len(sample)
        
        
        return ratio < threshold