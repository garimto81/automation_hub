# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 요구 사항

- Python ≥ 3.11
- Docker (Local PostgreSQL) 또는 Supabase (Production)

---

## 프로젝트 개요

**automation_hub** - WSOP 방송 자동화 통합 프로젝트 (공유 인프라)

세 프로젝트가 공통으로 사용하는 **공유 백엔드** 역할:
- Pydantic 모델 + JSON Schema 검증
- PostgreSQL Repository 패턴 (비동기)
- 모니터링 대시보드 (선택)

### 데이터 흐름

```
┌─────────────────────────────────────────────────────────────┐
│  automation_feature_table (RFID) ──┐                        │
│  automation_sub (CSV/수작업) ──────┼─► PostgreSQL/Supabase  │
│                                    │      (공유 DB)         │
│  automation_ae (AE 렌더링) ◄───────┴── polling get_pending()│
└─────────────────────────────────────────────────────────────┘
```

---

## 빌드/테스트 명령

### 환경 설정

```powershell
cp .env.example .env
pip install -e ".[dev]"
```

### 데이터베이스

**Local (Docker)**:
```powershell
docker-compose up -d postgres
docker-compose exec postgres psql -U postgres -d wsop_automation -c "\dt"
```

**Production (Supabase)**:
```powershell
# 스키마 적용 (DATABASE_URL 환경변수 필요)
node scripts/apply-schema.mjs
```

### 테스트

```powershell
pytest tests/ -v                                    # 전체
pytest tests/test_models.py -v                      # 단일 파일
pytest tests/test_models.py::TestHandModel -v       # 단일 클래스
```

> `asyncio_mode = "auto"` 설정으로 `@pytest.mark.asyncio` 불필요

### 린트/타입 체크

```powershell
ruff check shared/ --fix
mypy shared/
```

---

## 코드 구조

```
automation_hub/
├── shared/
│   ├── models/          # Pydantic v2 도메인 모델
│   ├── db/              # Database 연결 + Repository
│   └── validators/      # JSON Schema 검증
├── schemas/v1/          # JSON Schema 정의
├── supabase/migrations/ # Supabase 마이그레이션
├── monitor/             # FastAPI 대시보드 (선택)
└── scripts/
    ├── init-db.sql      # Local Docker 초기화
    └── apply-schema.mjs # Supabase 스키마 적용
```

### 핵심 모듈

**shared/models/** - Pydantic 모델
- `to_db_dict()`: 모델 → DB dict (JSON 직렬화 포함)
- `from_db_row()`: DB row → 모델 역변환

**shared/db/** - 데이터 접근
- `get_db()`: Database 싱글톤
- `async with db.session()`: 자동 commit/rollback
- Raw SQL + asyncpg (ORM 미사용)

**shared/validators/** - JSON Schema 검증
```python
from shared.validators import SchemaValidator
valid, errors = SchemaValidator.validate_gfx_session(data)
```

---

## 데이터베이스 스키마

스키마 정의 위치: `supabase/migrations/`

### 핵심 테이블

| 테이블 | 역할 | 소스 |
|--------|------|------|
| `hands` | 포커 핸드 (레거시) | RFID/CSV |
| `poker_sessions` | GFX 세션 | RFID |
| `poker_hands` | GFX 핸드 | RFID |
| `poker_players` | 핸드 내 플레이어 | RFID |
| `poker_events` | 베팅 액션/이벤트 | RFID |
| `hand_results` | 핸드 결과 (phevaluator) | 계산 |
| `tournaments` | 토너먼트 정보 | CSV |
| `render_instructions` | 렌더링 작업 큐 | sub → ae |
| `render_outputs` | 렌더링 결과 | ae |

### 마이그레이션

```powershell
# 새 마이그레이션 파일 생성
# supabase/migrations/YYYYMMDDHHMMSS_description.sql

# Supabase에 적용
node scripts/apply-schema.mjs
```

---

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| DATABASE_URL | - | Supabase 연결 문자열 |
| POSTGRES_HOST | localhost | Local DB 호스트 |
| POSTGRES_PORT | 5432 | Local DB 포트 |
| POSTGRES_DB | wsop_automation | DB 이름 |
| DEBUG | false | SQL 로깅 활성화 |

---

## 개발 규칙

| 규칙 | 이유 |
|------|------|
| TDD 먼저 | 테스트 → 구현 → 리팩토링 |
| 비동기 필수 | 모든 DB 작업은 `async def` + `await` |
| Pydantic v2 | 타입 검증 + JSON 직렬화 |
| Repository 패턴 | DB 로직 집중화 |

---

## 주의사항

- **싱글톤**: `get_db()` 전역 상태 (테스트 후 `reset_db()` 호출)
- **RLS**: Supabase에서 `service_role` 키 사용 필수
- **Realtime**: `poker_hands`, `hand_results` 테이블 활성화됨

---

## 문서 관리 (중앙화 정책)

### 문서 작성 위치

| 문서 유형 | 작성 위치 | 비고 |
|----------|----------|------|
| **Checklist** | `C:\claude\docs\unified\checklists\HUB\` | 필수 |
| **PRD** | `C:\claude\docs\unified\prds\HUB\` | 신규 생성 시 |
| **기술 명세** | `C:\claude\docs\unified\specs\HUB\` | 선택 |
| Schedule | `docs/schedules/` | 로컬 유지 |
| Schema | `docs/SCHEMA_DESIGN.md` | 로컬 유지 |

### 중앙화 규칙

| 규칙 | 내용 |
|------|------|
| **신규 문서** | 반드시 `docs/unified/{type}/HUB/` 에 생성 |
| **기존 문서 수정** | 중앙 위치로 이동 후 수정 |
| **네이밍** | `HUB-NNNN-{slug}.md` 형식 사용 |
| **로컬 금지** | `tasks/prds/`, `docs/checklists/` 신규 생성 금지 |

### PRD 현황 (6개)

| ID | 제목 | 상태 |
|----|------|:----:|
| HUB-0001 | WSOP Automation Hub v2.0 (Redis, WebSocket) | Draft |
| HUB-0002 | 충돌/중복 모니터링 시스템 | Draft |
| HUB-0003 | 프로젝트 간 모델 통합 | Draft |
| HUB-0004 | 통합 프론트엔드 대시보드 | Draft |
| HUB-0005 | GG Production 자막 워크플로우 (3-App) | Draft |
| HUB-0006 | MVP 일정 관리 시스템 | Draft |

### 프로젝트 의존성

```
HUB (공유 인프라)
├── FT (automation_feature_table) - 데이터 입력
├── SUB (automation_sub) - 데이터 관리
└── AE (automation_ae) - 렌더링 출력
```
