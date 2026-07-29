from __future__ import annotations

import base64
import binascii
import os
import secrets
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SecretBox:
    """Versioned authenticated encryption for locally persisted credentials."""

    VERSION = "v1"

    def __init__(self, key_path: Path) -> None:
        self.key_path = key_path
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        if self.key_path.exists():
            key = self.key_path.read_bytes()
        else:
            key = secrets.token_bytes(32)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            descriptor = os.open(self.key_path, flags, 0o600)
            try:
                os.write(descriptor, key)
            finally:
                os.close(descriptor)
        if len(key) != 32:
            raise ValueError("The application secret must contain a 256-bit key")
        self._key = key

    def encrypt(self, plaintext: str) -> str:
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(self._key).encrypt(nonce, plaintext.encode(), self.VERSION.encode())
        encoded = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
        return f"{self.VERSION}:{encoded}"

    def decrypt(self, value: str) -> str:
        version, separator, encoded = value.partition(":")
        if not separator or version != self.VERSION:
            raise ValueError("Unsupported secret ciphertext version")
        try:
            payload = base64.urlsafe_b64decode(encoded.encode("ascii"))
        except (binascii.Error, ValueError) as error:
            raise ValueError("Invalid secret ciphertext encoding") from error
        if len(payload) <= 12:
            raise ValueError("Invalid secret ciphertext")
        try:
            plaintext = AESGCM(self._key).decrypt(payload[:12], payload[12:], version.encode())
        except InvalidTag as error:
            raise ValueError("Secret ciphertext authentication failed") from error
        return plaintext.decode()
