import hashlib
import json
import time
import pandas as pd
from cryptography.fernet import Fernet

# Generate/load symmetric encryption key
try:
    with open("secret.key", "rb") as f:
        key = f.read()
except FileNotFoundError:
    key = Fernet.generate_key()
    with open("secret.key", "wb") as f:
        f.write(key)

fernet = Fernet(key)

class Block:
    def __init__(self, index, timestamp, encrypted_data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.encrypted_data = encrypted_data  # bytes
        self.previous_hash = previous_hash
        self.hash = self.compute_hash()

    def compute_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "encrypted_data": self.encrypted_data.decode(),
            "previous_hash": self.previous_hash
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        return Block(0, time.time(), fernet.encrypt(b"Genesis Block"), "0")

    def add_block(self, data_dict):
        data_str = json.dumps(data_dict)
        encrypted_data = fernet.encrypt(data_str.encode())
        last_block = self.chain[-1]
        new_block = Block(len(self.chain), time.time(), encrypted_data, last_block.hash)
        self.chain.append(new_block)

    def display_chain(self):
        for block in self.chain:
            print(f"Index: {block.index}")
            print(f"Timestamp: {block.timestamp}")
            print(f"Encrypted Data (base64): {block.encrypted_data}")
            print(f"Decrypted Data: {fernet.decrypt(block.encrypted_data).decode(errors='ignore')}")
            print(f"Previous Hash: {block.previous_hash}")
            print(f"Hash: {block.hash}")
            print("-" * 50)
