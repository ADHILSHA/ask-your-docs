# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAIError

from app.api.routes import conversations, documents, health, qa
from app.auth.router import router as auth_router
from app.config import get_settings


def create_app() -> FastAPI:
    # Schema is owned by Alembic migrations (`alembic upgrade head`), not
    # create_all — see the Dockerfile CMD and the README.
    settings = get_settings()
    app = FastAPI(title="ask-your-docs")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        # No cookies/auth credentials are used, so don't opt into them.
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Any OpenAI failure (rate limit, auth, timeout, connection) becomes a clean
    # 502 instead of a bare 500 — handled in one place so every route is covered.
    @app.exception_handler(OpenAIError)
    async def openai_error_handler(request: Request, exc: OpenAIError):
        return JSONResponse(
            status_code=502,
            content={"detail": "Upstream AI service error. Please try again."},
        )

    app.include_router(health.router)
    app.include_router(auth_router)
    app.include_router(documents.router)
    app.include_router(conversations.router)
    app.include_router(qa.router)

    return app


app = create_app()
