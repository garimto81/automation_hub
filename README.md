# automation_hub

WSOP 방송 자동화 통합 프로젝트 - 공유 모듈 및 모니터링

## 개요

세 프로젝트를 연결하는 공유 인프라:

```
┌─────────────────────────────────────────────────────────────────┐
│                    완전 자동화 파이프라인                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [RFID JSON] → feature_table ─┐                                 │
│  [WSOP+ CSV] → automation_sub ─┼─► PostgreSQL ─► automation_ae  │
│  [수작업 입력] → UI/API ──────┘       (공유 DB)     (polling)   │
│                                                                 │
│  모니터링: automation_hub (상태 확인, 에러 알림만)              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 구조

```
automation_hub/
├── shared/                     # 공유 모듈 (각 프로젝트에서 import)
│   ├── models/
│   │   ├── hand.py             # 핸드 데이터 모델
│   │   ├── tournament.py       # 토너먼트 데이터 모델
│   │   └── render_instruction.py  # 렌더링 지시서 모델
│   └── db/
│       ├── connection.py       # PostgreSQL 연결
│       └── repositories.py     # CRUD 로직
├── monitor/                    # 모니터링 대시보드 (선택)
├── scripts/
│   └── init-db.sql             # DB 초기화 스크립트
├── docker-compose.yml          # PostgreSQL 인프라
└── pyproject.toml
```

## 설치

```bash
# 프로젝트 설치
pip install -e .

# 개발 의존성 포함
pip install -e ".[dev]"

# 모니터링 포함
pip install -e ".[monitor]"
```

## PostgreSQL 시작

```bash
# .env 파일 생성
cp .env.example .env

# PostgreSQL 시작
docker-compose up -d postgres

# 테이블 확인
docker-compose exec postgres psql -U postgres -d wsop_automation -c "\dt"
```

## 사용법

### 각 프로젝트에서 shared 모듈 사용

```python
# DB 연결
from shared.db import get_db, HandsRepository, RenderInstructionsRepository
from shared.models import Hand, RenderInstruction

db = get_db()
hands_repo = HandsRepository(db)
instructions_repo = RenderInstructionsRepository(db)

# feature_table: 핸드 저장
hand = Hand(table_id="feature_1", hand_number=42, ...)
await hands_repo.insert(hand)

# automation_sub: 렌더링 지시서 생성
instruction = RenderInstruction(
    template_name="leaderboard",
    layer_data={"player_name": "John Doe"},
)
await instructions_repo.insert(instruction)

# automation_ae: pending 지시서 polling
pending = await instructions_repo.get_pending()
```

### 모니터링 (선택)

```bash
# 모니터링 서비스 시작
docker-compose --profile monitor up -d

# 대시보드 접속
open http://localhost:8080
```

## 데이터베이스 스키마

### hands 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | PK |
| table_id | VARCHAR | 테이블 ID |
| hand_number | INTEGER | 핸드 번호 |
| hand_rank | VARCHAR | 핸드 랭크 |
| pot_size | INTEGER | 팟 사이즈 |
| players_json | JSONB | 플레이어 정보 |
| source | VARCHAR | rfid/csv/manual |

### render_instructions 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL | PK |
| template_name | VARCHAR | AE 템플릿 이름 |
| layer_data_json | JSONB | 레이어 데이터 |
| status | VARCHAR | pending/processing/completed/failed |
| priority | INTEGER | 1(최고) - 10(최저) |

## 관련 프로젝트

- `automation_feature_table`: RFID JSON 처리
- `automation_sub`: CSV 파싱 + 렌더링 지시서 생성
- `automation_ae`: AE 렌더링 실행
