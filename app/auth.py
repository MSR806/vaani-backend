import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import requests
from functools import lru_cache
from .config import AUTH0_DOMAIN, AUTH0_API_AUDIENCE, AUTH0_ISSUER, AUTH0_ALGORITHMS
import base64
import struct

# Security scheme for Swagger UI
security = HTTPBearer()


def get_auth0_jwks():
    print(f"AUTH0_DOMAIN: {AUTH0_DOMAIN}")
    """Cache and return Auth0 JSON Web Key Set for verifying tokens"""
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    print(f"JWKS URL: {jwks_url}")
    response = requests.get(jwks_url)
    print(f"Response: {response}")
    return response.json()


def get_signing_key(token):
    """Get the signing key used to sign the token"""
    try:
        jwks = get_auth0_jwks()
        print(f"JWKS: {jwks}")
        unverified_header = jwt.get_unverified_header(token)
        print(f"Unverified header: {unverified_header}")
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                # Convert the RSA key components to PEM format
                n = int.from_bytes(base64.urlsafe_b64decode(key["n"] + "=" * (-len(key["n"]) % 4)), byteorder='big')
                e = int.from_bytes(base64.urlsafe_b64decode(key["e"] + "=" * (-len(key["e"]) % 4)), byteorder='big')
                
                # Construct the RSA public key in PEM format
                from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
                from cryptography.hazmat.primitives import serialization
                
                numbers = RSAPublicNumbers(e, n)
                public_key = numbers.public_key()
                
                pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                return pem
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
        print(f"Key: {key}")
        payload = jwt.decode(
            token,
            key,
            algorithms=AUTH0_ALGORITHMS,
            audience=AUTH0_API_AUDIENCE,
            issuer=AUTH0_ISSUER,
        )
        print(f"Payload: {payload}")
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
    print(f"Token: {token}")
    payload = verify_token(token)
    print(f"Payload: {payload}")
    
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

async def get_auth0_user_details(access_token: str) -> dict:
    """Get user details from Auth0 UserInfo endpoint"""
    try:
        # Make request to Auth0 UserInfo endpoint
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        response = requests.get(
            f"https://{AUTH0_DOMAIN}/userinfo",
            headers=headers
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to fetch user details from Auth0"
            )
            
        user_data = response.json()
        return {
            "name": user_data.get("name") or user_data.get("nickname") or user_data.get("email", "Anonymous"),
            "email": user_data.get("email", "Anonymous")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error fetching user details: {str(e)}"
        )
