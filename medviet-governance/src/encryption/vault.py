# src/encryption/vault.py
import json
import os
import base64

import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SimpleVault:
    """
    Envelope encryption pattern (local dev substitute for AWS KMS).

    Architecture:
        Master Key (KEK) → encrypts → Data Key (DEK) → encrypts → Data

    ponytail: KEK stored in plain file — swap for HSM/KMS before production.
    """

    def __init__(self, master_key_path: str = ".vault_key"):
        self.master_key_path = master_key_path
        self.kek = self._load_or_create_kek()

    def _load_or_create_kek(self) -> bytes:
        if os.path.exists(self.master_key_path):
            with open(self.master_key_path, "rb") as f:
                return base64.b64decode(f.read())
        kek = os.urandom(32)
        with open(self.master_key_path, "wb") as f:
            f.write(base64.b64encode(kek))
        return kek

    def generate_dek(self) -> tuple[bytes, bytes]:
        plaintext_dek = os.urandom(32)
        aesgcm = AESGCM(self.kek)
        nonce = os.urandom(12)
        encrypted_dek = nonce + aesgcm.encrypt(nonce, plaintext_dek, None)
        return plaintext_dek, encrypted_dek

    def decrypt_dek(self, encrypted_dek: bytes) -> bytes:
        nonce, ciphertext = encrypted_dek[:12], encrypted_dek[12:]
        return AESGCM(self.kek).decrypt(nonce, ciphertext, None)

    def encrypt_data(self, plaintext: str) -> dict:
        plaintext_dek, encrypted_dek = self.generate_dek()

        aesgcm = AESGCM(plaintext_dek)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

        del plaintext_dek

        return {
            "encrypted_dek": base64.b64encode(encrypted_dek).decode(),
            "ciphertext": base64.b64encode(nonce + ciphertext).decode(),
            "algorithm": "AES-256-GCM",
        }

    def decrypt_data(self, encrypted_payload: dict) -> str:
        encrypted_dek = base64.b64decode(encrypted_payload["encrypted_dek"])
        blob = base64.b64decode(encrypted_payload["ciphertext"])

        plaintext_dek = self.decrypt_dek(encrypted_dek)
        nonce, ciphertext = blob[:12], blob[12:]

        plaintext = AESGCM(plaintext_dek).decrypt(nonce, ciphertext, None)
        del plaintext_dek

        return plaintext.decode()

    def encrypt_column(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        df = df.copy()
        df[column] = df[column].apply(lambda x: json.dumps(self.encrypt_data(str(x))))
        return df
