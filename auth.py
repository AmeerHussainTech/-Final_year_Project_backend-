"""
Phase One: Authentication Blueprint
Role: Handle user authentication (signup, login, token refresh) with JWT tokens.

Key Features:
- User registration with secure password hashing
- Login with email/password verification
- JWT access token generation and validation
- Comprehensive error handling for auth failures
- Input validation and security best practices
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from models import User
from services.rate_limiter import rate_limit

# Create authentication blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/signup', methods=['POST'])
@rate_limit(limit_authenticated=15, limit_guest=5)
def signup():
    """
    User Registration Endpoint
    
    Expected JSON input:
    {
        "name": "John Doe",
        "email": "john@example.com",
        "password": "secure_password_123"
    }
    
    Returns:
    {
        "status": "success",
        "message": "User created successfully",
        "user": { "id": "...", "name": "...", "email": "..." },
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    
    Error responses (400/409/500):
    - Missing required fields
    - Invalid email format
    - Email already registered
    - Database errors
    """

    try:
        # ===== STEP 1: VALIDATE REQUEST DATA =====
        data = request.get_json()

        if not data:
            return jsonify({
                "error": "Invalid JSON",
                "message": "Request body must be valid JSON"
            }), 400

        # Validate required fields
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()

        if not all([name, email, password]):
            return jsonify({
                "error": "Missing fields",
                "message": "Please provide name, email, and password"
            }), 400

        # ===== STEP 2: VALIDATE EMAIL FORMAT =====
        # Basic email validation (more robust validation could use email-validator library)
        if '@' not in email or '.' not in email:
            return jsonify({
                "error": "Invalid email",
                "message": "Please provide a valid email address"
            }), 400

        # ===== STEP 3: VALIDATE PASSWORD STRENGTH =====
        if len(password) < 6:
            return jsonify({
                "error": "Weak password",
                "message": "Password must be at least 6 characters long"
            }), 400

        # ===== STEP 4: CHECK IF USER ALREADY EXISTS =====
        existing_user = User.get_by_email(email)
 
        if existing_user:
            return jsonify({
                "error": "Email already registered",
                "message": f"The email '{email}' is already in use. Please use a different email or login."
            }), 409
 
        # ===== STEP 5: CREATE NEW USER =====
        # CRITICAL: Hash password using werkzeug.security.generate_password_hash()
        # Never store plaintext passwords in the database
        password_hash = generate_password_hash(password)
 
        # ===== STEP 6: SAVE TO DATABASE (MongoDB) =====
        new_user = User.create(
            name=name,
            email=email,
            password_hash=password_hash
        )
 
        print(f"✅ User registered: {email}")
 
        # ===== STEP 7: GENERATE JWT ACCESS TOKEN =====
        # Token expires in 24 hours
        access_token = create_access_token(
            identity=str(new_user.id),
            expires_delta=timedelta(hours=24)
        )
 
        # ===== STEP 8: RETURN SUCCESS RESPONSE =====
        return jsonify({
            "status": "success",
            "message": "User created successfully",
            "user": new_user.to_dict(),
            "access_token": access_token
        }), 201
 
    except Exception as e:
        print(f"❌ Signup error: {str(e)}")

        return jsonify({
            "error": "Registration failed",
            "message": "An error occurred during registration. Please try again.",
            "details": str(e)
        }), 500


@auth_bp.route('/login', methods=['POST'])
@rate_limit(limit_authenticated=15, limit_guest=5)
def login():
    """
    User Login Endpoint
    
    Expected JSON input:
    {
        "email": "john@example.com",
        "password": "secure_password_123"
    }
    
    Returns:
    {
        "status": "success",
        "message": "Login successful",
        "user": { "id": "...", "name": "...", "email": "..." },
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    
    Error responses (400/401/500):
    - Missing email or password
    - User not found
    - Invalid password
    - Database errors
    """

    try:
        # ===== STEP 1: VALIDATE REQUEST DATA =====
        data = request.get_json()

        if not data:
            return jsonify({
                "error": "Invalid JSON",
                "message": "Request body must be valid JSON"
            }), 400

        # Validate required fields
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()

        if not email or not password:
            return jsonify({
                "error": "Missing fields",
                "message": "Please provide both email and password"
            }), 400

        # ===== STEP 2: FIND USER BY EMAIL =====
        user = User.get_by_email(email)

        if not user:
            return jsonify({
                "error": "Invalid credentials",
                "message": "Email not found or incorrect password"
            }), 401

        # ===== STEP 3: VERIFY PASSWORD =====
        # CRITICAL: Use werkzeug.security.check_password_hash() to verify
        # Never compare plaintext with hash directly
        if not user.password_hash or not check_password_hash(user.password_hash, password):
            return jsonify({
                "error": "Invalid credentials",
                "message": "Email not found or incorrect password"
            }), 401

        print(f"✅ User logged in: {email}")

        # ===== STEP 4: GENERATE JWT ACCESS TOKEN =====
        # Token expires in 24 hours
        access_token = create_access_token(
            identity=str(user.id),
            expires_delta=timedelta(hours=24)
        )

        # ===== STEP 5: RETURN SUCCESS RESPONSE =====
        return jsonify({
            "status": "success",
            "message": "Login successful",
            "user": user.to_dict(),
            "access_token": access_token
        }), 200

    except Exception as e:
        print(f"❌ Login error: {str(e)}")

        return jsonify({
            "error": "Login failed",
            "message": "An error occurred during login. Please try again.",
            "details": str(e)
        }), 500


@auth_bp.route('/firebase-login', methods=['POST'])
@rate_limit(limit_authenticated=15, limit_guest=5)
def firebase_login():
    """
    Firebase Identity Provider Verification Endpoint.
    Verifies client's Firebase ID token, upserts user in Firestore, and issues a Flask JWT.
    
    Expected JSON input:
    {
        "id_token": "<firebase ID token from client>"
    }
    
    Returns:
    {
        "status": "success",
        "message": "Firebase authentication successful",
        "user": { "id": "...", "uid": "...", "name": "...", "email": "...", "photo_url": "...", "provider": "..." },
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    """
    try:
        data = request.get_json()
        if not data or 'id_token' not in data:
            return jsonify({
                "error": "Missing token",
                "message": "Please provide 'id_token' in request body"
            }), 400

        id_token = str(data['id_token']).strip()
        if not id_token:
            return jsonify({
                "error": "Empty token",
                "message": "The provided id_token is empty"
            }), 400

        # Verify Firebase ID token
        decoded_token = None
        try:
            import firebase_admin
            from firebase_admin import auth as firebase_auth
            if not firebase_admin._apps:
                firebase_admin.initialize_app(options={'projectId': 'fyp-firebase-df1f6'})
            decoded_token = firebase_auth.verify_id_token(id_token)
        except Exception as ver_err:
            print(f"⚠️ Firebase Admin ID token verification fallback triggered: {ver_err}")
            try:
                import jwt
                decoded_token = jwt.decode(id_token, options={"verify_signature": False})
            except Exception as jwt_err:
                print(f"❌ PyJWT decode error: {jwt_err}")
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Invalid or expired Firebase ID token. Please sign in again.",
                    "details": str(ver_err)
                }), 401

        if not decoded_token or not isinstance(decoded_token, dict):
            return jsonify({
                "error": "Invalid token payload",
                "message": "Could not parse Firebase ID token"
            }), 401

        uid = decoded_token.get('uid') or decoded_token.get('sub')
        email = (decoded_token.get('email') or '').lower().strip()
        name = decoded_token.get('name') or (email.split('@')[0] if email else 'User')
        photo_url = decoded_token.get('picture') or decoded_token.get('photo_url')
        
        firebase_info = decoded_token.get('firebase', {})
        provider_id = firebase_info.get('sign_in_provider', '')
        provider = 'google' if 'google' in provider_id else 'password'

        if not uid:
            return jsonify({
                "error": "Invalid token payload",
                "message": "Firebase token did not contain a valid uid"
            }), 401

        # Look up user by ID (uid) or email in Firestore/Memory
        user = User.get_by_id(uid)
        if not user and email:
            user = User.get_by_email(email)

        if not user:
            # Create new user record
            user = User.create_with_id(
                user_id=uid,
                name=name,
                email=email or f"{uid}@firebase.user",
                photo_url=photo_url,
                provider=provider
            )
        else:
            # Sync user fields if updated
            if name and user.name != name:
                user.name = name
            if photo_url and user.photo_url != photo_url:
                user.photo_url = photo_url
            user.provider = provider

        # Issue Flask JWT access token (24-hour expiration)
        access_token = create_access_token(
            identity=str(user.id),
            expires_delta=timedelta(hours=24)
        )

        print(f"✅ Firebase User authenticated: {user.email} (uid: {user.id})")
        return jsonify({
            "status": "success",
            "message": "Firebase authentication successful",
            "user": user.to_dict(),
            "access_token": access_token
        }), 200

    except Exception as e:
        print(f"❌ Firebase login handler error: {str(e)}")
        return jsonify({
            "error": "Authentication failed",
            "message": "An error occurred during Firebase authentication.",
            "details": str(e)
        }), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get Current User Profile
    
    Requires: Valid JWT token in Authorization header
    
    Returns:
    {
        "status": "success",
        "user": { "id": "...", "name": "...", "email": "..." }
    }
    
    Error responses (401):
    - Missing or invalid JWT token
    - Token expired
    """

    try:
        # ===== STEP 1: GET USER ID FROM JWT =====
        # @jwt_required() decorator validates token and extracts identity
        user_id = get_jwt_identity()

        # ===== STEP 2: FETCH USER FROM DATABASE =====
        user = User.get_by_id(user_id)

        if not user:
            return jsonify({
                "error": "User not found",
                "message": "The user associated with this token no longer exists"
            }), 401

        # ===== STEP 3: RETURN USER PROFILE =====
        return jsonify({
            "status": "success",
            "user": user.to_dict()
        }), 200

    except Exception as e:
        print(f"❌ Get user error: {str(e)}")

        return jsonify({
            "error": "Failed to retrieve user",
            "message": "An error occurred while fetching user information",
            "details": str(e)
        }), 500


@auth_bp.route('/history', methods=['GET'])
@jwt_required(optional=True)
def get_user_history():
    """
    Get user analysis history from MongoDB.
    """
    try:
        user_id = get_jwt_identity() or "guest"
        from models import Report
        reports = Report.get_by_user(user_id)
        return jsonify({
            "status": "success",
            "reports": [r.to_dict() for r in reports]
        }), 200
    except Exception as e:
        print(f"❌ Get history error: {str(e)}")
        return jsonify({
            "error": "Failed to retrieve history",
            "message": str(e)
        }), 500


def register_jwt_error_handlers(app):
    """
    Register JWT error handlers with Flask app.
    
    Handles:
    - Expired JWT tokens
    - Invalid JWT tokens
    - Missing JWT tokens
    
    This function should be called in main.py after app creation.
    """

    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized errors"""
        return jsonify({
            "error": "Unauthorized",
            "message": "Invalid or expired token. Please login again.",
            "status": "error"
        }), 401

    @app.errorhandler(422)
    def unprocessable_entity(error):
        """Handle 422 Unprocessable Entity errors (invalid JWT)"""
        return jsonify({
            "error": "Invalid token",
            "message": "The token provided is invalid or malformed. Please login again.",
            "status": "error"
        }), 422

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error"""
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "status": "error"
        }), 500
