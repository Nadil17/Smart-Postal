from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from cryptography.fernet import Fernet
from config.settings import get_settings
import base64

settings = get_settings()

# Encryption for biometric data
def get_cipher():
    key = settings.ENCRYPTION_KEY.encode()
    if len(key) != 32:
        # Ensure key is 32 bytes
        key = base64.urlsafe_b64encode(key[:32].ljust(32, b'0'))
    return Fernet(key)

def _truncate_password(password: str) -> bytes:
    """Truncate password to 72 bytes for bcrypt compatibility"""
    return password.encode('utf-8')[:72]

def hash_password(password: str) -> str:
    truncated = _truncate_password(password)
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    truncated = _truncate_password(plain_password)
    return bcrypt.checkpw(truncated, hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

def encrypt_biometric_data(data: bytes) -> bytes:
    """Encrypt biometric data before storing"""
    cipher = get_cipher()
    return cipher.encrypt(data)

def decrypt_biometric_data(encrypted_data: bytes) -> bytes:
    """Decrypt biometric data when retrieving"""
    cipher = get_cipher()
    return cipher.decrypt(encrypted_data)