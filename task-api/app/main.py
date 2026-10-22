import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.logging_config import setup_logging
from app.database import init_db, close_db
from app.redis_client import init_redis, close_redis
from app.middleware import request_logging_middleware
from app.routers import health, tasks

setup_logging()
logger = logging.getLogger("task_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting task-api service")
    await init_db()
    logger.info("MySQL initialized")
    await init_redis()
    logger.info("Redis initialized")
    yield
    logger.info("Shutting down task-api service")
    await close_redis()
    await close_db()


app = FastAPI(title="Task API", version="1.0.0", lifespan=lifespan)

app.middleware("http")(request_logging_middleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(health.router)
app.include_router(tasks.router)
