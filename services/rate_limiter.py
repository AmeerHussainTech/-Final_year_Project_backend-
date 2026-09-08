"""
Rate Limiter Service for Presenova API
Provides sliding-window rate limiting per IP or JWT Identity.
Support tier-based limits for Guest vs Authenticated users.
"""

import time
import threading
from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity

# In-memory storage for sliding window timestamps
# Structure: { key: [timestamp1, timestamp2, ...] }
_request_records = {}
_lock = threading.Lock()


def rate_limit(limit_authenticated: int = 15, limit_guest: int = 3, window_seconds: int = 60):
    """
    Decorator for Flask routes enforcing rate limits.
    
    Args:
        limit_authenticated: Max requests per window for logged-in JWT users.
        limit_guest: Max requests per window for unauthenticated / guest users.
        window_seconds: Sliding window duration in seconds (default: 60s).
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if request.method == 'OPTIONS':
                return f(*args, **kwargs)
            try:
                user_id = get_jwt_identity()
            except Exception:
                user_id = None

            is_guest = not user_id or user_id == "guest"
            
            # Determine rate limit key & threshold
            client_ip = request.remote_addr or "127.0.0.1"
            key = f"usr:{user_id}" if not is_guest else f"ip:{client_ip}"
            max_allowed = limit_guest if is_guest else limit_authenticated
            
            now = time.time()
            cutoff = now - window_seconds
            
            with _lock:
                timestamps = _request_records.get(key, [])
                # Filter out expired timestamps outside current window
                valid_timestamps = [t for t in timestamps if t > cutoff]
                
                if len(valid_timestamps) >= max_allowed:
                    retry_after = int(window_seconds - (now - valid_timestamps[0]))
                    return jsonify({
                        "error": "Too Many Requests",
                        "message": f"Rate limit exceeded ({max_allowed} requests per {window_seconds}s). Please try again in {retry_after} seconds.",
                        "is_guest": is_guest,
                        "retry_after_seconds": max(1, retry_after)
                    }), 429
                
                valid_timestamps.append(now)
                _request_records[key] = valid_timestamps
                
            return f(*args, **kwargs)
        return wrapped
    return decorator


def enforce_guest_size_limit(max_guest_bytes: int = 10 * 1024 * 1024):
    """
    Helper function checking if a guest upload exceeds guest size cap.
    
    Args:
        max_guest_bytes: Cap for unauthenticated guest trial uploads (default: 10 MB).
    """
    try:
        user_id = get_jwt_identity()
    except Exception:
        user_id = None

    is_guest = not user_id or user_id == "guest"
    
    if is_guest and request.content_length and request.content_length > max_guest_bytes:
        mb = max_guest_bytes // (1024 * 1024)
        return jsonify({
            "error": "Guest File Size Limit Exceeded",
            "message": f"Guest trial uploads are limited to {mb} MB. Please sign up or log in for larger uploads (up to 50 MB)."
        }), 413
    return None

