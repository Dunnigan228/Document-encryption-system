import hashlib
class CustomCipher:  
    def __init__(self, key: bytes, rounds: int = 32):
        self.key = key
        self.rounds = rounds
        self.block_size = 16  
        
        
        self.round_keys = self._generate_round_keys()
        
        
        self.sbox = self._generate_sbox()
        self.inv_sbox = self._generate_inverse_sbox()
    
    def _generate_round_keys(self):
        round_keys = []
        
        for i in range(self.rounds):
            round_key = hashlib.sha256(
                self.key + i.to_bytes(4, 'big')
            ).digest()[:self.block_size]
            round_keys.append(round_key)
        
        return round_keys
    
    def _generate_sbox(self):
        seed = hashlib.sha256(self.key + b'SBOX').digest()
        
        sbox = list(range(256))
        for i in range(255, 0, -1):
            j = seed[i % len(seed)] % (i + 1)
            sbox[i], sbox[j] = sbox[j], sbox[i]
        
        return sbox
    
    def _generate_inverse_sbox(self):
        inv_sbox = [0] * 256
        for i, val in enumerate(self.sbox):
            inv_sbox[val] = i
        return inv_sbox
    
    def encrypt_block(self, block: bytes) -> bytes:
        if len(block) != self.block_size:
            raise ValueError(f"Размер блока должен быть {self.block_size} байт")
        
        state = bytearray(block)
        
        for round_num in range(self.rounds):
            left = state[:8]
            right = state[8:]
            
            f_output = self._round_function(right, self.round_keys[round_num])
            new_left = bytes(a ^ b for a, b in zip(left, f_output))
            if round_num < self.rounds - 1:
                state = bytearray(right + new_left)
            else:
                state = bytearray(new_left + right)
        
        return bytes(state)
    
    def decrypt_block(self, block: bytes) -> bytes:
        if len(block) != self.block_size:
            raise ValueError(f"Размер блока должен быть {self.block_size} байт")
        
        state = bytearray(block)

        for round_num in range(self.rounds - 1, -1, -1):
            if round_num < self.rounds - 1:
                left = state[8:]
                right = state[:8]
            else:
                left = state[:8]
                right = state[8:]
            
            f_output = self._round_function(right, self.round_keys[round_num])
            
            new_left = bytes(a ^ b for a, b in zip(left, f_output))
            
            state = bytearray(new_left + right)
        
        return bytes(state)
    
    def _round_function(self, data: bytes, round_key: bytes) -> bytes:
        result = bytes(a ^ b for a, b in zip(data, round_key[:len(data)]))

        result = bytes(self.sbox[b] for b in result)

        result = self._bit_permutation(result)

        result = self._linear_transformation(result)
        
        return result
    
    def _bit_permutation(self, data: bytes) -> bytes:
        bits = ''.join(format(b, '08b') for b in data)

        permuted = [bits[i] for i in range(0, len(bits), 2)] +                   [bits[i] for i in range(1, len(bits), 2)]
        
        permuted_str = ''.join(permuted)

        result = bytes(int(permuted_str[i:i+8], 2) 
                      for i in range(0, len(permuted_str), 8))
        
        return result
    
    def _linear_transformation(self, data: bytes) -> bytes:
        result = bytearray(len(data))
        
        for i in range(len(data)):
            result[i] = data[i] ^ data[(i + 1) % len(data)] ^                       data[(i + 2) % len(data)]
        
        return bytes(result)