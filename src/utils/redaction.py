"""
WinGamingDiag - Secret Redaction Utilities
Privacy protection by redacting sensitive data from logs and reports
"""

import re
import hashlib
from typing import Optional, List, Dict, Any, Union, Callable
from dataclasses import dataclass


@dataclass
class RedactionRule:
    """Rule for redacting sensitive data"""
    name: str
    pattern: str
    replacement: Union[str, Callable]
    description: str


class SecretRedactor:
    """
    Redacts sensitive information from diagnostic data.
    Ensures no passwords, API keys, or personal data leaks into reports.
    """
    
    def __init__(self):
        self._username_hashes: Dict[str, str] = {}  # Cache for consistent hashing
        
        # Define redaction rules
        self.rules: List[RedactionRule] = [
            # Passwords
            RedactionRule(
                name="password",
                pattern=r'(password[:=]\s*)\S+',
                replacement=r'\1[REDACTED]',
                description="Passwords in any format"
            ),
            RedactionRule(
                name="pwd",
                pattern=r'(pwd[:=]\s*)\S+',
                replacement=r'\1[REDACTED]',
                description="Password shorthand"
            ),
            
            # API Keys - keep last 4 chars for identification
            RedactionRule(
                name="api_key",
                pattern=r'([aA][pP][iI][_\-]?[kK][eE][yY][:s]?\s*)([a-zA-Z0-9\-_]{20,})',
                replacement=self._redact_api_key,
                description="API keys with partial visibility"
            ),
            
            # Authentication tokens
            RedactionRule(
                name="token",
                pattern=r'(token[:=]\s*)\S+',
                replacement=r'\1[REDACTED]',
                description="Authentication tokens"
            ),
            RedactionRule(
                name="bearer_token",
                pattern=r'(Bearer\s+)\S+',
                replacement=r'\1[REDACTED]',
                description="Bearer authentication tokens"
            ),
            
            # Secrets
            RedactionRule(
                name="secret",
                pattern=r'(secret[:=]\s*)\S+',
                replacement=r'\1[REDACTED]',
                description="Secret keys"
            ),
            
            # Private keys (SSH, etc.)
            RedactionRule(
                name="private_key",
                pattern=r'(-----BEGIN [A-Z ]+ PRIVATE KEY-----)[\s\S]+?(-----END [A-Z ]+ PRIVATE KEY-----)',
                replacement=r'\1[REDACTED]\2',
                description="Private keys"
            ),
            
            # Credit cards (mask all but last 4)
            RedactionRule(
                name="credit_card",
                pattern=r'\b(\d{4}[-\s]?){3}(\d{4})\b',
                replacement=r'****-****-****-\2',
                description="Credit card numbers"
            ),
            
            # Social Security Numbers
            RedactionRule(
                name="ssn",
                pattern=r'\b\d{3}-\d{2}-\d{4}\b',
                replacement='[SSN-REDACTED]',
                description="Social Security Numbers"
            ),
            
            # Email addresses (keep domain)
            RedactionRule(
                name="email",
                pattern=r'\b([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
                replacement=self._redact_email,
                description="Email addresses"
            ),
            
            # MAC addresses (keep manufacturer prefix)
            RedactionRule(
                name="mac_address",
                pattern=r'\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b',
                replacement=self._redact_mac,
                description="MAC addresses"
            ),
            
            # IP addresses (keep class)
            RedactionRule(
                name="ip_address",
                pattern=r'\b(\d{1,3}\.\d{1,3}\.\d{1,3})\.\d{1,3}\b',
                replacement=r'\1.***',
                description="IP addresses"
            ),
            
            # Database connection strings
            RedactionRule(
                name="connection_string_password",
                pattern=r'(Password|Pwd)=([^;]+)',
                replacement=r'\1=[REDACTED]',
                description="Database connection string passwords"
            ),
            
            # Windows product keys
            RedactionRule(
                name="product_key",
                pattern=r'\b([A-Z0-9]{5}-){4}[A-Z0-9]{5}\b',
                replacement='[PRODUCT-KEY-REDACTED]',
                description="Windows product keys"
            ),
            
            # Serial numbers (long alphanumeric)
            RedactionRule(
                name="serial_number",
                pattern=r'\b([A-Z0-9]{10,})\b',
                replacement=self._redact_serial,
                description="Hardware serial numbers"
            ),
        ]
    
    def _redact_api_key(self, match) -> str:
        """Redact API key, keeping last 4 chars"""
        prefix = match.group(1)
        key = match.group(2)
        if len(key) > 8:
            return f"{prefix}{'*' * (len(key) - 4)}{key[-4:]}"
        return f"{prefix}[REDACTED]"
    
    def _redact_email(self, match) -> str:
        """Redact email, keeping domain"""
        local = match.group(1)
        domain = match.group(2)
        if len(local) > 3:
            return f"{local[:2]}***@{domain}"
        return f"***@{domain}"
    
    def _redact_mac(self, match) -> str:
        """Redact MAC, keeping first 3 octets"""
        full_mac = match.group(0)
        parts = re.split(r'[:-]', full_mac)
        if len(parts) == 6:
            return f"{parts[0]}:{parts[1]}:{parts[2]}:**:**:**"
        return "[MAC-REDACTED]"
    
    def _redact_serial(self, match) -> str:
        """Redact serial number, keeping first and last 2 chars"""
        serial = match.group(1)
        if len(serial) > 6:
            return f"{serial[:2]}{'*' * (len(serial) - 4)}{serial[-2:]}"
        return "[SERIAL-REDACTED]"
    
    def anonymize_username(self, username: str) -> str:
        """
        Anonymize username with consistent hashing
        Same username always produces same hash within session
        """
        if username in self._username_hashes:
            return self._username_hashes[username]
        
        # Hash the username
        hashed = hashlib.sha256(username.encode()).hexdigest()[:8]
        anonymized = f"USER_{hashed}"
        self._username_hashes[username] = anonymized
        return anonymized
    
    def redact_path(self, path: str) -> str:
        """
        Redact username from file paths
        r"C:\Users\JohnDoe\Documents -> C:\Users\USER_abc12345\Documents"
        """
        # Match Windows user paths
        windows_pattern = r'(C:\\Users\\|/Users/)([^/\\]+)([/\\])'
        
        def replace_user(match):
            prefix = match.group(1)
            username = match.group(2)
            suffix = match.group(3)
            
            # Don't anonymize system accounts
            if username.lower() in ['public', 'default', 'all users', 'default user']:
                return match.group(0)
            
            anonymized = self.anonymize_username(username)
            return f"{prefix}{anonymized}{suffix}"
        
        return re.sub(windows_pattern, replace_user, path, flags=re.IGNORECASE)
    
    def redact_text(self, text: Union[str, bytes]) -> str:
        """
        Apply all redaction rules to text
        
        Args:
            text: Text to redact
            
        Returns:
            Redacted text
        """
        if text is None:
            return ""
        
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        
        if not isinstance(text, str):
            text = str(text)
        
        redacted = text
        
        # Apply each rule
        for rule in self.rules:
            try:
                if callable(rule.replacement):
                    redacted = re.sub(rule.pattern, rule.replacement, redacted, flags=re.IGNORECASE)
                else:
                    redacted = re.sub(rule.pattern, rule.replacement, redacted, flags=re.IGNORECASE)
            except Exception as e:
                # If a rule fails, continue with others
                continue
        
        # Redact paths
        redacted = self.redact_path(redacted)
        
        return redacted
    
    def redact_dict(self, data: Dict[str, Any], sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Redact sensitive data from a dictionary
        
        Args:
            data: Dictionary to redact
            sensitive_keys: Keys that should always be redacted
            
        Returns:
            Redacted dictionary copy
        """
        if sensitive_keys is None:
            sensitive_keys = [
                'password', 'pwd', 'secret', 'token', 'key', 'api_key',
                'private_key', 'credential', 'auth', 'passphrase'
            ]
        
        redacted = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key is sensitive
            is_sensitive = any(sk in key_lower for sk in sensitive_keys)
            
            if is_sensitive and isinstance(value, str):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value, sensitive_keys)
            elif isinstance(value, list):
                redacted[key] = [self.redact_dict(item, sensitive_keys) if isinstance(item, dict) 
                                else self.redact_text(str(item)) if isinstance(item, str) 
                                else item for item in value]
            elif isinstance(value, str):
                redacted[key] = self.redact_text(value)
            else:
                redacted[key] = value
        
        return redacted
    
    def redact_list(self, items: List[Any]) -> List[Any]:
        """Redact sensitive data from a list of items"""
        return [self.redact_dict(item) if isinstance(item, dict) 
                else self.redact_text(str(item)) if isinstance(item, str) 
                else item for item in items]
    
    def create_redacted_copy(self, data: Any) -> Any:
        """
        Create a redacted copy of any data structure
        
        Args:
            data: Any data (dict, list, str, etc.)
            
        Returns:
            Redacted copy
        """
        if isinstance(data, dict):
            return self.redact_dict(data)
        elif isinstance(data, list):
            return self.redact_list(data)
        elif isinstance(data, str):
            return self.redact_text(data)
        else:
            return data


# Singleton instance
_redactor = None

def get_redactor() -> SecretRedactor:
    """Get singleton redactor instance"""
    global _redactor
    if _redactor is None:
        _redactor = SecretRedactor()
    return _redactor


def redact_sensitive_data(data: Any) -> Any:
    """
    Convenience function to redact sensitive data
    
    Args:
        data: Data to redact
        
    Returns:
        Redacted data
    """
    return get_redactor().create_redacted_copy(data)


def redact_text(text: str) -> str:
    """
    Convenience function to redact text
    
    Args:
        text: Text to redact
        
    Returns:
        Redacted text
    """
    return get_redactor().redact_text(text)


def anonymize_username(username: str) -> str:
    """
    Convenience function to anonymize username
    
    Args:
        username: Username to anonymize
        
    Returns:
        Anonymized username
    """
    return get_redactor().anonymize_username(username)


__all__ = [
    'RedactionRule',
    'SecretRedactor',
    'get_redactor',
    'redact_sensitive_data',
    'redact_text',
    'anonymize_username'
]
