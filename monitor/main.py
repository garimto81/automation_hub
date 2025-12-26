"""모니터링 대시보드 서비스

각 프로젝트 상태 확인 및 DB 통계 제공.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from shared.db import get_db, RenderInstructionsRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 라이프사이클"""
    yield
    db = get_db()
    await db.close()


app = FastAPI(
    title="WSOP Automation Monitor",
    description="모니터링 대시보드",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/stats")
async def get_stats():
    """전체 통계"""
    db = get_db()
    instructions_repo = RenderInstructionsRepository(db)

    try:
        render_stats = await instructions_repo.get_stats()

        # 핸드 통계
        hands_result = await db.execute(
            "SELECT COUNT(*) as total FROM hands"
        )
        hands_count = hands_result[0]["total"] if hands_result else 0

        # 토너먼트 통계
        tournaments_result = await db.execute(
            "SELECT COUNT(*) as total FROM tournaments"
        )
        tournaments_count = tournaments_result[0]["total"] if tournaments_result else 0

        return {
            "timestamp": datetime.now().isoformat(),
            "hands": {
                "total": hands_count,
            },
            "tournaments": {
                "total": tournaments_count,
            },
            "render_instructions": render_stats,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.get("/pending")
async def get_pending_renders():
    """대기 중인 렌더링 작업"""
    db = get_db()
    instructions_repo = RenderInstructionsRepository(db)

    try:
        pending = await instructions_repo.get_pending(limit=20)
        return {
            "count": len(pending),
            "instructions": [
                {
                    "id": inst.id,
                    "template_name": inst.template_name,
                    "priority": inst.priority,
                    "created_at": inst.created_at.isoformat(),
                }
                for inst in pending
            ],
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
