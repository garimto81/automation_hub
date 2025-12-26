# PRD-0000: WSOP 방송 자동화 통합 허브 (automation_hub)

## 문서 정보

| 항목 | 내용 |
|------|------|
| **PRD ID** | PRD-0000 |
| **제목** | WSOP 방송 자동화 통합 허브 (automation_hub) |
| **부제** | 3개 프로젝트 공유 인프라 + Level 3 오케스트레이션 |
| **버전** | 1.0 |
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

| 계층 | 기술 |
|------|------|
| **데이터베이스** | PostgreSQL 16 (asyncpg) |
| **데이터 모델** | Pydantic v2 |
| **비동기 런타임** | Python async/await |
| **웹 프레임워크** | FastAPI |
| **ORM** | SQLAlchemy (asyncio) |
| **메시지 큐** | Redis (선택적) |
| **배경 작업** | APScheduler (모니터링 워커) |
| **문서화** | OpenAPI (Swagger) |

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

### 6.3 Phase 3: 모니터링 & 오케스트레이션 (예정)
- [ ] DB 스키마 확장 (monitoring_events, metrics)
- [ ] 이상 감지 엔진
- [ ] 백그라운드 모니터링 워커
- [ ] API 엔드포인트 구현
- [ ] 대시보드 (React)

---

## 7. 일정

| Phase | 기간 | 시간 | 상태 |
|-------|------|------|------|
| 1 | 2025-12-23 ~ 12-25 | 4시간 | ✅ 완료 |
| 2 | 2025-12-26 ~ 2026-01-10 | 14시간 | 진행 중 |
| 3 | 2026-01-13 ~ 2026-01-31 | 12시간 | 예정 |
| **총합** | **5주** | **30시간** | - |

---

## 8. 위험 요소 & 대응

| 위험 | 영향 | 대응 |
|------|------|------|
| DB 성능 저하 | 모니터링 지연 | 인덱싱, 파티셔닝 |
| Polling 부하 증가 | automation_ae CPU 사용량 ↑ | 배치 크기 조정, 주기 변경 |
| 이상 감지 오탐지 | 거짓 알림 폭증 | 임계값 튜닝, 학습 기간 확보 |
| 3개 프로젝트 버전 불일치 | 호환성 문제 | Semantic Versioning, 문서화 |

---

## 9. 성공 기준

프로젝트 완료는 다음 조건을 만족할 때:

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
- [ ] 통합 테스트 통과율 > 95%
- [ ] 성능 지표 달성 (응답시간, 정확도 등)

---

## 10. 참고 문서

### 공유 모듈
- `D:\AI\claude01\automation_hub\CLAUDE.md`
- `D:\AI\claude01\automation_hub\README.md`
- `D:\AI\claude01\automation_hub\shared\models\`
- `D:\AI\claude01\automation_hub\shared\db\`

### 외부 프로젝트
- PRD-0001: automation_feature_table
- PRD-WSOP-Sub: automation_sub
- PRD-WSOP-AE: automation_ae

---

**문서 작성**: 2025-12-26
**최종 검토**: -
**승인**: -
