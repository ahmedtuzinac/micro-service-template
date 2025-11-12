from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from typing import Callable


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("error_handler")

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        try:
            return await call_next(request)
        
        except HTTPException as e:
            # FastAPI HTTP exceptions
            self.logger.warning(f"HTTP Exception: {e.status_code} - {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": True,
                    "message": e.detail,
                    "status_code": e.status_code
                }
            )
        
        except Exception as e:
            # Unexpected errors
            self.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "message": "Internal server error",
                    "status_code": 500
                }
            )