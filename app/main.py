from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.responses import (
    NOT_FOUND_MSG,
    SERVER_ERROR_MSG,
    build_param_error_msg,
    error_response,
    format_validation_error,
)
from app.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    init_db()
    yield


app = FastAPI(
    title="DailyWall",
    description="Bing Wallpaper Local Archive API",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request, exc: RequestValidationError
):
    return error_response(400, format_validation_error(exc))


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException):
    if exc.status_code == 400:
        detail = exc.detail if isinstance(exc.detail, str) else None
        return error_response(400, build_param_error_msg(detail))
    if exc.status_code == 404:
        return error_response(404, NOT_FOUND_MSG)
    if exc.status_code == 500:
        return error_response(500, SERVER_ERROR_MSG)

    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return error_response(exc.status_code, detail)


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception):
    return error_response(500, SERVER_ERROR_MSG)


app.include_router(api_router)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
