import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import SECRET_KEY


MASKED_VALUE = "********"


def _fernet():
    key = base64.urlsafe_b64encode(
        hashlib.sha256(
            SECRET_KEY.encode("utf-8")
        ).digest()
    )
    return Fernet(key)


def encrypt_secret(plaintext):
    if plaintext is None:
        return None

    plaintext = str(plaintext)

    if plaintext == "":
        return ""

    return _fernet().encrypt(
        plaintext.encode("utf-8")
    ).decode("utf-8")


def decrypt_secret(ciphertext):
    if ciphertext is None:
        return None

    ciphertext = str(ciphertext)

    if ciphertext == "":
        return ""

    try:
        return _fernet().decrypt(
            ciphertext.encode("utf-8")
        ).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def is_secret_set(ciphertext):
    if ciphertext is None:
        return False

    return str(ciphertext) != ""


def masked_secret(ciphertext):
    if is_secret_set(ciphertext):
        return MASKED_VALUE

    return ""


def to_encrypted_storage(plaintext):
    if not plaintext:
        return plaintext

    return encrypt_secret(plaintext)
