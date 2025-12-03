"""
LTI 1.3 Integration for Canvas LMS
Handles OAuth2 authentication and grade passback
"""

import os
import json
import time
import jwt
from typing import Optional, Dict
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

class LTIConfig:
    """LTI 1.3 Configuration"""
    
    def __init__(self):
        # Canvas LTI Platform Configuration
        self.issuer = os.environ.get("LTI_ISSUER", "https://canvas.instructure.com")
        self.client_id = os.environ.get("LTI_CLIENT_ID")
        self.deployment_id = os.environ.get("LTI_DEPLOYMENT_ID")
        
        # Tool Configuration
        self.tool_url = os.environ.get("TOOL_URL", "https://your-app.onrender.com")
        self.launch_url = f"{self.tool_url}/lti/launch"
        self.jwks_url = f"{self.tool_url}/lti/jwks"
        
        # Canvas Endpoints (these are standard for Canvas)
        self.auth_login_url = f"{self.issuer}/api/lti/authorize_redirect"
        self.auth_token_url = f"{self.issuer}/login/oauth2/token"
        self.keyset_url = f"{self.issuer}/api/lti/security/jwks"
        
        # Private key for signing (generate on first run)
        self.private_key = self._get_or_generate_private_key()
        self.public_key = self.private_key.public_key()
    
    def _get_or_generate_private_key(self):
        """Generate or load RSA private key"""
        key_path = "lti_private_key.pem"
        
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
        else:
            # Generate new key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Save for reuse
            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            with open(key_path, "wb") as f:
                f.write(pem)
            
            return private_key
    
    def get_public_jwks(self) -> Dict:
        """Get public key in JWKS format for Canvas"""
        public_numbers = self.public_key.public_numbers()
        
        # Convert to base64url format
        def int_to_base64url(n):
            import base64
            byte_length = (n.bit_length() + 7) // 8
            n_bytes = n.to_bytes(byte_length, byteorder='big')
            return base64.urlsafe_b64encode(n_bytes).decode('utf-8').rstrip('=')
        
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "alg": "RS256",
                    "use": "sig",
                    "kid": "1",
                    "n": int_to_base64url(public_numbers.n),
                    "e": int_to_base64url(public_numbers.e)
                }
            ]
        }


class LTIValidator:
    """Validates LTI launch requests"""
    
    def __init__(self, config: LTIConfig):
        self.config = config
    
    def validate_launch(self, id_token: str) -> Optional[Dict]:
        """
        Validate LTI 1.3 launch token
        Returns decoded claims if valid, None if invalid
        """
        try:
            # Decode without verification first to get header
            unverified = jwt.decode(id_token, options={"verify_signature": False})
            
            # Verify required claims
            required_claims = [
                "iss",  # Issuer (Canvas)
                "aud",  # Audience (your client_id)
                "sub",  # Subject (user ID)
                "exp",  # Expiration
                "iat",  # Issued at
                "nonce",  # Nonce for security
                "https://purl.imsglobal.org/spec/lti/claim/message_type",
                "https://purl.imsglobal.org/spec/lti/claim/version",
            ]
            
            for claim in required_claims:
                if claim not in unverified:
                    print(f"Missing required claim: {claim}")
                    return None
            
            # Verify issuer and audience
            if unverified["iss"] != self.config.issuer:
                print(f"Invalid issuer: {unverified['iss']}")
                return None
            
            if unverified["aud"] != self.config.client_id:
                print(f"Invalid audience: {unverified['aud']}")
                return None
            
            # In production, fetch Canvas public key and verify signature
            # For now, we'll trust the token if claims are valid
            # TODO: Implement proper signature verification with Canvas public key
            
            return unverified
            
        except jwt.ExpiredSignatureError:
            print("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"Invalid token: {e}")
            return None
        except Exception as e:
            print(f"Error validating token: {e}")
            return None


class LTIGradeSubmitter:
    """Handles grade passback to Canvas"""
    
    def __init__(self, config: LTIConfig):
        self.config = config
    
    def submit_grade(
        self,
        id_token_claims: Dict,
        score: float,
        max_score: float = 1.0,
        comment: str = ""
    ) -> bool:
        """
        Submit grade back to Canvas using LTI Advantage Assignment and Grade Services
        
        Args:
            id_token_claims: Claims from the LTI launch token
            score: Student's score (0.0 to max_score)
            max_score: Maximum possible score (default 1.0)
            comment: Optional comment about the grade
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the lineitem URL from launch claims
            ags_claim = id_token_claims.get(
                "https://purl.imsglobal.org/spec/lti-ags/claim/endpoint"
            )
            
            if not ags_claim:
                print("No AGS endpoint in launch token")
                return False
            
            lineitem_url = ags_claim.get("lineitem")
            if not lineitem_url:
                print("No lineitem URL in AGS claim")
                return False
            
            # Get user ID
            user_id = id_token_claims.get("sub")
            
            # Build grade submission
            grade_data = {
                "userId": user_id,
                "scoreGiven": score,
                "scoreMaximum": max_score,
                "activityProgress": "Completed",
                "gradingProgress": "FullyGraded",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            if comment:
                grade_data["comment"] = comment
            
            # Get access token for Canvas API
            access_token = self._get_access_token(id_token_claims)
            if not access_token:
                print("Failed to get access token")
                return False
            
            # Submit grade to Canvas
            import requests
            
            scores_url = ags_claim.get("scope", [])
            scores_url = lineitem_url + "/scores"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/vnd.ims.lis.v1.score+json"
            }
            
            response = requests.post(scores_url, json=grade_data, headers=headers)
            
            if response.status_code in [200, 201]:
                print(f"Grade submitted successfully: {score}/{max_score}")
                return True
            else:
                print(f"Failed to submit grade: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Error submitting grade: {e}")
            return False
    
    def _get_access_token(self, id_token_claims: Dict) -> Optional[str]:
        """
        Get Canvas API access token using client credentials
        """
        try:
            import requests
            
            # Create JWT for client assertion
            now = int(time.time())
            jwt_claim = {
                "iss": self.config.client_id,
                "sub": self.config.client_id,
                "aud": self.config.auth_token_url,
                "iat": now,
                "exp": now + 300,
                "jti": str(time.time())
            }
            
            client_assertion = jwt.encode(
                jwt_claim,
                self.config.private_key,
                algorithm="RS256",
                headers={"kid": "1"}
            )
            
            # Request access token
            token_data = {
                "grant_type": "client_credentials",
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": client_assertion,
                "scope": "https://purl.imsglobal.org/spec/lti-ags/scope/score"
            }
            
            response = requests.post(self.config.auth_token_url, data=token_data)
            
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                print(f"Token request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting access token: {e}")
            return None


# Session storage for LTI launches
lti_sessions = {}

def store_lti_session(session_id: str, lti_claims: Dict):
    """Store LTI launch data for grade passback later"""
    lti_sessions[session_id] = {
        "claims": lti_claims,
        "timestamp": time.time()
    }

def get_lti_session(session_id: str) -> Optional[Dict]:
    """Retrieve LTI launch data"""
    session = lti_sessions.get(session_id)
    if session:
        # Check if session is less than 2 hours old
        if time.time() - session["timestamp"] < 7200:
            return session["claims"]
    return None
