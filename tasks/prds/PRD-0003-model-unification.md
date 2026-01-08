# PRD-0003: 프로젝트 간 모델 통합

## 문서 정보

| 항목 | 내용 |
|------|------|
| **PRD ID** | PRD-0003 |
| **제목** | 프로젝트 간 모델 통합 (Cross-Project Model Unification) |
| **버전** | 1.0.0 |
| **작성일** | 2026-01-05 |
| **상태** | Draft |
| **우선순위** | P0 |
| **관련 PRD** | PRD-0001 (automation_hub v2.0), PRD-0002 (충돌 모니터링) |

---

## Executive Summary

### 배경

automation_hub는 3개 프로젝트(feature_table, ae, sub)의 **공유 인프라**로 설계되었으나, 현재 각 프로젝트가 **독자적인 데이터 모델**을 운영하여 통합 효과가 발휘되지 않고 있습니다.

### 현재 문제

```
automation_hub (shared 모듈)
├── shared/models/hand.py          ← 미사용
├── shared/models/render_instruction.py  ← 미사용
└── shared/db/repositories.py      ← 미사용

automation_feature_table
└── src/models/hand.py             ← 독자적 모델 (HandResult, FusedHandResult)
    src/database/models.py         ← 독자적 ORM

automation_ae
└── backend/app/models/job.py      ← 독자적 모델 (Job, Template, Output)
    별도 ae_automation DB

automation_sub
└── (코드 없음, PRD 문서만 존재)
```

### 목표

| 목표 | 현재 | 목표 |
|------|------|------|
| shared 모듈 사용률 | 0% | 100% |
| 데이터 모델 통일률 | 0% | 100% |
| 하위 호환성 유지율 | N/A | 100% |
| 마이그레이션 데이터 손실률 | N/A | 0% |

---

## 1. 문제 정의 & 배경

### 1.1 현재 모델 구조

#### automation_hub (공유 모델 - 미사용)

```python
# shared/models/hand.py
class Hand(BaseModel):
    id: int
    table_id: str
    hand_number: int
    source: SourceType  # RFID | CSV | MANUAL
    hand_rank: HandRank
    pot_size: int
    winner: str
    players_json: dict
    community_cards_json: list
    actions_json: list

# shared/models/render_instruction.py
class RenderInstruction(BaseModel):
    id: int
    template_name: str
    layer_data_json: dict
    output_settings_json: dict
    status: RenderStatus  # PENDING | PROCESSING | COMPLETED | FAILED
    trigger_type: str
    trigger_id: str
```

#### automation_feature_table (독자적 모델)

```python
# src/models/hand.py
class SourceType(Enum):
    PRIMARY = "pokergfx"      # ← hub와 다름! (RFID vs pokergfx)
    SECONDARY = "ai_video"    # ← hub에 없음
    FUSED = "fused"           # ← hub에 없음
    MANUAL = "manual"

class HandResult(dataclass):
    table_id: str
    hand_number: int
    hand_rank: HandRank
    rank_value: int
    confidence: float = 1.0   # ← hub에 없음
    players_showdown: list[dict]
    pot_size: int

class FusedHandResult(dataclass):
    primary_result: HandResult | None
    secondary_result: AIVideoResult | None
    cross_validated: bool     # ← hub에 없음
    requires_review: bool     # ← hub에 없음

# src/database/models.py (SQLAlchemy ORM)
class Hand(Base):
    # 추가 관계
    recordings: list[Recording]  # ← hub에 없음
    grade: Grade                 # ← hub에 없음
    manual_marks: list[ManualMark]  # ← hub에 없음
```

#### automation_ae (독자적 모델)

```python
# backend/app/models/job.py
class Job(Base):
    id: int
    template_id: int          # ← FK, hub는 template_name (직접 값)
    status: JobStatus         # ← hub의 RenderStatus와 동일 값
    progress: int             # ← hub에 없음
    data: dict                # ← hub는 layer_data_json
    data_selections: list     # ← hub에 없음
    output_format: OutputFormat  # ← hub는 output_settings_json

# backend/app/models/template.py
class Template(Base):         # ← hub에 없음
    id: int
    name: str
    file_path: str
    layers: dict
```

### 1.2 불일치 분석

| 항목 | automation_hub | automation_feature_table | automation_ae |
|------|---------------|-------------------------|---------------|
| **Hand 소스 타입** | RFID, CSV, MANUAL | PRIMARY, SECONDARY, FUSED, MANUAL | N/A |
| **Hand 신뢰도** | 없음 | confidence (0.0~1.0) | N/A |
| **Hand 검증 상태** | 없음 | cross_validated, requires_review | N/A |
| **Recording** | 없음 | Recording 테이블 존재 | N/A |
| **Grade** | 없음 | Grade 테이블 (A/B/C) 존재 | N/A |
| **Template** | template_name (문자열) | N/A | Template 테이블 (FK) |
| **렌더 데이터** | layer_data_json | N/A | data (JSON) |
| **진행률** | 없음 | N/A | progress (0~100) |

### 1.3 영향도 분석

| 영향 | 설명 | 심각도 |
|------|------|--------|
| **데이터 파편화** | 동일 Hand 데이터가 여러 DB에 분산 | 높음 |
| **모니터링 불가** | PRD-0002 충돌 감지가 불완전 | 높음 |
| **코드 중복** | 유사 로직이 각 프로젝트에 중복 구현 | 중간 |
| **유지보수 비용** | 스키마 변경 시 3곳 동시 수정 필요 | 중간 |
| **테스트 복잡도** | 통합 테스트 환경 구성 어려움 | 낮음 |

---

## 2. 목표 & 성공 지표

### 2.1 핵심 목표

| # | 목표 | 상세 |
|---|------|------|
| 1 | **단일 진실 소스** | automation_hub/shared가 유일한 모델 정의 |
| 2 | **하위 호환성** | 기존 코드 최소 변경으로 마이그레이션 |
| 3 | **확장된 스키마** | Recording, Grade, Template 등 누락 모델 추가 |
| 4 | **어댑터 패턴** | SourceType 등 열거형 값 자동 매핑 |

### 2.2 성공 지표

| 지표 | 현재 | 목표 |
|------|------|------|
| shared 모듈 사용률 | 0% | 100% |
| 모델 정의 중복 | 3곳 | 1곳 (hub만) |
| 통합 DB 사용 | 3개 DB | 1개 DB (wsop_automation) |
| 마이그레이션 데이터 손실 | N/A | 0% |
| 하위 호환성 깨짐 | N/A | 0건 |

---

## 3. 통합 아키텍처

### 3.1 AS-IS vs TO-BE 모델 비교

![AS-IS TO-BE 모델 비교](../../docs/images/prd-0003-model-comparison.png)

> HTML 원본: [prd-0003-model-comparison.html](../../docs/mockups/prd-0003-model-comparison.html)

<details>
<summary>텍스트 다이어그램 (접기/펼치기)</summary>

#### AS-IS (현재)

```
┌─────────────────────────────────────────────────────────────────┐
│ automation_hub                                                   │
│ └── shared/models/ (미사용)                                      │
│     ├── Hand (기본)                                              │
│     └── RenderInstruction (기본)                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ automation_feature_table                                         │
│ └── src/models/ (독자적)                                         │
│     ├── HandResult, FusedHandResult                             │
│     ├── AIVideoResult                                           │
│     └── Recording, Grade (ORM)                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ automation_ae                                                    │
│ └── backend/app/models/ (독자적)                                 │
│     ├── Job, Output                                             │
│     ├── Template                                                │
│     └── DataType, DataRecord                                    │
└─────────────────────────────────────────────────────────────────┘
```

#### TO-BE (목표)

```
┌─────────────────────────────────────────────────────────────────┐
│ automation_hub                                                   │
│ └── shared/models/ (확장, 단일 진실 소스)                         │
│     ├── Hand (확장: confidence, cross_validated, requires_review)│
│     ├── Recording, Grade (신규)                                  │
│     ├── RenderInstruction (확장: progress)                       │
│     ├── RenderOutput (기존)                                      │
│     └── Template (신규: ae에서 이전)                             │
└─────────────────────────────────────────────────────────────────┘
        ↑                           ↑
        │ import                    │ import
┌───────┴───────────────┐  ┌───────┴───────────────┐
│ automation_feature_table │ │ automation_ae         │
│ └── adapters/           │  │ └── adapters/          │
│     hub_adapter.py      │  │     hub_adapter.py     │
│     (FusedHandResult    │  │     (Job → Render      │
│      → Hand 변환)       │  │      Instruction 변환) │
└─────────────────────────┘  └─────────────────────────┘
```

</details>

### 3.2 통합 스키마 설계

#### SourceType 통합 (확장)

```python
class SourceType(str, Enum):
    """통합 소스 타입"""
    RFID = "rfid"           # feature_table PRIMARY
    AI_VIDEO = "ai_video"   # feature_table SECONDARY (신규)
    CSV = "csv"             # sub 등에서 사용
    MANUAL = "manual"       # 공통

    # 하위 호환성 별칭
    @classmethod
    def from_legacy(cls, value: str) -> "SourceType":
        legacy_map = {
            "pokergfx": cls.RFID,
            "primary": cls.RFID,
            "secondary": cls.AI_VIDEO,
            "fused": cls.RFID,  # fused는 primary 기반
        }
        return legacy_map.get(value.lower(), cls(value))
```

#### Hand 모델 확장

```python
class Hand(BaseModel):
    # 기존 필드
    id: int | None = None
    table_id: str
    hand_number: int
    source: SourceType
    hand_rank: HandRank | None = None
    pot_size: int | None = None
    winner: str | None = None
    players_json: dict = Field(default_factory=dict)
    community_cards_json: list = Field(default_factory=list)
    actions_json: list = Field(default_factory=list)
    duration_seconds: int | None = None

    # 신규 필드 (feature_table에서 이전)
    confidence: float = 1.0
    cross_validated: bool = False
    requires_review: bool = False

    # 신규 필드 (fusion 정보)
    primary_source_id: int | None = None  # 원본 RFID Hand ID
    secondary_source_id: int | None = None  # AI Video 결과 ID

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = None
```

#### Recording 모델 (신규)

```python
class Recording(BaseModel):
    """Hand 녹화 정보 (feature_table에서 이전)"""
    id: int | None = None
    hand_id: int
    file_path: str
    file_name: str | None = None
    file_size_bytes: int | None = None
    duration_seconds: int | None = None
    vmix_input_number: int | None = None
    vmix_recording_id: str | None = None
    status: str = "completed"  # recording, completed, failed
    recording_started_at: datetime | None = None
    recording_ended_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)
```

#### Grade 모델 (신규)

```python
class GradeLevel(str, Enum):
    A = "A"  # 방송 우선 사용
    B = "B"  # 방송 사용 가능
    C = "C"  # 방송 미사용

class Grade(BaseModel):
    """Hand 등급 정보 (feature_table에서 이전)"""
    id: int | None = None
    hand_id: int
    grade: GradeLevel

    # 등급 판정 조건
    has_premium_hand: bool = False
    has_long_playtime: bool = False
    has_premium_board_combo: bool = False

    broadcast_eligible: bool = False
    suggested_edit_start_offset: int | None = None
    edit_start_confidence: float | None = None

    graded_by: str = "auto"  # auto, manual
    graded_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
```

#### Template 모델 (신규)

```python
class Template(BaseModel):
    """AE 템플릿 정보 (ae에서 이전)"""
    id: int | None = None
    name: str
    description: str | None = None
    file_path: str
    composition: str | None = None
    layers_json: dict = Field(default_factory=dict)
    thumbnail_path: str | None = None
    duration_seconds: float | None = None
    fps: int | None = None
    width: int | None = None
    height: int | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = None
```

#### RenderInstruction 확장

```python
class RenderInstruction(BaseModel):
    # 기존 필드 (유지)
    id: int | None = None
    template_name: str
    layer_data_json: dict = Field(default_factory=dict)
    output_settings_json: dict = Field(default_factory=dict)
    output_path: str | None = None
    output_filename: str | None = None
    status: RenderStatus = RenderStatus.PENDING
    priority: int = 5
    trigger_type: str | None = None
    trigger_id: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    max_retries: int = 3

    # 신규 필드 (ae에서 이전)
    progress: int = 0  # 0~100
    template_id: int | None = None  # FK to Template
    data_selections_json: list | None = None  # ae의 data_selections

    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
```

### 3.3 하위 호환성 레이어

```python
# shared/adapters/legacy.py

class LegacyAdapter:
    """기존 코드와의 호환성 유지"""

    @staticmethod
    def from_fused_hand_result(fused: "FusedHandResult") -> Hand:
        """feature_table FusedHandResult → shared Hand 변환"""
        source_map = {
            "pokergfx": SourceType.RFID,
            "primary": SourceType.RFID,
            "secondary": SourceType.AI_VIDEO,
            "fused": SourceType.RFID,
            "manual": SourceType.MANUAL,
        }

        return Hand(
            table_id=fused.table_id,
            hand_number=fused.hand_number,
            source=source_map.get(fused.source.value, SourceType.RFID),
            hand_rank=fused.hand_rank,
            confidence=fused.confidence,
            cross_validated=fused.cross_validated,
            requires_review=fused.requires_review,
            # ... 나머지 필드 매핑
        )

    @staticmethod
    def from_ae_job(job: "Job", template: "Template") -> RenderInstruction:
        """ae Job → shared RenderInstruction 변환"""
        return RenderInstruction(
            template_name=template.name,
            template_id=template.id,
            layer_data_json=job.data,
            progress=job.progress,
            status=RenderStatus(job.status.value),
            data_selections_json=job.data_selections,
            # ... 나머지 필드 매핑
        )
```

---

## 4. 기능 요구사항

### 4.1 shared/models 확장

| 모델 | 변경 유형 | 상세 |
|------|----------|------|
| Hand | 확장 | confidence, cross_validated, requires_review, primary/secondary_source_id |
| Recording | 신규 | hand_id FK, 녹화 파일 정보 |
| Grade | 신규 | hand_id FK, A/B/C 등급, 판정 조건 |
| Template | 신규 | AE 템플릿 메타데이터 |
| RenderInstruction | 확장 | progress, template_id FK, data_selections_json |
| SourceType | 확장 | AI_VIDEO 추가, from_legacy() 메서드 |

### 4.2 shared/db 확장

```python
# shared/db/repositories.py

class RecordingsRepository:
    async def insert(self, recording: Recording) -> int: ...
    async def get_by_hand_id(self, hand_id: int) -> list[Recording]: ...
    async def update_status(self, id: int, status: str) -> None: ...

class GradesRepository:
    async def insert(self, grade: Grade) -> int: ...
    async def get_by_hand_id(self, hand_id: int) -> Grade | None: ...
    async def update_grade(self, hand_id: int, grade: GradeLevel) -> None: ...

class TemplatesRepository:
    async def insert(self, template: Template) -> int: ...
    async def get_by_name(self, name: str) -> Template | None: ...
    async def get_by_id(self, id: int) -> Template | None: ...
    async def list_all(self) -> list[Template]: ...
    async def update(self, id: int, **fields) -> None: ...
```

### 4.3 스키마 업데이트 (init-db.sql)

```sql
-- recordings 테이블 (신규)
CREATE TABLE IF NOT EXISTS recordings (
    id SERIAL PRIMARY KEY,
    hand_id INTEGER REFERENCES hands(id) ON DELETE CASCADE,
    file_path VARCHAR(500) NOT NULL,
    file_name VARCHAR(255),
    file_size_bytes INTEGER,
    duration_seconds INTEGER,
    vmix_input_number INTEGER,
    vmix_recording_id VARCHAR(100),
    status VARCHAR(50) DEFAULT 'completed',
    recording_started_at TIMESTAMP,
    recording_ended_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_recordings_hand_id ON recordings(hand_id);

-- grades 테이블 (신규)
CREATE TABLE IF NOT EXISTS grades (
    id SERIAL PRIMARY KEY,
    hand_id INTEGER UNIQUE REFERENCES hands(id) ON DELETE CASCADE,
    grade VARCHAR(1) NOT NULL CHECK (grade IN ('A', 'B', 'C')),
    has_premium_hand BOOLEAN DEFAULT false,
    has_long_playtime BOOLEAN DEFAULT false,
    has_premium_board_combo BOOLEAN DEFAULT false,
    broadcast_eligible BOOLEAN DEFAULT false,
    suggested_edit_start_offset INTEGER,
    edit_start_confidence FLOAT,
    graded_by VARCHAR(50) DEFAULT 'auto',
    graded_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_grades_hand_id ON grades(hand_id);
CREATE INDEX idx_grades_grade ON grades(grade);

-- templates 테이블 (신규)
CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    composition VARCHAR(100),
    layers_json JSONB,
    thumbnail_path VARCHAR(500),
    duration_seconds FLOAT,
    fps INTEGER,
    width INTEGER,
    height INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_templates_name ON templates(name);

-- hands 테이블 확장 (ALTER)
ALTER TABLE hands ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 1.0;
ALTER TABLE hands ADD COLUMN IF NOT EXISTS cross_validated BOOLEAN DEFAULT false;
ALTER TABLE hands ADD COLUMN IF NOT EXISTS requires_review BOOLEAN DEFAULT false;
ALTER TABLE hands ADD COLUMN IF NOT EXISTS primary_source_id INTEGER;
ALTER TABLE hands ADD COLUMN IF NOT EXISTS secondary_source_id INTEGER;

-- render_instructions 테이블 확장 (ALTER)
ALTER TABLE render_instructions ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0;
ALTER TABLE render_instructions ADD COLUMN IF NOT EXISTS template_id INTEGER REFERENCES templates(id);
ALTER TABLE render_instructions ADD COLUMN IF NOT EXISTS data_selections_json JSONB;
```

---

## 5. 마이그레이션 전략

### 5.1 Phase별 마이그레이션

![마이그레이션 흐름](../../docs/images/prd-0003-migration-flow.png)

> HTML 원본: [prd-0003-migration-flow.html](../../docs/mockups/prd-0003-migration-flow.html)

#### Phase 1: 스키마 확장

```
1. automation_hub/scripts/init-db.sql 업데이트
2. shared/models/ 확장
3. shared/db/repositories.py 신규 Repository 추가
4. 단위 테스트 작성
```

#### Phase 2: feature_table 통합

```
1. adapters/hub_adapter.py 생성
2. FusedHandResult → Hand 변환 로직
3. Recording, Grade 저장 로직 변경
4. 기존 feature_table DB → wsop_automation 마이그레이션
5. 통합 테스트
```

#### Phase 3: ae 통합

```
1. backend/app/adapters/hub_adapter.py 생성
2. Job → RenderInstruction 변환 로직
3. Template 저장 로직 변경
4. 기존 ae_automation DB → wsop_automation 마이그레이션
5. 통합 테스트
```

#### Phase 4: 검증 및 정리

```
1. 데이터 무결성 검증
2. 성능 테스트
3. 문서 업데이트
4. 구버전 코드 정리 (Deprecation)
```

### 5.2 롤백 계획

| Phase | 롤백 방법 |
|-------|----------|
| Phase 1 | ALTER TABLE DROP COLUMN (스키마 원복) |
| Phase 2 | feature_table의 어댑터 비활성화, 자체 DB 재사용 |
| Phase 3 | ae의 어댑터 비활성화, ae_automation DB 재사용 |
| Phase 4 | N/A (정리 단계) |

### 5.3 데이터 검증

```sql
-- 마이그레이션 후 검증 쿼리

-- 1. Hand 개수 일치 확인
SELECT
    (SELECT COUNT(*) FROM hands) as hub_count,
    -- feature_table 원본과 비교

-- 2. Recording 연결 확인
SELECT h.id, h.hand_number, COUNT(r.id) as recording_count
FROM hands h
LEFT JOIN recordings r ON h.id = r.hand_id
GROUP BY h.id, h.hand_number;

-- 3. Grade 연결 확인
SELECT h.id, h.hand_number, g.grade
FROM hands h
LEFT JOIN grades g ON h.id = g.hand_id
WHERE g.id IS NULL;  -- Grade 누락 확인

-- 4. RenderInstruction-Template 연결 확인
SELECT ri.id, ri.template_name, t.id as template_id
FROM render_instructions ri
LEFT JOIN templates t ON ri.template_id = t.id
WHERE ri.template_id IS NOT NULL AND t.id IS NULL;
```

---

## 6. 구현 로드맵

### Phase 1: 스키마 확장 (1주)

| # | 작업 | 파일 |
|---|------|------|
| 1 | SourceType 확장 (AI_VIDEO, from_legacy) | shared/models/hand.py |
| 2 | Hand 모델 확장 | shared/models/hand.py |
| 3 | Recording 모델 신규 | shared/models/recording.py |
| 4 | Grade 모델 신규 | shared/models/grade.py |
| 5 | Template 모델 신규 | shared/models/template.py |
| 6 | RenderInstruction 확장 | shared/models/render_instruction.py |
| 7 | 신규 Repository 추가 | shared/db/repositories.py |
| 8 | init-db.sql 업데이트 | scripts/init-db.sql |
| 9 | 단위 테스트 | tests/test_models.py |

### Phase 2: feature_table 통합 (1주)

| # | 작업 | 파일 |
|---|------|------|
| 1 | 어댑터 레이어 생성 | feature_table/adapters/hub_adapter.py |
| 2 | FusedHandResult → Hand 변환 | 어댑터 |
| 3 | Recording 저장 로직 변경 | src/recording/manager.py |
| 4 | Grade 저장 로직 변경 | src/grading/grader.py |
| 5 | 데이터 마이그레이션 스크립트 | scripts/migrate_feature_table.py |
| 6 | 통합 테스트 | tests/integration/ |

### Phase 3: ae 통합 (1주)

| # | 작업 | 파일 |
|---|------|------|
| 1 | 어댑터 레이어 생성 | ae/backend/app/adapters/hub_adapter.py |
| 2 | Job → RenderInstruction 변환 | 어댑터 |
| 3 | Template 저장 로직 변경 | services/template_parser.py |
| 4 | Output → RenderOutput 변환 | 어댑터 |
| 5 | 데이터 마이그레이션 스크립트 | scripts/migrate_ae.py |
| 6 | 통합 테스트 | tests/integration/ |

### Phase 4: 검증 및 정리 (1주)

| # | 작업 | 파일 |
|---|------|------|
| 1 | 데이터 무결성 검증 | scripts/verify_migration.sql |
| 2 | 성능 테스트 | tests/performance/ |
| 3 | CLAUDE.md 업데이트 | 각 프로젝트 |
| 4 | Deprecation 완료 | 구버전 코드 제거 |

---

## 7. 위험 관리

| # | 위험 | 영향 | 심각도 | 대응책 |
|---|------|------|--------|--------|
| 1 | 마이그레이션 중 데이터 손실 | 운영 장애 | 높음 | 백업 + 롤백 계획 |
| 2 | 하위 호환성 깨짐 | 기존 코드 오류 | 높음 | 어댑터 패턴 + 점진적 이전 |
| 3 | 스키마 변경 실패 | DB 불일치 | 중간 | Alembic 도입 (PRD-0001) |
| 4 | 성능 저하 | 응답 지연 | 중간 | 인덱스 최적화 |
| 5 | 테스트 누락 | 숨겨진 버그 | 중간 | 커버리지 80% 이상 |

---

## 8. 성공 기준

### 8.1 필수 (MVP)

- [ ] Phase 1~2 완료
- [ ] feature_table이 shared 모듈 사용
- [ ] 기존 기능 정상 동작
- [ ] 단위 테스트 커버리지 > 80%

### 8.2 권장 (Full)

- [ ] Phase 3~4 완료
- [ ] ae가 shared 모듈 사용
- [ ] 단일 wsop_automation DB 운영
- [ ] Deprecation 완료

### 8.3 품질 체크리스트

- [ ] 모든 모델 타입 힌트 완료
- [ ] Repository 패턴 일관성
- [ ] 마이그레이션 롤백 테스트
- [ ] 문서 최신화

---

## 9. 참고 문서

### 시각화 자료

| 다이어그램 | 이미지 | HTML 원본 |
|-----------|--------|-----------|
| AS-IS/TO-BE 모델 비교 | [PNG](../../docs/images/prd-0003-model-comparison.png) | [HTML](../../docs/mockups/prd-0003-model-comparison.html) |
| 마이그레이션 흐름도 | [PNG](../../docs/images/prd-0003-migration-flow.png) | [HTML](../../docs/mockups/prd-0003-migration-flow.html) |
| SourceType 매핑 | [PNG](../../docs/images/prd-0003-sourcetype-mapping.png) | [HTML](../../docs/mockups/prd-0003-sourcetype-mapping.html) |

### 내부 문서

- `PRD-0001-automation-hub-v2.md` - 상위 PRD (Redis, Zombie Hunter)
- `PRD-0002-conflict-monitoring.md` - 충돌 모니터링
- `shared/models/` - 기존 모델 정의
- `shared/db/repositories.py` - Repository 패턴

### 외부 프로젝트

- `C:\claude\automation_feature_table` - RFID 처리
- `C:\claude\automation_ae` - AE 렌더링
- `C:\claude\automation_sub` - 문서 저장소

---

**작성**: 2026-01-05
**검토**: -
**승인**: -
