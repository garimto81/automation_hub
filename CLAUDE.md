# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 프로젝트 개요

**automation_hub** - WSOP 방송 자동화 통합 프로젝트 (공유 인프라)

### 핵심 역할

automation_hub는 세 프로젝트가 공통으로 사용하는 **공유 백엔드** 역할:

1. **Pydantic 모델**: Hand, Tournament, RenderInstruction 등 도메인 모델
2. **PostgreSQL 저장소**: 공유 데이터베이스 및 CRUD Repository 패턴
3. **비동기 DB 연결**: SQLAlchemy + asyncpg를 통한 async/await 지원
4. **모니터링 대시보드** (선택): FastAPI 기반 상태 모니터링

### 연결된 프로젝트

```
┌─────────────────────────────────────────────────────────────┐
│  automation_feature_table (RFID 처리)                       │
│  ↓                                                          │
│  shared.models.Hand → HandsRepository.insert()             │
│  ↓                                                          │
│  PostgreSQL (wsop_automation DB)                           │
│  ↑                                          ↓              │
│  automation_ae (AE 렌더링) ← RenderInstructionsRepository   │
│  ↑                           .get_pending() polling        │
│  automation_sub (CSV + 수작업)                             │
│  RenderInstructionsRepository.insert()                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 빌드/테스트 명령

### 환경 설정

```powershell
# 환경 변수 파일 생성 (.env)
cp .env.example .env

# 프로젝트 설치 (개발 모드)
pip install -e ".[dev]"

# 모니터링 포함 설치
pip install -e ".[monitor]"
```

### PostgreSQL 시작

```powershell
# PostgreSQL 컨테이너 시작 (초기 테이블 자동 생성)
docker-compose up -d postgres

# 컨테이너 상태 확인
docker-compose ps

# 테이블 확인
docker-compose exec postgres psql -U postgres -d wsop_automation -c "\dt"

# 컨테이너 종료
docker-compose down
```

### 테스트 실행

```powershell
# 전체 테스트 (pytest 권장)
pytest tests/ -v

# 단일 테스트 파일
pytest tests/test_models.py -v

# 단일 테스트 케이스
pytest tests/test_models.py::TestHandModel::test_create_hand -v
```

### 린트 및 타입 체크

```powershell
# Ruff 린트 (자동 수정)
ruff check shared/ --fix

# MyPy 타입 체크 (strict mode)
mypy shared/
```

### 모니터링 서비스

```powershell
# 모니터링 포함해서 시작
docker-compose --profile monitor up -d

# 대시보드 접속
# http://localhost:8080
```

---

## 코드 구조

### shared/models/ - 도메인 모델 (Pydantic v2)

| 파일 | 역할 |
|------|------|
| `hand.py` | Hand (포커 핸드), SourceType (RFID/CSV/Manual), HandRank 열거형 |
| `tournament.py` | Tournament (토너먼트), BlindLevel, PayoutEntry |
| `render_instruction.py` | RenderInstruction (렌더링 작업), RenderOutput (결과), RenderStatus |

**핵심 패턴**:
- `to_db_dict()`: Pydantic 모델 → DB 딕셔너리 변환 (JSON 직렬화 포함)
- `from_db_row()`: DB 행 → Pydantic 모델 역변환
- `@property` 메서드: is_premium, display_name 등 비즈니스 로직

### shared/db/ - 데이터 접근 계층

| 파일 | 역할 |
|------|------|
| `connection.py` | Database 클래스, DatabaseSettings (env 파싱), get_db() 싱글톤 |
| `repositories.py` | HandsRepository, TournamentsRepository, RenderInstructionsRepository, RenderOutputsRepository |

**핵심 패턴**:
- **Async Context Manager**: `async with db.session() as session:` 자동 commit/rollback
- **Raw SQL + asyncpg**: SQLAlchemy ORM 대신 execute()/execute_write() 사용 (간단함)
- **Lazy Initialization**: _engine, _session_factory는 첫 사용 시 생성

### 모니터링 서비스 (선택)

| 파일 | 역할 |
|------|------|
| `monitor/main.py` | FastAPI 앱, 상태 조회 엔드포인트 |
| `Dockerfile.monitor` | Python 3.11 컨테이너 이미지 |

---

## 아키텍처 패턴

### 1. 모델 → Repository 단방향 의존성

```
Hand (모델)
  ↓
HandsRepository (DB 접근)
  ↓
Database (연결 관리)
```

각 Repository는 `Database` 인스턴스를 받아서 쿼리 실행.

### 2. 비동기 워크플로우

```python
# 공유 모듈 사용 예시 (다른 프로젝트에서)
from shared.db import get_db, HandsRepository
from shared.models import Hand

db = get_db()
async with db.session() as _:  # 트랜잭션 시작
    repo = HandsRepository(db)
    hand_id = await repo.insert(hand)
# 여기서 자동 commit (예외 발생 시 rollback)
```

### 3. 환경 변수 관리

```python
# DatabaseSettings (shared/db/connection.py)에서 .env 자동 파싱
# .env 파일:
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=postgres
```

---

## 데이터베이스 스키마

### hands 테이블

```sql
CREATE TABLE hands (
    id SERIAL PRIMARY KEY,
    table_id VARCHAR,
    hand_number INTEGER,
    source VARCHAR (rfid|csv|manual),
    hand_rank VARCHAR,
    pot_size INTEGER,
    winner VARCHAR,
    players_json JSONB,
    community_cards_json JSONB,
    actions_json JSONB,
    duration_seconds INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### render_instructions 테이블

```sql
CREATE TABLE render_instructions (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR,
    layer_data_json JSONB,
    output_settings_json JSONB,
    output_path VARCHAR,
    output_filename VARCHAR,
    status VARCHAR (pending|processing|completed|failed),
    priority INTEGER,
    trigger_type VARCHAR,
    trigger_id VARCHAR,
    error_message TEXT,
    retry_count INTEGER,
    max_retries INTEGER,
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### render_outputs 테이블

```sql
CREATE TABLE render_outputs (
    id SERIAL PRIMARY KEY,
    instruction_id INTEGER REFERENCES render_instructions(id),
    output_path VARCHAR,
    file_size INTEGER,
    frame_count INTEGER,
    status VARCHAR,
    error_message TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

---

## 개발 규칙

| 규칙 | 이유 |
|------|------|
| TDD 먼저 작성 | 테스트 → 구현 → 리팩토링 순서 |
| 절대 경로만 사용 | Windows 크로스플랫폼 호환성 |
| 비동기/await 강제 | 멀티 프로젝트 동시 처리 |
| 모델은 Pydantic v2 | 타입 검증 + JSON 직렬화 자동화 |
| Repository 패턴 | DB 로직 집중화 (테스트 용이) |

---

## 일반적인 작업

### 새로운 모델 추가

1. `shared/models/new_model.py` 작성 (Pydantic BaseModel)
2. `to_db_dict()`, `from_db_row()` 메서드 구현
3. `tests/test_models.py`에 테스트 추가
4. Repository 클래스 생성 (`shared/db/repositories.py`)

### 새로운 Repository 메서드

1. `shared/db/repositories.py`에 async 메서드 추가
2. SQL 쿼리 작성 (`:param` 바인딩 사용)
3. `tests/test_models.py`에 테스트 추가
4. DB 마이그레이션 필요시 `scripts/init-db.sql` 업데이트

### DB 마이그레이션

- 현재는 Alembic이 설치되어 있지만 미사용
- 테이블 변경 시: `scripts/init-db.sql` 수정 후 컨테이너 재시작

---

## 주의사항

- **전역 상태**: `_db_instance` 싱글톤 사용 (테스트 후 `reset_db()` 호출)
- **JSON 직렬화**: `to_db_dict()` 사용 시 수동으로 `json.dumps()` 처리 필요
- **타입스트릭트**: MyPy strict mode 활성화 → 타입 힌트 필수
- **비동기**: 모든 DB 작업은 `async def` + `await` 필수
