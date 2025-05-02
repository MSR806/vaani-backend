import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import requests
from functools import lru_cache
from .config import AUTH0_DOMAIN, AUTH0_API_AUDIENCE, AUTH0_ISSUER, AUTH0_ALGORITHMS

# Security scheme for Swagger UI
security = HTTPBearer()


@lru_cache()
def get_auth0_jwks():
    """Cache and return Auth0 JSON Web Key Set for verifying tokens"""
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    return requests.get(jwks_url).json()


def get_signing_key(token):
    """Get the signing key used to sign the token"""
    try:
        jwks = get_auth0_jwks()
        unverified_header = jwt.get_unverified_header(token)
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                return rsa_key
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signing key",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error retrieving token signing key: {str(e)}",
        )


def verify_token(token: str):
    """Verify an Auth0 JWT token"""
    try:
        key = get_signing_key(token)
        payload = jwt.decode(
            token,
            key,
            algorithms=AUTH0_ALGORITHMS,
            audience=AUTH0_API_AUDIENCE,
            issuer=AUTH0_ISSUER,
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to validate token: {str(e)}",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Dependency to enforce authentication and extract user details"""
    token = credentials.credentials
    payload = verify_token(token)
    
    # Extract user information from the token
    # 'sub' is the Auth0 user ID, typically in format 'auth0|user_id'
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identity",
        )
    
    # You can add additional user verification logic here if needed
    
    return {
        "user_id": user_id,
        # Add any additional user information from the token you want to pass to the routes
        "permissions": payload.get("permissions", []),
        "email": payload.get("email")
    }
