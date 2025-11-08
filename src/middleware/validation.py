"""
Request validation middleware
"""

import os
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

async def validate_api_key(request: Request, credentials: HTTPAuthorizationCredentials = None):
    """Validate API key from request"""
    expected_key = os.getenv('API_KEY', 'your-vision-api-key-here')
    
    # Skip validation in development if no key set
    if expected_key == 'your-vision-api-key-here':
        return True
    
    # Check Authorization header
    if credentials:
        if credentials.credentials == expected_key:
            return True
    
    # Check x-api-key header
    api_key = request.headers.get('x-api-key')
    if api_key == expected_key:
        return True
    
    raise HTTPException(
        status_code=401,
        detail="Invalid or missing API key"
    )
