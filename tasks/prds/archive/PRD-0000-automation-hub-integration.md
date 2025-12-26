# PRD-0000: WSOP 방송 자동화 통합 허브 (automation_hub)

## 문서 정보

| 항목 | 내용 |
|------|------|
| **PRD ID** | PRD-0000 |
| **제목** | WSOP 방송 자동화 통합 허브 (automation_hub) |
| **부제** | 3개 프로젝트 공유 인프라 + Level 3 오케스트레이션 |
| **버전** | 2.0 (Reliability Update) |
| **작성일** | 2025-12-26 |
| **수정일** | 2025-12-26 |
| **상태** | In Progress |
| **일정** | 2025-12-26 ~ 2026-01-31 (5주) |

### 관련 문서

| PRD | 제목 | 설명 |
|-----|------|------|
| [PRD-0001](../../../automation_feature_table/tasks/prds/PRD-0001-poker-hand-auto-capture.md) | 포커 핸드 자동 캡처 시스템 | automation_feature_table: RFID 처리 |
| PRD-WSOP-Sub | WSOP 방송 자동화 워크플로우 | automation_sub: CSV 렌더링 지시 |
| PRD-WSOP-AE | After Effects 자동 렌더링 | automation_ae: AE 템플릿 렌더링 |

---

## 1. 개요

### 1.1 배경

WSOP(World Series of Poker) 방송 자동화를 위해 3개의 독립적인 프로젝트가 개발 중입니다:

1. **automation_feature_table**: RFID 기반 포커 핸드 자동 캡처
2. **automation_sub**: CSV + 수작업 데이터 통합 및 그래픽 생성
3. **automation_ae**: After Effects 템플릿 자동 렌더링

현재 각 프로젝트는 **독립적으로 작동**하여, 다음과 같은 문제가 발생합니다:

#### 현재 문제점

| 문제 | 영향 | 심각도 |
|------|------|--------|
| **데이터 흐름 미연결** | 핸드 → 렌더링 지시 → 출력이 서로 다른 DB에 산재 | 높음 |
| **상태 추적 불가** | 특정 핸드의 렌더링 상태를 추적할 수 없음 | 높음 |
| **에러 대응 미흡** | 한 프로젝트의 장애가 다른 프로젝트에 영향 미침 | 높음 |
| **모니터링 부재** | 3개 프로젝트의 상태를 중앙에서 확인 불가 | 중간 |
| **자동 조치 불가** | 지연, 실패 등 상황에 자동 대응 불가 | 중간 |

### 1.2 솔루션: automation_hub

**automation_hub**는 3개 프로젝트를 통합하는 **공유 인프라 + 오케스트레이션 허브**입니다.

```
┌─────────────────────────────────────────────────────────────┐
│                   automation_hub (통합 중심)                │
│   ├── PostgreSQL (공유 DB)                                   │
│   │   ├── hands (RFID 포커 데이터)                           │
│   │   ├── tournaments (토너먼트 정보)                        │
│   │   ├── render_instructions (렌더링 작업 큐)               │
│   │   ├── render_outputs (렌더링 결과)                       │
│   │   └── monitoring_events (모니터링 이벤트)                │
│   │                                                           │
│   ├── Level 3 오케스트레이션                                 │
│   │   ├── 자동 감지 (anomaly detection)                      │
│   │   ├── 자동 결정 (auto-remediation)                       │
│   │   └── 개입 가능 (manual override)                        │
│   │                                                           │
│   └── 모니터링 대시보드 (FastAPI)                            │
│       ├── 실시간 상태 조회                                    │
│       ├── 메트릭 분석                                        │
│       └── 관리자 개입 (재시도, 우선순위 등)                 │
│                                                              │
├─ automation_feature_table (RFID 처리)                        │
│  ↓ Hand 데이터 저장                                          │
├─ automation_sub (CSV 통합)                                   │
│  ↓ RenderInstruction 생성                                    │
└─ automation_ae (AE 렌더링)                                   │
   ↓ RenderOutput 저장                                         │
   └─► PostgreSQL (공유 DB)                                   │
```

### 1.3 목표

| 목표 | 상세 |
|------|------|
| **완전 통합** | 3개 프로젝트가 단일 PostgreSQL 사용하여 데이터 일관성 확보 |
| **자동화 확대** | 수동 개입 최소화 (지연, 실패 자동 감지 및 조치) |
| **가시성 확보** | 실시간 대시보드로 3개 프로젝트 상태 중앙 모니터링 |
| **유연성 유지** | 모든 자동 결정을 관리자가 수동으로 변경 가능 |

### 1.4 성공 지표

| 지표 | 목표값 |
|------|--------|
| **데이터 흐름 완성도** | 100% (Hand → RenderInstruction → RenderOutput) |
| **모니터링 가용성** | 99.9% (대시보드 정상 작동) |
| **이상 감지 정확도** | > 95% (거짓 양성 < 5%) |
| **자동 재시도 성공률** | > 85% |
| **평균 응답 시간** | < 50ms (모니터링 API) |

---

## 2. 사용자 환경

### 2.1 사용자

| 역할 | 설명 |
|------|------|
| **방송 엔지니어** | 실시간으로 대시보드 모니터링, 문제 발생 시 즉시 개입 |
| **시스템 관리자** | 월 1회 설정 변경, 성능 최적화 |
| **데이터 관리자** | CSV 입력 및 품질 관리 (automation_sub) |

### 2.2 사용 환경

| 항목 | 현황 |
|------|------|
| **배포 환경** | 온프레미스 (로컬 네트워크) |
| **운영 시간** | 방송 기간 24시간 연속 운영 |
| **대시보드 접속** | 웹 브라우저 (http://localhost:8080) |
| **Python 버전** | 3.11+ |
| **DB** | PostgreSQL 16 |

### 2.3 주요 시나리오

#### 시나리오 1: 정상 데이터 흐름
```
1. automation_feature_table: RFID JSON → Hand 생성
2. PostgreSQL: hands 테이블 저장
3. Event 감지: 프리미엄 핸드 (Royal Flush 이상)
4. automation_sub: RenderInstruction 자동 생성
5. PostgreSQL: render_instructions (status=pending) 저장
6. automation_ae: InstructionPoller 감지 → Job 생성
7. Celery: render_worker 렌더링 실행
8. PostgreSQL: render_outputs 저장 + NAS 최종 저장
9. Monitoring: 완료 알림 + 대시보드 갱신
```

#### 시나리오 2: 렌더링 지연 감지
```
1. 모니터링 워커: RenderInstruction (pending > 30분) 감지
2. monitoring_events: 'anomaly' 이벤트 생성 (severity=warning)
3. 대시보드: 실시간 알림 (Slack/Email)
4. 옵션 A (자동): max_retries < retry_count면 자동 재시도
5. 옵션 B (수동): 관리자 POST /api/actions/retry 호출
6. RenderInstruction: status=pending으로 리셋 + 우선순위 상향
7. automation_ae: 다음 polling에서 감지 및 재처리
```

#### 시나리오 3: 에러 발생 및 수동 개입
```
1. automation_ae: 렌더링 실패 (Nexrender 503 timeout)
2. render_worker: status=failed, retry_count 증가
3. 모니터링: error_rate > 10% 감지 → alert
4. 대시보드: 실패한 작업 목록 표시
5. 관리자: 네트워크 문제 해결 후 bulk-retry
6. POST /api/actions/bulk-retry: {status: 'failed', created_after: ...}
7. 조건 기반 일괄 재시도 실행
```

---

## 3. 기능 명세

### 3.1 공유 데이터 모델

#### 3.1.1 Hand (포커 핸드)
```python
Hand:
  - id: int (PK)
  - table_id: str (피처 테이블 ID)
  - hand_number: int (테이블 내 핸드 번호)
  - source: SourceType (RFID | CSV | MANUAL)
  - hand_rank: HandRank (Royal Flush ~ High Card)
  - pot_size: int
  - winner: str
  - players: list[PlayerInfo] (플레이어 정보)
  - community_cards: list[str]
  - is_premium: bool (property) → 프리미엄 핸드 여부
  - created_at: datetime
```

**생성 주체**: automation_feature_table (RFID 수신 시)

#### 3.1.2 RenderInstruction (렌더링 작업)
```python
RenderInstruction:
  - id: int (PK)
  - template_name: str (AE 템플릿 이름)
  - layer_data: dict (AE에 주입할 데이터)
  - output_settings: OutputSettings (PNG, MOV, MP4 포맷)
  - status: RenderStatus (PENDING → PROCESSING → COMPLETED/FAILED)
  - priority: int (1=최고, 10=최저)
  - trigger_type: str (premium_hand, elimination 등)
  - trigger_id: str (Hand ID 또는 Event ID)
  - retry_count: int
  - max_retries: int (기본값 3)
  - error_message: Optional[str]
  - created_at, started_at, completed_at: datetime
```

**생성 주체**: automation_sub (CSV 파싱 또는 이벤트 트리거)

#### 3.1.3 RenderOutput (렌더링 결과)
```python
RenderOutput:
  - id: int (PK)
  - instruction_id: int (FK → render_instructions)
  - output_path: str (NAS 최종 저장 경로)
  - file_size: int (바이트)
  - frame_count: Optional[int] (PNG 시퀀스인 경우)
  - status: RenderStatus (COMPLETED | FAILED)
  - error_message: Optional[str]
  - created_at, completed_at: datetime
```

**생성 주체**: automation_ae (렌더링 완료 시)

### 3.2 모니터링 & 오케스트레이션

#### 3.2.1 자동 감지 (Anomaly Detection)

**지연 감지**:
- RenderInstruction.status = 'pending' && created_at < now - 30분
- 액션: monitoring_events 생성 (severity=warning)

**고아 데이터 감지**:
- Hand.is_premium = true && RenderInstruction이 없음
- 액션: 자동 RenderInstruction 생성 또는 알림

**에러율 급증 감지**:
- failed 작업 비율 > 10% (1시간 윈도우)
- 액션: alert 이벤트 생성 + 관리자 알림

**처리율 하락 감지**:
- 현재 시간 처리율 < 이전 시간 처리율 × 0.5
- 액션: warning 이벤트 생성

#### 3.2.2 자동 결정 & 조치 (Auto-Remediation)

| 상황 | 자동 결정 | 효과 |
|------|---------|------|
| failed 작업 + retry_count < max_retries | 자동 재시도 | 복구율 ↑ |
| 우선순위 역전 | 우선순위 정렬 | 응답시간 ↓ |
| 장시간 처리 안됨 | 우선순위 상향 + 재시도 | 순환 대기 방지 |

#### 3.2.3 개입 가능 (Manual Override)

```
API: POST /api/actions/retry
  → 수동으로 failed 작업 재시도

API: POST /api/actions/change-priority
  → RenderInstruction 우선순위 변경

API: POST /api/actions/bulk-retry
  → 조건 기반 일괄 재시도 (created_after, status 등)

API: POST /api/actions/cancel
  → 작업 취소

API: POST /api/events/{id}/resolve
  → 모니터링 이벤트 해결 처리
```

### 3.3 API 명세

#### 3.3.1 대시보드 API
```
GET /api/dashboard
  응답: {
    projects: {
      feature_table: { status, last_activity, hands_today },
      sub: { status, instructions_created },
      ae: { status, worker_status, outputs_completed }
    },
    metrics: {
      throughput_1h,
      avg_latency_1h,
      error_rate_1h,
      queue_depth: { pending, processing }
    },
    active_alerts: [...],
    data_flow_health: { orphan_hands, delayed_instructions, completion_rate }
  }
```

#### 3.3.2 메트릭 API
```
GET /api/metrics/throughput?window=1h
GET /api/metrics/latency?window=1h
GET /api/metrics/error-rate?window=1h
GET /api/metrics/queue-depth
```

#### 3.3.3 데이터 흐름 API
```
GET /api/data-flow?hand_id=123
  응답: {
    hand: {...},
    instructions: [...],
    outputs: [...],
    status_chain: "Hand → RenderInstruction → RenderOutput"
  }
```

#### 3.3.4 관리자 개입 API
```
POST /api/actions/retry
  본문: { instruction_id: 123, reason: "..." }

POST /api/actions/change-priority
  본문: { instruction_id: 123, priority: 1, reason: "..." }

POST /api/actions/bulk-retry
  본문: {
    filter: { status: "failed", created_after: "2025-12-26T00:00:00Z" },
    reason: "..."
  }

POST /api/actions/cancel
  본문: { instruction_id: 123, reason: "..." }
```

#### 3.3.5 이벤트 관리 API
```
GET /api/events?severity=error&resolved=false
GET /api/events/{id}
POST /api/events/{id}/resolve
  본문: { resolved_by: "admin@", notes: "..." }
```

---

## 4. 기술 스택

### 4.1 현재 (v1.0)

| 계층 | 기술 | 비고 |
|------|------|------|
| **데이터베이스** | PostgreSQL 16 (asyncpg) | 유지 |
| **데이터 모델** | Pydantic v2 | 유지 |
| **비동기 런타임** | Python async/await | 유지 |
| **웹 프레임워크** | FastAPI | 유지 |
| **ORM** | SQLAlchemy (asyncio) | 유지 |
| **작업 분배** | DB Polling | ⚠️ 개선 필요 |
| **마이그레이션** | init-db.sql (수동) | ⚠️ 개선 필요 |
| **배경 작업** | APScheduler | 유지 |
| **실시간 통신** | N/A | ⚠️ 개선 필요 |
| **문서화** | OpenAPI (Swagger) | 유지 |

### 4.2 제안 (v2.0)

| 계층 | 기술 | 개선 효과 |
|------|------|---------|
| **데이터베이스** | PostgreSQL 16 + **Redis 7** | DB 부하 분산, 실시간 작업 분배 |
| **작업 분배** | **Redis Stream/Queue + arq** | Polling 제거, Latency 1초 이내 |
| **마이그레이션** | **Alembic** | 코드 기반 자동 마이그레이션 |
| **실시간 통신** | **WebSocket (FastAPI)** | 새로고침 없이 실시간 업데이트 |
| **인증** | **Basic Auth / API Key** | 대시보드 보안 강화 |

---

## 4A. 현재 아키텍처 분석 (AS-IS)

### 장점 (Pros)

| # | 장점 | 설명 |
|---|------|------|
| 1 | **명확한 관심사 분리** | `shared` 패키지로 3개 서비스가 동일 DTO/DB 로직 공유 |
| 2 | **비동기 처리 최적화** | async/await + asyncpg로 DB I/O 최적화 |
| 3 | **코드 품질 관리** | Pydantic v2 타입 검증 + Repository 패턴 캡슐화 |
| 4 | **확장성 대비** | docker-compose 컨테이너화 |

### 단점 및 위험 요소 (Cons)

| # | 단점 | 영향 | 심각도 |
|---|------|------|--------|
| 1 | **DB를 큐로 사용 (Polling)** | 규모 확대 시 DB 부하 증가, Latency 저하 | 높음 |
| 2 | **좀비 프로세스 처리 부재** | `processing` 상태 작업 영구 정체 (Stuck Job) | 높음 |
| 3 | **마이그레이션 관리 미흡** | 운영 환경 스키마 변경 시 데이터 손실 위험 | 중간 |
| 4 | **모니터링 인증 부재** | 대시보드 무단 접근 가능 | 중간 |
| 5 | **실시간성 부재** | API 호출(새로고침) 의존적 상태 확인 | 낮음 |

---

## 4B. 개선 제안 (To-Be Strategy)

### 개선 1: Redis 기반 Message Queue 도입

**문제**: DB Polling으로 인한 부하 및 지연

**솔루션**: Redis + arq (또는 Celery)를 도입하여 이벤트 기반 작업 분배

```
┌─────────────────────────────────────────────────────────────┐
│  현재 (v1.0): DB Polling                                    │
│  automation_sub → PostgreSQL (pending) ← automation_ae     │
│                   5초마다 polling                           │
├─────────────────────────────────────────────────────────────┤
│  제안 (v2.0): Redis Pub/Sub                                 │
│  automation_sub → PostgreSQL + Redis Stream                │
│                              ↓ 즉시 이벤트                  │
│                   automation_ae (Consumer)                  │
└─────────────────────────────────────────────────────────────┘
```

**docker-compose.yml 추가**:
```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - wsop-network
    restart: unless-stopped
```

**효과**:
- Latency: 5초 → 1초 이내
- DB 부하: 80% 감소 (Polling 제거)
- 확장성: Consumer Group으로 수평 확장 가능

---

### 개선 2: Zombie Hunter (Stuck Job Recovery)

**문제**: 렌더링 중 서버 크래시 시 `processing` 작업 영구 정체

**솔루션**: 주기적으로 타임아웃된 작업을 감지하고 복구

**새 Repository 메서드**:
```python
async def get_stuck_jobs(self, timeout_minutes: int = 10) -> list[RenderInstruction]:
    """processing 상태가 timeout_minutes 초과한 작업 조회"""
    query = """
    SELECT * FROM render_instructions
    WHERE status = 'processing'
      AND started_at < NOW() - INTERVAL ':timeout minutes'
    """
    return await self.db.execute(query, {"timeout": timeout_minutes})

async def reset_to_pending(self, instruction_id: int) -> bool:
    """작업을 pending으로 리셋하고 retry_count 증가"""
    query = """
    UPDATE render_instructions
    SET status = 'pending',
        retry_count = retry_count + 1,
        started_at = NULL
    WHERE id = :id AND retry_count < max_retries
    """
    return await self.db.execute_write(query, {"id": instruction_id})
```

**Reaper 프로세스 (APScheduler)**:
```python
@scheduler.scheduled_job('interval', minutes=1)
async def recover_stuck_jobs():
    repo = RenderInstructionsRepository(db)
    stuck_jobs = await repo.get_stuck_jobs(timeout_minutes=10)

    for job in stuck_jobs:
        if job.retry_count < job.max_retries:
            await repo.reset_to_pending(job.id)
            # Redis Queue에 재발행 (v2.0)
            logger.warning(f"Recovered stuck job: {job.id}")
        else:
            await repo.update_status(
                job.id,
                RenderStatus.FAILED,
                "Timeout and max retries exceeded"
            )
            logger.error(f"Job permanently failed: {job.id}")
```

**효과**:
- 작업 유실: 0%
- 자동 복구율: > 85%

---

### 개선 3: Alembic 마이그레이션 정식 도입

**문제**: init-db.sql 수동 관리로 인한 스키마 변경 위험

**솔루션**: Alembic을 통한 코드 기반 마이그레이션

**도입 단계**:
1. 기존 스키마를 Alembic 초기 버전으로 캡처
2. `shared/models` 변경 시 자동 감지: `alembic revision --autogenerate`
3. 컨테이너 시작 시 자동 적용: `alembic upgrade head`

**디렉토리 구조**:
```
automation_hub/
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
└── shared/
```

**효과**:
- 스키마 변경 추적 가능
- 롤백 지원
- 다운타임 최소화

---

### 개선 4: WebSocket 실시간 모니터링

**문제**: 대시보드 상태 확인이 API 호출(새로고침) 의존적

**솔루션**: FastAPI WebSocket + PostgreSQL LISTEN/NOTIFY (또는 Redis Pub/Sub)

**새 엔드포인트**:
```python
@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    await websocket.accept()

    # Redis Pub/Sub 또는 PostgreSQL LISTEN
    async for event in subscribe_events():
        await websocket.send_json({
            "type": event.type,  # "hand_created", "render_completed", etc.
            "data": event.data,
            "timestamp": event.timestamp
        })
```

**이벤트 트리거**:
- Hand 생성 시 → `hand_created` 이벤트
- RenderInstruction 상태 변경 시 → `instruction_updated` 이벤트
- RenderOutput 완료 시 → `render_completed` 이벤트

**효과**:
- 새로고침 없이 실시간 업데이트
- 운영자 응답 시간 단축

---

### 개선 5: 대시보드 보안 강화

**문제**: 모니터링 대시보드 인증 없음

**솔루션**: Basic Auth 또는 API Key 인증

**FastAPI 미들웨어**:
```python
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

@app.get("/api/dashboard")
async def get_dashboard(credentials: HTTPBasicCredentials = Depends(security)):
    if not verify_credentials(credentials):
        raise HTTPException(status_code=401)
    return await dashboard_service.get_stats()
```

**환경 변수**:
```env
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=secure_password_here
```

---

## 5. 아키텍처

### 5.1 계층 구조

```
┌─────────────────────────────────────────┐
│   Web API Layer (FastAPI)               │
│   - 대시보드, 메트릭, 관리자 개입       │
├─────────────────────────────────────────┤
│   Service Layer (비즈니스 로직)         │
│   - anomaly_detector.py                 │
│   - metrics_calculator.py               │
│   - health_checker.py                   │
│   - action_handler.py                   │
├─────────────────────────────────────────┤
│   Data Access Layer (Repository)        │
│   - HandsRepository                     │
│   - RenderInstructionsRepository        │
│   - RenderOutputsRepository             │
│   - EventRepository                     │
│   - MetricRepository                    │
├─────────────────────────────────────────┤
│   Database Layer (PostgreSQL)           │
│   - hands, tournaments, render_*        │
│   - monitoring_events, monitoring_*     │
└─────────────────────────────────────────┘
```

### 5.2 데이터 흐름

```
automation_feature_table
    ↓ Hand 저장
PostgreSQL (hands)
    ↓ event trigger (is_premium=true)

automation_sub
    ↓ RenderInstruction 생성
PostgreSQL (render_instructions, status=pending)
    ↓
automation_ae (InstructionPoller)
    ↓ 5초마다 polling
    ↓ RenderInstruction → Job 변환
    ↓ Celery 큐 추가

Celery Worker
    ↓ render_task 실행
    ↓ Nexrender 호출 → AE 렌더링

PostgreSQL (render_outputs)
    ↓
NAS (최종 저장소)
    ↓
Monitoring Dashboard
    ↓ 실시간 상태 표시
```

---

## 6. 구현 범위

### 6.1 Phase 1: 공유 모듈 (완료)
- ✅ Hand, RenderInstruction, RenderOutput 모델
- ✅ PostgreSQL 스키마
- ✅ Repository 패턴 (CRUD)

### 6.2 Phase 2: 데이터 흐름 통합 (예정)
- [ ] automation_ae: InstructionPoller 구현
- [ ] automation_sub: InstructionGenerator 구현
- [ ] automation_feature_table: automation_hub 동기화
- [ ] 테스트 및 통합

### 6.3 Phase 2.5: 안정성 개선 (v2.0 신규)

> gemini.md 분석 결과 반영

#### 6.3.1 Zombie Hunter 구현 (우선순위: 높음)
- [ ] `RenderInstructionsRepository.get_stuck_jobs()` 메서드 추가
- [ ] `RenderInstructionsRepository.reset_to_pending()` 메서드 추가
- [ ] APScheduler 기반 Reaper 프로세스 구현
- [ ] 타임아웃 임계값 설정 (기본 10분)
- [ ] 테스트 케이스 작성

#### 6.3.2 Alembic 마이그레이션 도입 (우선순위: 중간)
- [ ] `alembic init` 초기화
- [ ] 기존 스키마를 초기 마이그레이션으로 캡처
- [ ] SQLAlchemy ORM 모델과 동기화
- [ ] docker-compose에 `alembic upgrade head` 추가
- [ ] init-db.sql 제거

#### 6.3.3 대시보드 인증 추가 (우선순위: 중간)
- [ ] FastAPI HTTPBasic 미들웨어 구현
- [ ] 환경 변수 기반 인증 정보 관리
- [ ] 테스트 케이스 작성

### 6.4 Phase 3: 모니터링 & 오케스트레이션 (예정)
- [ ] DB 스키마 확장 (monitoring_events, metrics)
- [ ] 이상 감지 엔진
- [ ] 백그라운드 모니터링 워커
- [ ] API 엔드포인트 구현
- [ ] 대시보드 (React)

### 6.5 Phase 4: 실시간성 & 확장성 (v2.0 신규)

> gemini.md 분석 결과 반영

#### 6.5.1 Redis 메시지 큐 도입 (우선순위: 높음)
- [ ] Redis 7 컨테이너 추가 (docker-compose)
- [ ] Redis 연결 모듈 구현 (`shared/redis/connection.py`)
- [ ] arq 기반 작업 큐 구현
- [ ] DB Polling 로직을 Redis 이벤트 기반으로 대체
- [ ] Consumer Group 설정 (수평 확장 대비)

#### 6.5.2 WebSocket 실시간 업데이트 (우선순위: 중간)
- [ ] FastAPI WebSocket 엔드포인트 (`/ws/dashboard`)
- [ ] 이벤트 브로드캐스팅 로직
- [ ] PostgreSQL LISTEN/NOTIFY 또는 Redis Pub/Sub 연동
- [ ] 프론트엔드 WebSocket 클라이언트 구현

#### 6.5.3 RenderStatus 열거형 확장 (우선순위: 낮음)
- [ ] `STALE` 또는 `TIMED_OUT` 상태 추가
- [ ] 기존 코드 호환성 검토

---

## 7. 일정

| Phase | 설명 | 우선순위 | 상태 |
|-------|------|----------|------|
| 1 | 공유 모듈 | - | ✅ 완료 |
| 2 | 데이터 흐름 통합 | 필수 | 진행 중 |
| 2.5 | 안정성 개선 (v2.0) | 높음 | 예정 |
| 3 | 모니터링 & 오케스트레이션 | 필수 | 예정 |
| 4 | 실시간성 & 확장성 (v2.0) | 중간 | 예정 |

### 권장 구현 순서

```
Phase 1 (완료)
    ↓
Phase 2 (데이터 흐름)
    ↓
Phase 2.5 (Zombie Hunter → Alembic → 인증)  ← v2.0 추가
    ↓
Phase 3 (모니터링)
    ↓
Phase 4 (Redis → WebSocket)  ← v2.0 추가
```

> **Note**: Phase 2.5와 4는 기존 Phase와 병렬 진행 가능

---

## 8. 위험 요소 & 대응

### 8.1 기존 위험 요소

| 위험 | 영향 | 대응 |
|------|------|------|
| DB 성능 저하 | 모니터링 지연 | 인덱싱, 파티셔닝 |
| Polling 부하 증가 | automation_ae CPU 사용량 ↑ | **→ Redis 도입 (Phase 4)** |
| 이상 감지 오탐지 | 거짓 알림 폭증 | 임계값 튜닝, 학습 기간 확보 |
| 3개 프로젝트 버전 불일치 | 호환성 문제 | Semantic Versioning, 문서화 |

### 8.2 신규 식별 위험 (gemini.md 분석)

| 위험 | 영향 | 심각도 | 대응책 | Phase |
|------|------|--------|--------|-------|
| **Stuck Job (좀비 작업)** | 렌더링 서버 크래시 시 작업 영구 정체 | 높음 | Zombie Hunter 구현 | 2.5 |
| **스키마 마이그레이션 실패** | 운영 환경 데이터 손실 | 중간 | Alembic 도입 | 2.5 |
| **대시보드 무단 접근** | 보안 취약점 | 중간 | Basic Auth 추가 | 2.5 |
| **실시간성 부족** | 운영자 응답 지연 | 낮음 | WebSocket 도입 | 4 |
| **DB 큐 사용** | 규모 확대 시 병목 | 높음 | Redis Stream 도입 | 4 |

---

## 9. 비기능 요구사항 (v2.0 신규)

### 9.1 성능

| 지표 | 현재 (v1.0) | 목표 (v2.0) |
|------|------------|-------------|
| 모니터링 API 응답 시간 | N/A | < 200ms |
| 렌더링 작업 분배 Latency | 5초 (Polling) | < 1초 (Redis) |
| 동시 처리 가능 작업 수 | 제한 없음 | 100+ (Consumer Group) |

### 9.2 확장성

| 항목 | 요구사항 |
|------|---------|
| 수평 확장 | automation_ae 인스턴스 추가 시 작업 중복 할당 방지 |
| 클라이언트 호환성 | 기존 `shared` 라이브러리 사용 코드 변경 최소화 |

### 9.3 안정성

| 지표 | 목표값 |
|------|--------|
| Stuck Job 복구율 | > 85% |
| 작업 유실률 | 0% |
| 자동 재시도 성공률 | > 85% |

### 9.4 보안

| 항목 | 요구사항 |
|------|---------|
| 대시보드 인증 | Basic Auth 또는 API Key 필수 |
| 환경 변수 관리 | 민감 정보 .env 파일 분리 |

---

## 10. 성공 기준

프로젝트 완료는 다음 조건을 만족할 때:

### 10.1 필수 (MVP)
- [x] Phase 1 완료 (공유 모듈)
- [ ] Phase 2 완료 (데이터 흐름 통합)
  - [ ] automation_ae InstructionPoller 구현 + 테스트
  - [ ] automation_sub InstructionGenerator 구현 + 테스트
  - [ ] automation_feature_table 동기화 구현 + 테스트
  - [ ] 엔드 투 엔드 흐름 검증
- [ ] Phase 3 완료 (모니터링 & 오케스트레이션)
  - [ ] 모니터링 API 모두 구현
  - [ ] 이상 감지 엔진 구현
  - [ ] 관리자 개입 API 테스트 완료
  - [ ] 대시보드 UI 구현 (React)

### 10.2 안정성 개선 (v2.0)
- [ ] Phase 2.5 완료
  - [ ] Zombie Hunter 구현 및 테스트
  - [ ] Alembic 마이그레이션 도입
  - [ ] 대시보드 인증 추가

### 10.3 실시간성 & 확장성 (v2.0)
- [ ] Phase 4 완료
  - [ ] Redis 메시지 큐 도입
  - [ ] WebSocket 실시간 업데이트
  - [ ] Consumer Group 수평 확장 검증

### 10.4 품질 지표
- [ ] 통합 테스트 통과율 > 95%
- [ ] 모니터링 API 응답 시간 < 200ms
- [ ] Stuck Job 복구율 > 85%
- [ ] 렌더링 Latency < 1초 (Phase 4 완료 시)

---

## 11. 참고 문서

### 공유 모듈
- `D:\AI\claude01\automation_hub\CLAUDE.md`
- `D:\AI\claude01\automation_hub\README.md`
- `D:\AI\claude01\automation_hub\shared\models\`
- `D:\AI\claude01\automation_hub\shared\db\`

### 외부 프로젝트
- PRD-0001: automation_feature_table
- PRD-WSOP-Sub: automation_sub
- PRD-WSOP-AE: automation_ae

### v2.0 분석 문서
- `D:\AI\claude01\automation_hub\gemini.md` - 아키텍처 분석 및 개선 제안 (Gemini AI)

---

**문서 작성**: 2025-12-26
**v2.0 업데이트**: 2025-12-26 (gemini.md 분석 반영)
**최종 검토**: -
**승인**: -
