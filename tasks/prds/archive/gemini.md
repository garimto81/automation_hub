제공해주신 `automation_hub` 프로젝트의 파일들을 기반으로 현재 아키텍처를 분석하고, 최신 기술 트렌드를 반영하여 장단점 분석 및 개선된 PRD(제품 요구사항 정의서)를 작성해 드리겠습니다.

---

# 1. 현황 분석 및 아키텍처 리뷰

### **1.1 현재 기술 스택 분석 (AS-IS)**

제공된 `pyproject.toml` 및 소스 코드를 통해 확인된 기술 스택은 다음과 같습니다.

* **Language:** Python 3.11 (최신 안정 버전군에 속함, 3.12/3.13으로 마이그레이션 용이)
* **Web Framework:** FastAPI (모니터링용)
* **Database:** PostgreSQL 16 (최신 메이저 버전)
* **ORM/Driver:** SQLAlchemy 2.0+ (Async), asyncpg (비동기 처리의 표준)
* **Data Validation:** Pydantic V2 (최신 표준, `model_dump` 사용 확인됨)
* **Architecture:** Shared Database Pattern (공유 데이터베이스 패턴) + Polling Consumer

### **1.2 장점 (Pros)**

1. **명확한 관심사 분리 (Shared Module):** `shared` 패키지를 통해 여러 마이크로서비스(`feature_table`, `sub`, `ae`)가 동일한 데이터 모델(DTO)과 DB 로직을 공유하여 정합성을 보장하고 있습니다.
2. **비동기 처리 최적화:** `async/await`, `asyncpg`, `SQLAlchemy AsyncSession`을 사용하여 DB I/O 바운드 작업에서 높은 성능을 기대할 수 있습니다.
3. **코드 품질 관리:** Pydantic V2를 활용한 엄격한 타입 검증과 `Repository Pattern`을 통한 DB 접근 로직의 캡슐화가 잘 되어 있습니다.
4. **확장성 대비:** `docker-compose`를 통한 컨테이너화가 되어 있어 배포가 용이합니다.

### **1.3 단점 및 위험 요소 (Cons)**

1. **DB를 큐(Queue)로 사용 (Polling 방식):**
* `RenderInstructionsRepository.get_pending`을 `automation_ae`가 주기적으로 폴링하는 구조입니다. 트래픽이 적을 땐 괜찮지만, 규모가 커지면 DB 부하가 증가하고 실시간성(Latency)이 떨어집니다.


2. **좀비 프로세스 처리 부재:**
* 렌더링 중(`processing`)인 작업이 AE 서버의 크래시로 인해 멈출 경우, 해당 작업은 영원히 `processing` 상태로 남아 재시도되지 않는 "Stuck Job" 문제가 발생할 수 있습니다.


3. **마이그레이션 관리 미흡:**
* `alembic`이 의존성에는 있지만, 실제 DB 초기화는 `scripts/init-db.sql`에 의존하고 있습니다. 운영 환경에서 스키마 변경 시 데이터 손실 위험이 있습니다.


4. **보안 및 모니터링:**
* 모니터링 대시보드(`/pending`, `/stats`)에 인증 절차가 없습니다.
* 실시간 상태 확인이 API 호출(새로고침)에 의존적입니다 (WebSocket 부재).



---

# 2. 개선 제안 (To-Be Strategy)

최신 백엔드 트렌드(Event-Driven Architecture)를 반영한 단계별 개선안입니다.

### **개선 1: Message Queue 도입 (Redis)**

* **제안:** DB 폴링 대신 **Redis**와 가벼운 비동기 작업 큐인 **ARQ** 또는 **Celery**를 도입합니다.
* **효과:** `automation_sub`가 작업을 생성하면 즉시 큐에 넣고, `automation_ae`가 이를 소비합니다. DB는 "상태 기록용"으로만 사용하고 "작업 분배용"으로는 사용하지 않아 부하를 줄입니다.

### **개선 2: Dead Letter Queue 및 Timeout 로직**

* **제안:** `started_at`을 기준으로 일정 시간(예: 10분)이 지나도 완료되지 않은 작업을 감지하여 `pending`으로 되돌리거나 `failed`로 처리하는 **Reaper(수확기)** 프로세스를 추가합니다.

### **개선 3: Alembic 정식 도입**

* **제안:** `init-db.sql`을 제거하고, 코드 기반(`SQLAlchemy` 모델)에서 DB 스키마를 자동 생성 및 관리하도록 `Alembic` 마이그레이션 스크립트를 작성합니다.

### **개선 4: 실시간 모니터링 (WebSocket)**

* **제안:** FastAPI의 `WebSocket`을 활용하여 클라이언트(운영자)가 새로고침 없이 렌더링 진행 상황과 핸드 데이터를 실시간으로 볼 수 있게 합니다.

---

# 3. 개선된 제품 요구사항 정의서 (PRD)

**Project Name:** WSOP Automation Hub v2.0 (Reliability Update)

## 1. 개요 (Overview)

본 프로젝트는 WSOP 방송 자동화 시스템의 중추 역할을 하는 `automation_hub`의 안정성, 실시간성, 유지보수성을 강화하기 위한 버전 2.0 업데이트입니다. 기존의 공유 DB 패턴을 유지하되, 메시지 큐 시스템을 도입하여 처리 지연을 최소화하고 장애 복구 능력을 확보합니다.

## 2. 목표 (Goals)

* **Latency 감소:** 렌더링 지시 생성부터 작업 시작까지의 지연 시간을 1초 이내로 단축.
* **안정성 확보:** 렌더링 서버 장애 시 중단된 작업을 자동으로 감지하고 복구하는 메커니즘 구축.
* **운영 효율화:** 실시간 대시보드 제공 및 스키마 변경 자동화.

## 3. 기능 요구사항 (Functional Requirements)

### 3.1 렌더링 작업 관리 (Queue Management) [신규/개선]

* **Redis 기반 작업 큐:**
* `RenderInstruction` 생성 시 DB 저장 후 즉시 Redis Stream/Queue에 Job ID 발행.
* `automation_ae`는 Redis를 구독(Subscribe)하여 즉시 작업 시작.


* **Failover (장애 복구):**
* 주기적(예: 1분)으로 `processing` 상태인 작업 중 `started_at`이 임계치(예: 10분)를 초과한 작업을 조회.
* 해당 작업의 `retry_count`를 확인하여 재시도 가능 시 `pending`으로 롤백 및 관리자 알림 발송.



### 3.2 데이터베이스 관리 (Schema Migration) [개선]

* **Alembic 도입:**
* `shared/models`의 변경 사항을 감지하여 마이그레이션 파일 자동 생성 (`alembic revision --autogenerate`).
* 컨테이너 구동 시 `alembic upgrade head` 자동 실행.



### 3.3 실시간 모니터링 대시보드 [개선]

* **WebSocket Endpoint (`/ws/dashboard`):**
* DB에 새로운 `Hand`나 `RenderOutput`이 저장될 때마다 연결된 클라이언트에 JSON 데이터 브로드캐스팅.
* PostgreSQL의 `LISTEN/NOTIFY` 기능이나 Redis Pub/Sub을 활용하여 구현.


* **보안:**
* 대시보드 접속 시 Basic Auth 또는 API Key 인증 추가.



### 3.4 데이터 무결성 강화 [유지/강화]

* **중복 방지:** `hands` 테이블의 `(table_id, hand_number)` 유니크 제약 조건을 엄격히 유지.
* **트랜잭션:** 렌더링 지시 생성과 큐 발행은 원자적(Atomic)으로 처리되거나, 'Outbox Pattern'을 고려(선택적).

## 4. 비기능 요구사항 (Non-Functional Requirements)

* **성능:** 모니터링 API 응답 속도 200ms 이내.
* **확장성:** 렌더링 서버(`automation_ae`)를 수평 확장(Scale-out) 해도 작업이 중복 할당되지 않아야 함 (Redis Consumer Group 활용).
* **호환성:** 기존 `shared` 라이브러리를 사용하는 클라이언트 코드의 변경을 최소화.

## 5. 시스템 아키텍처 및 기술 스택 (Tech Stack Update)

| 구분 | 기존 (v1.0) | **제안 (v2.0)** | 비고 |
| --- | --- | --- | --- |
| **언어** | Python 3.11 | **Python 3.11+** | 유지 |
| **DB** | PostgreSQL 16 | **PostgreSQL 16 + Redis 7** | Redis 추가 (Queue/Cache) |
| **ORM** | SQLAlchemy (Async) | SQLAlchemy (Async) | 유지 |
| **Migration** | init-db.sql (수동) | **Alembic** | 자동화 도구 적용 |
| **Job Queue** | DB Polling | **Redis (arq or Celery)** | Polling 제거 |
| **Real-time** | N/A | **WebSocket (FastAPI)** | 실시간성 확보 |

## 6. 구현 상세 가이드 (Implementation Guide)

### 6.1 `shared/models/render_instruction.py` 수정 제안

상태 관리를 더 명확히 하기 위해 `RenderStatus`에 `STALE` 혹은 `TIMED_OUT`을 추가하는 것을 고려합니다.

### 6.2 Redis 도입을 위한 `docker-compose.yml` 수정

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
    # ... 기존 서비스들 설정 ...
    # monitor 및 ae 서비스에 REDIS_URL 환경변수 추가

```

### 6.3 Zombie Hunter (Stuck Job Recovery) 로직 예시

`monitor` 서비스 내부 혹은 별도의 스케줄러에서 실행:

```python
async def recover_stuck_jobs(repo: RenderInstructionsRepository, timeout_minutes: int = 10):
    # 10분 이상 processing 상태인 작업 조회
    stuck_jobs = await repo.get_stuck_jobs(timeout_minutes)
    for job in stuck_jobs:
        if job.retry_count < job.max_retries:
            await repo.reset_to_pending(job.id)
            # Redis Queue에 다시 push
        else:
            await repo.update_status(job.id, RenderStatus.FAILED, "Timeout and max retries exceeded")

```

이 PRD는 기존 시스템의 장점인 "공유 모듈을 통한 데이터 일관성"을 유지하면서, 단점인 "DB 폴링 부하"와 "장애 복구 미비"를 해결하는 데 초점을 맞추었습니다.