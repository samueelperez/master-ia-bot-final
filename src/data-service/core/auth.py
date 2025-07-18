"""
Authentication functionality for the External Data Service.
"""
import logging
import time
from typing import Optional, Dict, List
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext

from core.config import settings

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

# Mock users database (in a real implementation, this would be a database)
USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin"),
        "disabled": False,
        "scopes": ["read:all", "write:all"]
    },
    "reader": {
        "username": "reader",
        "hashed_password": pwd_context.hash("reader"),
        "disabled": False,
        "scopes": ["read:all"]
    }
}


class User:
    """User model."""
    
    def __init__(self, username: str, disabled: bool = False, scopes: List[str] = None):
        """
        Initialize a user.
        
        Args:
            username: Username
            disabled: Whether the user is disabled
            scopes: User scopes
        """
        self.username = username
        self.disabled = disabled
        self.scopes = scopes or []


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain password
        hashed_password: Hashed password
        
    Returns:
        Whether the password is correct
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_user(username: str) -> Optional[Dict]:
    """
    Get a user from the database.
    
    Args:
        username: Username
        
    Returns:
        User or None if not found
    """
    if username in USERS_DB:
        user_dict = USERS_DB[username]
        return user_dict
    return None


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """
    Authenticate a user.
    
    Args:
        username: Username
        password: Password
        
    Returns:
        User or None if authentication failed
    """
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create an access token.
    
    Args:
        data: Token data
        expires_delta: Token expiry
        
    Returns:
        JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Get the current user from a token.
    
    Args:
        token: JWT token
        
    Returns:
        User
        
    Raises:
        HTTPException: If authentication failed
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        token_scopes = payload.get("scopes", [])
    except jwt.PyJWTError:
        raise credentials_exception
    
    user_dict = get_user(username)
    if user_dict is None:
        raise credentials_exception
    
    return User(
        username=user_dict["username"],
        disabled=user_dict["disabled"],
        scopes=token_scopes
    )


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current active user.
    
    Args:
        current_user: Current user
        
    Returns:
        User
        
    Raises:
        HTTPException: If the user is disabled
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return current_user


def has_scope(required_scopes: List[str]):
    """
    Check if a user has the required scopes.
    
    Args:
        required_scopes: Required scopes
        
    Returns:
        Dependency function
    """
    async def check_scopes(current_user: User = Depends(get_current_active_user)):
        for scope in required_scopes:
            if scope not in current_user.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required scope: {scope}",
                )
        return current_user
    
    return check_scopes
