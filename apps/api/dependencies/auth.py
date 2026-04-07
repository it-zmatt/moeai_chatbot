from fastapi import HTTPException, Request, status

from models.client import Client


def get_current_client(request: Request) -> Client:
    current_client = getattr(request.state, "current_client", None)
    if current_client is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    return current_client
