"""
Pytest configuration and shared fixtures.

This file provides reusable fixtures for:
- Async test client (httpx.AsyncClient)
- In-memory SQLite database (replaces MySQL)
- Fake Redis client (replaces Redis Cluster)
"""
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add task-api to Python path so we can import app modules
task_api_root = Path(__file__).parent.parent.parent / "task-api"
sys.path.insert(0, str(task_api_root))

# 在 lifespan 触发前，把真实数据库/Redis 初始化替换为 no-op
# 测试使用 fixture 注入的 in-memory SQLite 和 fakeredis
patch("app.main.init_db", new=AsyncMock()).start()
patch("app.main.init_redis", new=AsyncMock()).start()
patch("app.main.close_db", new=AsyncMock()).start()
patch("app.main.close_redis", new=AsyncMock()).start()

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import fakeredis

from app.database import Base, get_db
from app.main import app


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _dispose_real_engines():
    """app.database.engine 在 import 时就创建了，指向不存在的 MySQL，
    测试结束后必须显式 dispose，否则异步连接池资源会阻止事件循环关闭。"""
    yield
    from app.database import engine as real_engine
    await real_engine.dispose()
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Provide a fresh in-memory database for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def fake_redis():
    """Provide a fake Redis client for testing."""
    server = fakeredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session, fake_redis):
    """Provide an async HTTP client with test database and fake Redis."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.redis_client.redis_client", fake_redis), \
         patch("app.crud.redis_module.redis_client", fake_redis):
        transport = ASGITransport(app=app)
        ac = AsyncClient(transport=transport, base_url="http://test")
        yield ac
        await ac.aclose()

    app.dependency_overrides.clear()
