

import hashlib
from typing import List


class CryptoLayerManager:
    
    
    def __init__(self):
        self.permutation_rounds = 16
        self.sbox_count = 8
    
    def apply_custom_transformations(self, data: bytes, key: bytes) -> bytes:
        
        result = bytearray(data)
        
        
        sboxes = self._generate_sboxes(key)
        permutation_key = self._generate_permutation_key(key, len(data))
        
        
        for round_num in range(self.permutation_rounds):
            
            result = self._apply_substitution(result, sboxes, round_num)
            
            
            result = self._apply_permutation(result, permutation_key, round_num)
            
            
            round_key = self._derive_round_key(key, round_num, len(result))
            result = self._xor_with_key(result, round_key)
        
        return bytes(result)
    
    def remove_custom_transformations(self, data: bytes, key: bytes) -> bytes:
        
        result = bytearray(data)
        
        
        sboxes = self._generate_sboxes(key)
        inv_sboxes = self._generate_inverse_sboxes(sboxes)
        permutation_key = self._generate_permutation_key(key, len(data))
        
        
        for round_num in range(self.permutation_rounds - 1, -1, -1):
            
            round_key = self._derive_round_key(key, round_num, len(result))
            result = self._xor_with_key(result, round_key)
            
            
            result = self._apply_inverse_permutation(result, permutation_key, round_num)
            
            
            result = self._apply_substitution(result, inv_sboxes, round_num)
        
        return bytes(result)
    
    def _generate_sboxes(self, key: bytes) -> List[List[int]]:
        
        sboxes = []
        
        for i in range(self.sbox_count):
            
            seed = hashlib.sha256(key + i.to_bytes(4, 'big')).digest()
            
            
            sbox = list(range(256))
            
            
            for j in range(255, 0, -1):
                
                rand_byte = seed[j % len(seed)]
                k = rand_byte % (j + 1)
                sbox[j], sbox[k] = sbox[k], sbox[j]
            
            sboxes.append(sbox)
        
        return sboxes
    
    def _generate_inverse_sboxes(self, sboxes: List[List[int]]) -> List[List[int]]:
        
        inv_sboxes = []
        
        for sbox in sboxes:
            inv_sbox = [0] * 256
            for i, val in enumerate(sbox):
                inv_sbox[val] = i
            inv_sboxes.append(inv_sbox)
        
        return inv_sboxes
    
    def _apply_substitution(self, data: bytearray, sboxes: List[List[int]], 
                           round_num: int) -> bytearray:
        
        result = bytearray(len(data))
        
        for i, byte in enumerate(data):
            sbox_index = (i + round_num) % len(sboxes)
            result[i] = sboxes[sbox_index][byte]
        
        return result
    
    def _generate_permutation_key(self, key: bytes, length: int) -> List[int]:
        
        
        hash_val = hashlib.sha512(key + b'PERMUTATION').digest()
        
        indices = list(range(length))
        
        
        for i in range(length - 1, 0, -1):
            j = int.from_bytes(
                hashlib.sha256(hash_val + i.to_bytes(8, 'big')).digest()[:4],
                'big'
            ) % (i + 1)
            indices[i], indices[j] = indices[j], indices[i]
        
        return indices
    
    def _apply_permutation(self, data: bytearray, perm_key: List[int], 
                          round_num: int) -> bytearray:
        
        if len(data) != len(perm_key):
            return data
        
        result = bytearray(len(data))
        
        for i, pos in enumerate(perm_key):
            result[pos] = data[i]
        
        return result
    
    def _apply_inverse_permutation(self, data: bytearray, perm_key: List[int], 
                                   round_num: int) -> bytearray:
        
        if len(data) != len(perm_key):
            return data
        
        result = bytearray(len(data))
        
        for i, pos in enumerate(perm_key):
            result[i] = data[pos]
        
        return result
    
    def _derive_round_key(self, master_key: bytes, round_num: int, 
                         length: int) -> bytes:
        
        round_data = master_key + round_num.to_bytes(4, 'big')
        key_material = hashlib.sha512(round_data).digest()
        
        
        result = b''
        counter = 0
        while len(result) < length:
            result += hashlib.sha512(
                key_material + counter.to_bytes(4, 'big')
            ).digest()
            counter += 1
        
        return result[:length]
    
    def _xor_with_key(self, data: bytearray, key: bytes) -> bytearray:
        
        result = bytearray(len(data))
        
        for i, byte in enumerate(data):
            result[i] = byte ^ key[i % len(key)]
        
        return result