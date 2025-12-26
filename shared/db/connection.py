"""PostgreSQL 연결 관리"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """DB 설정"""

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "wsop_automation"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


class Database:
    """비동기 PostgreSQL 연결 관리"""

    def __init__(self, settings: Optional[DatabaseSettings] = None):
        self.settings = settings or DatabaseSettings()
        self._engine = None
        self._session_factory = None

    def _create_engine(self):
        """엔진 생성 (lazy initialization)"""
        if self._engine is None:
            self._engine = create_async_engine(
                self.settings.database_url,
                echo=os.getenv("DEBUG", "false").lower() == "true",
                poolclass=NullPool,  # 연결 풀 비활성화 (단순화)
            )
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """세션 컨텍스트 매니저"""
        self._create_engine()
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def execute(self, query: str, params: Optional[dict] = None) -> list[dict]:
        """SQL 실행 (단순 쿼리용)"""
        from sqlalchemy import text

        self._create_engine()
        async with self._engine.connect() as conn:
            result = await conn.execute(text(query), params or {})
            rows = result.fetchall()
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]

    async def execute_write(self, query: str, params: Optional[dict] = None) -> int:
        """SQL 실행 (INSERT/UPDATE/DELETE)"""
        from sqlalchemy import text

        self._create_engine()
        async with self._engine.begin() as conn:
            result = await conn.execute(text(query), params or {})
            return result.rowcount

    async def close(self):
        """연결 종료"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


# 전역 인스턴스
_db_instance: Optional[Database] = None


def get_db() -> Database:
    """전역 DB 인스턴스 반환"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def reset_db():
    """DB 인스턴스 리셋 (테스트용)"""
    global _db_instance
    _db_instance = None
