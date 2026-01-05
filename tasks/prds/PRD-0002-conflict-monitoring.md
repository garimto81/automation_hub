# PRD-0002: 충돌/중복 모니터링 시스템

## 문서 정보

| 항목 | 내용 |
|------|------|
| **PRD ID** | PRD-0002 |
| **제목** | 충돌/중복 모니터링 시스템 (Conflict & Duplication Monitor) |
| **버전** | 1.0.0 |
| **작성일** | 2025-01-05 |
| **상태** | Draft |
| **우선순위** | P1 |
| **관련 PRD** | PRD-0001 (automation_hub v2.0) |

---

## Executive Summary

### 배경

automation_hub는 3개 프로젝트(feature_table, sub, ae)의 **공유 인프라**입니다. 현재 데이터 충돌과 중복에 대한 **사후 감지 및 알림 체계가 부재**하여, 문제 발생 시 수동으로 발견해야 합니다.

### 핵심 역할

이 시스템은 **작업을 지시하지 않고**, 각 프로젝트 간 **충돌지점과 중복 지점만 모니터링**합니다:

```
┌─────────────────────────────────────────────────────────────┐
│                    automation_hub                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Conflict Monitor (본 PRD)                │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐               │   │
│  │  │  Hand   │  │ Render  │  │ Concur  │   → GitHub    │   │
│  │  │  Dup    │  │  Dup    │  │ Conflict│     Issues    │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘               │   │
│  │       └───────────┴───────────┘                      │   │
│  │                    ↓                                  │   │
│  │              5분 주기 스캔                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  PostgreSQL ←── feature_table, sub, ae ──→ 데이터 저장      │
└─────────────────────────────────────────────────────────────┘
```

### 목표

| 목표 | 현재 | 목표 |
|------|------|------|
| 중복 데이터 감지율 | 0% (수동 발견) | 100% (자동 감지) |
| 충돌 알림 시간 | 수시간~수일 | < 10분 |
| 이슈 등록 | 수동 | 자동 (GitHub Issues) |

---

## 1. 문제 정의 & 배경

### 1.1 현재 상황

| 프로젝트 | 데이터 유형 | 충돌 가능성 |
|----------|------------|------------|
| feature_table | Hand (RFID) | 동일 테이블+핸드 번호 중복 저장 시도 |
| sub | RenderInstruction | 동일 trigger_id로 중복 렌더링 요청 |
| ae | RenderOutput | 여러 인스턴스가 동일 작업 동시 처리 |

### 1.2 문제점

| # | 문제 | 영향 | 심각도 |
|---|------|------|--------|
| 1 | **Hand 중복 감지 부재** | UNIQUE 제약으로 INSERT 실패만 발생, 알림 없음 | 중간 |
| 2 | **RenderInstruction 중복** | 동일 trigger_id로 여러 렌더링 생성 가능 | 높음 |
| 3 | **동시 처리 충돌** | ae 수평 확장 시 작업 중복 할당 | 높음 |
| 4 | **사후 분석 어려움** | 충돌 이력 미보관 | 중간 |

### 1.3 제약 조건

- **작업 지시 금지**: 이 시스템은 모니터링만 수행 (orchestrator가 아님)
- **기존 스키마 유지**: hands, render_instructions 테이블 변경 최소화
- **PRD-0001과 독립**: Redis 도입 전에도 동작 가능 (DB Polling 기반)

---

## 2. 목표 & 성공 지표

### 2.1 핵심 목표

| # | 목표 | 상세 |
|---|------|------|
| 1 | **중복 감지** | Hand, RenderInstruction 중복 100% 자동 감지 |
| 2 | **충돌 감지** | 동시 처리 충돌 (racing condition) 감지 |
| 3 | **자동 이슈 등록** | 감지 시 GitHub Issues에 자동 등록 |
| 4 | **이력 보관** | 충돌 이벤트 DB 저장 (분석용) |

### 2.2 성공 지표

| 지표 | 현재 | 목표 |
|------|------|------|
| 중복 감지율 | 0% | 100% |
| 충돌 알림 지연 | N/A (수동) | < 10분 (5분 주기 + 처리) |
| GitHub Issue 자동 생성율 | 0% | 100% |
| False Positive 비율 | N/A | < 5% |

---

## 3. 아키텍처

### 3.1 시스템 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    Conflict Monitor                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ HandDuplicate│    │ RenderDup    │    │ Concurrency  │   │
│  │ Detector     │    │ Detector     │    │ Detector     │   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘   │
│         │                   │                   │            │
│         └───────────────────┴───────────────────┘            │
│                             │                                │
│                             ▼                                │
│                    ┌────────────────┐                       │
│                    │ ConflictEvent  │                       │
│                    │ Aggregator     │                       │
│                    └────────┬───────┘                       │
│                             │                                │
│              ┌──────────────┼──────────────┐                │
│              ▼              ▼              ▼                │
│     ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│     │ PostgreSQL │  │ GitHub     │  │ Dashboard  │         │
│     │ (events)   │  │ Issues     │  │ WebSocket  │         │
│     └────────────┘  └────────────┘  └────────────┘         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 감지 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    5분 주기 스케줄러                          │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Hand 중복 스캔                                            │
│    SELECT table_id, hand_number, COUNT(*)                   │
│    FROM hands                                                │
│    WHERE created_at > NOW() - INTERVAL '10 minutes'         │
│    GROUP BY table_id, hand_number                           │
│    HAVING COUNT(*) > 1                                       │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. RenderInstruction 중복 스캔                               │
│    SELECT trigger_id, COUNT(*)                              │
│    FROM render_instructions                                  │
│    WHERE created_at > NOW() - INTERVAL '10 minutes'         │
│      AND trigger_id IS NOT NULL                             │
│    GROUP BY trigger_id                                       │
│    HAVING COUNT(*) > 1                                       │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 동시 처리 충돌 스캔                                       │
│    SELECT id, started_at                                    │
│    FROM render_instructions                                  │
│    WHERE status = 'processing'                              │
│    GROUP BY template_name, trigger_id                       │
│    HAVING COUNT(*) > 1                                       │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 이벤트 생성 & 발행                                        │
│    - conflict_events 테이블 INSERT                          │
│    - GitHub Issue 생성 (gh api)                             │
│    - WebSocket 브로드캐스트 (optional)                       │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 데이터 모델

#### conflict_events 테이블 (신규)

```sql
CREATE TABLE conflict_events (
    id SERIAL PRIMARY KEY,

    -- 이벤트 정보
    event_type VARCHAR(50) NOT NULL,  -- hand_duplicate, render_duplicate, concurrency_conflict
    severity VARCHAR(20) NOT NULL,     -- info, warning, error, critical

    -- 충돌 상세
    conflict_key VARCHAR(200) NOT NULL, -- 예: "table_1:hand_42", "trigger:premium_hand:123"
    affected_ids INTEGER[] NOT NULL,    -- 충돌에 관련된 레코드 ID 목록
    details_json JSONB,                 -- 추가 상세 정보

    -- 해결 상태
    status VARCHAR(20) DEFAULT 'open', -- open, acknowledged, resolved, ignored
    resolution_notes TEXT,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),

    -- GitHub 연동
    github_issue_number INTEGER,
    github_issue_url VARCHAR(500),

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_conflict_events_type ON conflict_events(event_type);
CREATE INDEX idx_conflict_events_status ON conflict_events(status);
CREATE INDEX idx_conflict_events_created ON conflict_events(created_at DESC);
CREATE INDEX idx_conflict_events_key ON conflict_events(conflict_key);
```

#### ConflictEvent 모델 (Pydantic)

```python
class ConflictType(str, Enum):
    HAND_DUPLICATE = "hand_duplicate"
    RENDER_DUPLICATE = "render_duplicate"
    CONCURRENCY_CONFLICT = "concurrency_conflict"

class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ConflictStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    IGNORED = "ignored"

class ConflictEvent(BaseModel):
    id: Optional[int] = None
    event_type: ConflictType
    severity: Severity
    conflict_key: str
    affected_ids: list[int]
    details: dict = Field(default_factory=dict)
    status: ConflictStatus = ConflictStatus.OPEN
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    github_issue_number: Optional[int] = None
    github_issue_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
```

---

## 4. 기능 요구사항

### 4.1 Hand 중복 감지

#### 4.1.1 감지 조건

| 조건 | 설명 |
|------|------|
| UNIQUE 제약 위반 | `(table_id, hand_number)` 중복 INSERT 시도 |
| 시간 기반 중복 | 10분 내 동일 키로 여러 레코드 생성 |

#### 4.1.2 구현

```python
class HandDuplicateDetector:
    async def scan(self, lookback_minutes: int = 10) -> list[ConflictEvent]:
        query = """
            SELECT table_id, hand_number,
                   array_agg(id) as ids,
                   array_agg(source) as sources,
                   COUNT(*) as count
            FROM hands
            WHERE created_at > NOW() - INTERVAL ':minutes minutes'
            GROUP BY table_id, hand_number
            HAVING COUNT(*) > 1
        """
        results = await self.db.execute(query, {"minutes": lookback_minutes})

        events = []
        for row in results:
            events.append(ConflictEvent(
                event_type=ConflictType.HAND_DUPLICATE,
                severity=Severity.WARNING,
                conflict_key=f"{row['table_id']}:{row['hand_number']}",
                affected_ids=row['ids'],
                details={
                    "table_id": row['table_id'],
                    "hand_number": row['hand_number'],
                    "sources": row['sources'],
                    "duplicate_count": row['count']
                }
            ))
        return events
```

### 4.2 RenderInstruction 중복 감지

#### 4.2.1 감지 조건

| 조건 | 설명 |
|------|------|
| trigger_id 중복 | 동일 trigger_id로 여러 렌더링 요청 |
| template + trigger 중복 | 동일 템플릿 + 동일 트리거로 중복 생성 |

#### 4.2.2 구현

```python
class RenderDuplicateDetector:
    async def scan(self, lookback_minutes: int = 10) -> list[ConflictEvent]:
        query = """
            SELECT trigger_type, trigger_id, template_name,
                   array_agg(id) as ids,
                   array_agg(status) as statuses,
                   COUNT(*) as count
            FROM render_instructions
            WHERE created_at > NOW() - INTERVAL ':minutes minutes'
              AND trigger_id IS NOT NULL
            GROUP BY trigger_type, trigger_id, template_name
            HAVING COUNT(*) > 1
        """
        results = await self.db.execute(query, {"minutes": lookback_minutes})

        events = []
        for row in results:
            # 모두 완료된 경우 심각도 낮춤
            all_completed = all(s == 'completed' for s in row['statuses'])
            severity = Severity.INFO if all_completed else Severity.ERROR

            events.append(ConflictEvent(
                event_type=ConflictType.RENDER_DUPLICATE,
                severity=severity,
                conflict_key=f"{row['trigger_type']}:{row['trigger_id']}",
                affected_ids=row['ids'],
                details={
                    "trigger_type": row['trigger_type'],
                    "trigger_id": row['trigger_id'],
                    "template_name": row['template_name'],
                    "statuses": row['statuses'],
                    "duplicate_count": row['count']
                }
            ))
        return events
```

### 4.3 동시 처리 충돌 감지

#### 4.3.1 감지 조건

| 조건 | 설명 |
|------|------|
| 동시 processing | 동일 작업이 여러 인스턴스에서 동시에 processing |
| 중복 할당 | Consumer Group 없이 같은 작업 중복 할당 |

#### 4.3.2 구현

```python
class ConcurrencyConflictDetector:
    async def scan(self) -> list[ConflictEvent]:
        query = """
            SELECT template_name, trigger_id,
                   array_agg(id) as ids,
                   array_agg(started_at) as started_times,
                   COUNT(*) as count
            FROM render_instructions
            WHERE status = 'processing'
              AND trigger_id IS NOT NULL
            GROUP BY template_name, trigger_id
            HAVING COUNT(*) > 1
        """
        results = await self.db.execute(query)

        events = []
        for row in results:
            events.append(ConflictEvent(
                event_type=ConflictType.CONCURRENCY_CONFLICT,
                severity=Severity.CRITICAL,
                conflict_key=f"concurrent:{row['template_name']}:{row['trigger_id']}",
                affected_ids=row['ids'],
                details={
                    "template_name": row['template_name'],
                    "trigger_id": row['trigger_id'],
                    "started_times": [str(t) for t in row['started_times']],
                    "concurrent_count": row['count']
                }
            ))
        return events
```

### 4.4 GitHub Issue 자동 등록

#### 4.4.1 Issue 생성 로직

```python
class GitHubIssueCreator:
    def __init__(self, repo: str = "garimto81/claude"):
        self.repo = repo

    async def create_issue(self, event: ConflictEvent) -> tuple[int, str]:
        """GitHub Issue 생성 후 (issue_number, url) 반환"""

        title = self._generate_title(event)
        body = self._generate_body(event)
        labels = self._get_labels(event)

        # gh CLI 사용
        cmd = f"""
            gh issue create \
                --repo {self.repo} \
                --title "{title}" \
                --body "{body}" \
                --label "{','.join(labels)}"
        """
        result = await asyncio.create_subprocess_shell(cmd, ...)

        # issue URL 파싱
        issue_url = result.stdout.strip()
        issue_number = int(issue_url.split('/')[-1])

        return issue_number, issue_url

    def _generate_title(self, event: ConflictEvent) -> str:
        type_names = {
            ConflictType.HAND_DUPLICATE: "Hand 중복",
            ConflictType.RENDER_DUPLICATE: "렌더링 중복",
            ConflictType.CONCURRENCY_CONFLICT: "동시 처리 충돌"
        }
        return f"[{event.severity.value.upper()}] {type_names[event.event_type]}: {event.conflict_key}"

    def _generate_body(self, event: ConflictEvent) -> str:
        return f"""
## 충돌 정보

| 항목 | 값 |
|------|---|
| **이벤트 유형** | {event.event_type.value} |
| **심각도** | {event.severity.value} |
| **충돌 키** | `{event.conflict_key}` |
| **영향 받은 ID** | {event.affected_ids} |
| **감지 시각** | {event.created_at} |

## 상세 정보

```json
{json.dumps(event.details, indent=2, ensure_ascii=False)}
```

## 조치 필요

- [ ] 원인 분석
- [ ] 중복 데이터 정리
- [ ] 재발 방지 조치

---
*자동 생성됨 by automation_hub Conflict Monitor*
        """

    def _get_labels(self, event: ConflictEvent) -> list[str]:
        labels = ["conflict-monitor", "automated"]

        severity_labels = {
            Severity.INFO: "priority:low",
            Severity.WARNING: "priority:medium",
            Severity.ERROR: "priority:high",
            Severity.CRITICAL: "priority:critical"
        }
        labels.append(severity_labels[event.severity])

        type_labels = {
            ConflictType.HAND_DUPLICATE: "type:duplicate",
            ConflictType.RENDER_DUPLICATE: "type:duplicate",
            ConflictType.CONCURRENCY_CONFLICT: "type:concurrency"
        }
        labels.append(type_labels[event.event_type])

        return labels
```

### 4.5 스케줄러

#### 4.5.1 5분 주기 실행

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class ConflictMonitorScheduler:
    def __init__(self, db: Database, github_repo: str):
        self.db = db
        self.hand_detector = HandDuplicateDetector(db)
        self.render_detector = RenderDuplicateDetector(db)
        self.concurrency_detector = ConcurrencyConflictDetector(db)
        self.issue_creator = GitHubIssueCreator(github_repo)
        self.events_repo = ConflictEventsRepository(db)

        self.scheduler = AsyncIOScheduler()

    def start(self):
        self.scheduler.add_job(
            self.scan_all,
            'interval',
            minutes=5,
            id='conflict_scan'
        )
        self.scheduler.start()

    async def scan_all(self):
        """모든 감지기 실행"""
        all_events = []

        # 병렬 스캔
        hand_events, render_events, concurrency_events = await asyncio.gather(
            self.hand_detector.scan(),
            self.render_detector.scan(),
            self.concurrency_detector.scan()
        )

        all_events.extend(hand_events)
        all_events.extend(render_events)
        all_events.extend(concurrency_events)

        # 중복 이벤트 필터링 (이미 등록된 conflict_key)
        new_events = await self._filter_existing(all_events)

        # 이벤트 처리
        for event in new_events:
            # DB 저장
            event_id = await self.events_repo.insert(event)
            event.id = event_id

            # GitHub Issue 생성
            if event.severity in (Severity.WARNING, Severity.ERROR, Severity.CRITICAL):
                issue_number, issue_url = await self.issue_creator.create_issue(event)
                await self.events_repo.update_github_info(event_id, issue_number, issue_url)

            logger.info(f"Conflict detected: {event.event_type} - {event.conflict_key}")

    async def _filter_existing(self, events: list[ConflictEvent]) -> list[ConflictEvent]:
        """최근 24시간 내 동일 conflict_key 이벤트 필터링"""
        existing_keys = await self.events_repo.get_recent_keys(hours=24)
        return [e for e in events if e.conflict_key not in existing_keys]
```

---

## 5. API 엔드포인트

### 5.1 이벤트 조회

```python
@app.get("/api/conflicts")
async def list_conflicts(
    status: Optional[ConflictStatus] = None,
    event_type: Optional[ConflictType] = None,
    severity: Optional[Severity] = None,
    limit: int = 50,
    offset: int = 0
) -> list[ConflictEvent]:
    """충돌 이벤트 목록 조회"""
    pass

@app.get("/api/conflicts/{event_id}")
async def get_conflict(event_id: int) -> ConflictEvent:
    """충돌 이벤트 상세 조회"""
    pass
```

### 5.2 이벤트 상태 관리

```python
@app.post("/api/conflicts/{event_id}/acknowledge")
async def acknowledge_conflict(event_id: int) -> ConflictEvent:
    """이벤트 확인 처리"""
    pass

@app.post("/api/conflicts/{event_id}/resolve")
async def resolve_conflict(
    event_id: int,
    resolution_notes: str,
    resolved_by: str
) -> ConflictEvent:
    """이벤트 해결 처리"""
    pass

@app.post("/api/conflicts/{event_id}/ignore")
async def ignore_conflict(event_id: int) -> ConflictEvent:
    """이벤트 무시 처리"""
    pass
```

### 5.3 통계

```python
@app.get("/api/conflicts/stats")
async def get_conflict_stats() -> dict:
    """충돌 통계"""
    return {
        "total": 42,
        "by_status": {"open": 5, "resolved": 35, "ignored": 2},
        "by_type": {"hand_duplicate": 10, "render_duplicate": 25, "concurrency_conflict": 7},
        "by_severity": {"info": 5, "warning": 20, "error": 15, "critical": 2},
        "trend_7days": [...]
    }
```

### 5.4 수동 스캔 트리거

```python
@app.post("/api/conflicts/scan")
async def trigger_scan() -> dict:
    """수동 스캔 실행"""
    events = await scheduler.scan_all()
    return {"scanned_at": datetime.now(), "new_events": len(events)}
```

---

## 6. 비기능 요구사항

### 6.1 성능

| 지표 | 요구사항 |
|------|---------|
| 스캔 소요 시간 | < 10초 (5분 주기에서 부하 없음) |
| API 응답 시간 | < 200ms |
| DB 쿼리 최적화 | 인덱스 활용, 시간 범위 제한 |

### 6.2 안정성

| 항목 | 요구사항 |
|------|---------|
| 스캔 실패 복구 | 다음 주기에서 자동 재시도 |
| GitHub API 실패 | 로컬 저장 후 나중에 재시도 |
| DB 연결 실패 | 재연결 로직 + 알림 |

### 6.3 보안

| 항목 | 요구사항 |
|------|---------|
| GitHub 토큰 | 환경 변수로 관리 (GITHUB_TOKEN) |
| API 인증 | PRD-0001의 Basic Auth와 통합 |

---

## 7. 환경 변수

```env
# 기존 (PRD-0001)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=wsop_automation

# 충돌 모니터링 (신규)
CONFLICT_SCAN_INTERVAL_MINUTES=5
CONFLICT_LOOKBACK_MINUTES=10
CONFLICT_GITHUB_REPO=garimto81/claude
GITHUB_TOKEN=ghp_xxx...

# 알림 필터
CONFLICT_MIN_SEVERITY=warning  # info, warning, error, critical
```

---

## 8. 구현 로드맵

### Phase 1: 기반 구축

- [ ] `conflict_events` 테이블 생성 (init-db.sql 업데이트)
- [ ] `ConflictEvent` Pydantic 모델 구현
- [ ] `ConflictEventsRepository` 구현

### Phase 2: 감지기 구현

- [ ] `HandDuplicateDetector` 구현
- [ ] `RenderDuplicateDetector` 구현
- [ ] `ConcurrencyConflictDetector` 구현
- [ ] 단위 테스트 작성

### Phase 3: 이슈 연동

- [ ] `GitHubIssueCreator` 구현
- [ ] Issue 템플릿 작성
- [ ] 라벨 자동 생성

### Phase 4: 스케줄러 & API

- [ ] `ConflictMonitorScheduler` 구현
- [ ] REST API 엔드포인트 구현
- [ ] 통합 테스트

### Phase 5: 대시보드 연동 (선택)

- [ ] WebSocket 이벤트 브로드캐스트
- [ ] 대시보드 UI에 충돌 패널 추가

---

## 9. 위험 관리

| # | 위험 | 영향 | 대응책 |
|---|------|------|--------|
| 1 | GitHub API Rate Limit | Issue 생성 실패 | 큐잉 후 재시도 |
| 2 | False Positive 과다 | 노이즈 증가 | 시간 범위 조정, 필터 추가 |
| 3 | 스캔 부하 | DB 성능 저하 | 인덱스 최적화, 시간 제한 |

---

## 10. 성공 기준

### 10.1 필수 (MVP)

- [ ] Phase 1~3 완료
- [ ] 3가지 충돌 유형 모두 감지
- [ ] GitHub Issue 자동 생성
- [ ] 단위 테스트 커버리지 > 80%

### 10.2 권장

- [ ] Phase 4~5 완료
- [ ] 대시보드 통합
- [ ] False Positive < 5%

---

## 11. 참고 문서

### 내부 문서

- `PRD-0001-automation-hub-v2.md` - 상위 PRD
- `shared/models/` - 기존 데이터 모델
- `shared/db/repositories.py` - Repository 패턴

### 외부 참고

- [GitHub CLI - Issue 관리](https://cli.github.com/manual/gh_issue_create)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)

---

**작성**: 2025-01-05
**검토**: -
**승인**: -
