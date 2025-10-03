# security_manager.py - Secure NLP Interface with encryption and authentication
import hashlib
import secrets
import json
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import whisper
import sounddevice as sd
import numpy as np
import tempfile
import scipy.io.wavfile
import logging

logger = logging.getLogger(__name__)

class SecureNLPInterface:
    def __init__(self, user_db_file="users.json", key_file="encryption.key"):
        self.user_db_file = user_db_file
        self.key_file = key_file
        self.encryption_key = self._load_or_create_key()
        self.fernet = Fernet(self.encryption_key)
        self.users = self._load_users()
        
    def _load_or_create_key(self) -> bytes:
        """Load existing encryption key or create a new one"""
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            return key
    
    def _load_users(self) -> dict:
        """Load user database"""
        if os.path.exists(self.user_db_file):
            try:
                with open(self.user_db_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def _save_users(self):
        """Save user database"""
        with open(self.user_db_file, "w") as f:
            json.dump(self.users, f, indent=2)
    
    def _hash_password(self, password: str, salt: bytes = None) -> tuple:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode(), base64.b64encode(salt).decode()
    
    def register_user(self, username: str, password: str) -> bool:
        """Register a new user with hashed password"""
        if username in self.users:
            return False
        
        hashed_password, salt = self._hash_password(password)
        self.users[username] = {
            "password": hashed_password,
            "salt": salt,
            "created_at": str(datetime.datetime.now()),
            "last_login": None
        }
        self._save_users()
        logger.info(f"User {username} registered successfully")
        return True
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate user with secure password verification"""
        if username not in self.users:
            # Create default user for demo purposes
            if username == "admin" and password == "admin123":
                return self.register_user(username, password)
            return False
        
        user_data = self.users[username]
        salt = base64.b64decode(user_data["salt"].encode())
        hashed_password, _ = self._hash_password(password, salt)
        
        if hashed_password == user_data["password"]:
            self.users[username]["last_login"] = str(datetime.datetime.now())
            self._save_users()
            logger.info(f"User {username} authenticated successfully")
            return True
        
        logger.warning(f"Failed authentication attempt for user {username}")
        return False
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            encrypted = self.fernet.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return data  # Fallback to unencrypted
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return encrypted_data  # Fallback to assume unencrypted
    
    def secure_voice_input(self) -> str:
        """Secure voice input with noise reduction and validation"""
        try:
            print("🎤 Listening... Speak now.")
            fs = 22050
            duration = 8
            
            # Record audio
            print("Recording...")
            audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait()
            print("Recording complete.")
            
            # Apply basic noise reduction
            audio = self._reduce_noise(audio)
            
            # Normalize audio
            if np.max(np.abs(audio)) > 0:
                audio = audio / np.max(np.abs(audio))
            
            # Transcribe using Whisper
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
                scipy.io.wavfile.write(tmpfile.name, fs, audio)
                
                # Load Whisper model
                model = whisper.load_model("small")
                result = model.transcribe(
                    tmpfile.name,
                    language="en",
                    temperature=0.0,  # More deterministic
                    word_timestamps=True
                )
                
                command = result["text"].strip()
                confidence = getattr(result, 'avg_logprob', 0.0)
                
                # Clean up temp file
                os.unlink(tmpfile.name)
                
                if confidence < -1.0:  # Low confidence threshold
                    logger.warning(f"Low confidence transcription: {confidence}")
                    return self._ask_confirmation(command)
                
                print(f"You said: {command}")
                return command.lower()
                
        except Exception as e:
            logger.error(f"Voice input error: {e}")
            return ""
    
    def _reduce_noise(self, audio: np.ndarray) -> np.ndarray:
        """Apply basic noise reduction"""
        # Simple high-pass filter to reduce low-frequency noise
        from scipy import signal
        b, a = signal.butter(4, 300 / (22050 / 2), btype='high')
        return signal.filtfilt(b, a, audio.flatten()).reshape(-1, 1)
    
    def _ask_confirmation(self, command: str) -> str:
        """Ask user to confirm low-confidence transcription"""
        print(f"I heard: '{command}'. Is this correct? (y/n)")
        confirmation = input().strip().lower()
        if confirmation == 'y':
            return command
        else:
            print("Please type your command instead:")
            return input().strip()
    
    def validate_input(self, text: str) -> dict:
        """Validate and sanitize input text"""
        # Remove potentially dangerous characters
        sanitized = ''.join(char for char in text if char.isprintable())
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'eval\(',
            r'exec\(',
            r'__import__',
            r'open\(',
            r'file\('
        ]
        
        import re
        risk_level = "low"
        for pattern in suspicious_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                risk_level = "high"
                break
        
        return {
            "original": text,
            "sanitized": sanitized,
            "risk_level": risk_level,
            "length": len(sanitized)
        }
    
    def log_security_event(self, event_type: str, details: dict):
        """Log security-related events"""
        security_log = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event_type": event_type,
            "details": details
        }
        
        log_file = "security.log"
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(security_log) + "\n")
        except Exception as e:
            logger.error(f"Failed to write security log: {e}")

import datetime