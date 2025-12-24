"""
Thread-safe session storage with expiration for PHI token management
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import threading


class SessionStore:
    """Thread-safe session storage with expiration for managing PHI tokens"""
    
    def __init__(self, expiration_hours: int = 24):
        self._store: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self.expiration_hours = expiration_hours
    
    def get(self, session_id: str) -> Optional[Dict[str, str]]:
        """Get tokens for a session if it exists and hasn't expired"""
        with self._lock:
            if session_id in self._store:
                session = self._store[session_id]
                # Check expiration
                if datetime.now() < session['expires_at']:
                    return session['tokens']
                else:
                    # Expired, clean up
                    del self._store[session_id]
            return None
    
    def set(self, session_id: str, tokens: Dict[str, str]):
        """Set tokens for a session with expiration"""
        with self._lock:
            self._store[session_id] = {
                'tokens': tokens,
                'expires_at': datetime.now() + timedelta(hours=self.expiration_hours)
            }
    
    def update(self, session_id: str, new_tokens: Dict[str, str]):
        """Update tokens for a session, merging with existing tokens"""
        with self._lock:
            if session_id not in self._store:
                self.set(session_id, new_tokens)
            else:
                self._store[session_id]['tokens'].update(new_tokens)
                # Refresh expiration
                self._store[session_id]['expires_at'] = datetime.now() + timedelta(hours=self.expiration_hours)
    
    def delete(self, session_id: str) -> bool:
        """Delete a session"""
        with self._lock:
            if session_id in self._store:
                del self._store[session_id]
                return True
            return False
    
    def cleanup_expired(self):
        """Remove expired sessions"""
        with self._lock:
            now = datetime.now()
            expired = [sid for sid, data in self._store.items() if now >= data['expires_at']]
            for sid in expired:
                del self._store[sid]
            return len(expired)

