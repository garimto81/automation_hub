# WSOP Automation Hub - Database Schema Design

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Supabase PostgreSQL                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────┐    ┌─────────────────┐    ┌──────────────────┐  │
│   │   hands     │    │   tournaments   │    │ render_outputs   │  │
│   │  (RFID/CSV) │    │   (CSV 파싱)    │    │   (AE 결과)      │  │
│   └─────────────┘    └─────────────────┘    └────────┬─────────┘  │
│         ▲                                            │             │
│         │                                            │ FK          │
│   ┌─────┴─────┐                              ┌───────▼─────────┐  │
│   │ feature   │                              │ render_         │  │
│   │ _table    │                              │ instructions    │  │
│   │ (polling) │                              │ (sub → ae)      │  │
│   └───────────┘                              └─────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ENUM Types

| Type | Values | Usage |
|------|--------|-------|
| `source_type` | rfid, csv, manual | hands.source |
| `hand_rank` | royal_flush ~ high_card (10종) | hands.hand_rank |
| `render_status` | pending, processing, completed, failed | render_*.status |
| `output_format` | png_sequence, mov_alpha, mp4 | output_settings_json.format |
| `event_type` | HOLDEM, PLO, PLO8, RAZZ, STUD, HORSE, MIXED | tournaments.event_type |

---

## Tables

### 1. hands

**포커 핸드 데이터** - feature_table(RFID), sub(CSV), 수작업에서 수집

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | PK |
| table_id | VARCHAR(50) | 테이블 식별자 |
| hand_number | INTEGER | 핸드 번호 |
| source | source_type | 데이터 소스 |
| hand_rank | hand_rank | 핸드 랭킹 (optional) |
| pot_size | INTEGER | 팟 사이즈 |
| winner | VARCHAR(100) | 승자 이름 |
| players_json | JSONB | 플레이어 정보 배열 |
| community_cards_json | JSONB | 커뮤니티 카드 배열 |
| actions_json | JSONB | 베팅 액션 배열 |
| duration_seconds | INTEGER | 핸드 소요 시간 |
| created_at | TIMESTAMPTZ | 생성 시각 |
| updated_at | TIMESTAMPTZ | 수정 시각 |

**Unique**: (table_id, hand_number)

**Indexes**:
- `idx_hands_table_id` - 테이블별 조회
- `idx_hands_hand_rank` - 랭킹별 조회 (부분 인덱스)
- `idx_hands_premium` - 프리미엄 핸드 조회 (Full House 이상)
- `idx_hands_players_gin` - 플레이어 검색 (GIN)

### 2. tournaments

**토너먼트 정보** - WSOP+ CSV에서 파싱

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | PK |
| name | VARCHAR(200) | 토너먼트 이름 |
| event_code | VARCHAR(50) | 이벤트 코드 (UNIQUE) |
| event_type | event_type | 이벤트 타입 |
| buy_in | INTEGER | 바이인 금액 |
| prize_pool | BIGINT | 총 상금 |
| total_entries | INTEGER | 총 참가자 수 |
| remaining_players | INTEGER | 남은 플레이어 수 |
| current_level | INTEGER | 현재 블라인드 레벨 |
| blinds_json | JSONB | 블라인드 구조 배열 |
| current_blinds_json | JSONB | 현재 블라인드 정보 |
| payouts_json | JSONB | 상금 배분 구조 |
| places_paid | INTEGER | 입상 인원 |
| standings_json | JSONB | 순위 정보 배열 |
| start_date | TIMESTAMPTZ | 시작 일시 |
| end_date | TIMESTAMPTZ | 종료 일시 |
| source | VARCHAR(20) | 데이터 소스 |
| created_at | TIMESTAMPTZ | 생성 시각 |
| updated_at | TIMESTAMPTZ | 수정 시각 |

**Indexes**:
- `idx_tournaments_event_code` - 코드별 조회
- `idx_tournaments_active` - 활성 토너먼트 (remaining > 0)

### 3. render_instructions

**렌더링 지시서** - sub가 생성, ae가 polling 후 처리

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | PK |
| template_name | VARCHAR(100) | AE 템플릿 이름 |
| layer_data_json | JSONB | 레이어 데이터 |
| output_settings_json | JSONB | 출력 설정 |
| output_path | VARCHAR(500) | 출력 경로 |
| output_filename | VARCHAR(200) | 출력 파일명 |
| status | render_status | 상태 |
| priority | INTEGER | 우선순위 (1-10) |
| trigger_type | VARCHAR(50) | 트리거 타입 |
| trigger_id | VARCHAR(100) | 트리거 ID |
| error_message | TEXT | 에러 메시지 |
| retry_count | INTEGER | 재시도 횟수 |
| max_retries | INTEGER | 최대 재시도 |
| created_at | TIMESTAMPTZ | 생성 시각 |
| started_at | TIMESTAMPTZ | 시작 시각 |
| completed_at | TIMESTAMPTZ | 완료 시각 |

**Indexes**:
- `idx_render_instructions_pending_poll` - Pending 작업 polling (핵심)
- `idx_render_instructions_trigger` - 트리거 기반 조회

### 4. render_outputs

**렌더링 결과** - ae가 완료 후 저장

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | PK |
| instruction_id | BIGINT | FK → render_instructions |
| output_path | VARCHAR(500) | 실제 저장 경로 |
| file_size | BIGINT | 파일 크기 (bytes) |
| frame_count | INTEGER | 프레임 수 (PNG sequence) |
| status | render_status | 상태 |
| error_message | TEXT | 에러 메시지 |
| created_at | TIMESTAMPTZ | 생성 시각 |
| completed_at | TIMESTAMPTZ | 완료 시각 |

**FK**: instruction_id → render_instructions(id) ON DELETE CASCADE

---

## Views

| View | Description |
|------|-------------|
| `v_premium_hands` | 프리미엄 핸드 (Full House 이상), 랭킹순 정렬 |
| `v_pending_renders` | 대기 중 렌더링 작업, 우선순위순 정렬 |
| `v_active_tournaments` | 활성 토너먼트 (remaining_players > 0) |

---

## Triggers

| Trigger | Table | Description |
|---------|-------|-------------|
| `tr_hands_updated_at` | hands | updated_at 자동 갱신 |
| `tr_tournaments_updated_at` | tournaments | updated_at 자동 갱신 |
| `tr_render_instructions_started` | render_instructions | processing 전환 시 started_at 설정 |
| `tr_render_instructions_completed` | render_instructions | completed/failed 전환 시 completed_at 설정 |

---

## RLS Policies

| Policy | Role | Access |
|--------|------|--------|
| Service role full access | service_role | ALL (CRUD) |
| Authenticated read access | authenticated | SELECT only |

> 모든 테이블에 RLS 활성화됨. 서버 간 통신은 service_role 키 사용.

---

## Realtime

다음 테이블에 Supabase Realtime 활성화:
- `hands` - 새 핸드 실시간 알림
- `render_instructions` - 렌더링 상태 실시간 모니터링

---

## JSONB Schemas

### players_json (hands)

```json
[
  {
    "seat": 1,
    "name": "John Doe",
    "stack": 150000,
    "hole_cards": ["As", "Kh"]
  }
]
```

### blinds_json (tournaments)

```json
[
  {
    "level": 1,
    "small_blind": 100,
    "big_blind": 200,
    "ante": 25,
    "duration_minutes": 60
  }
]
```

### output_settings_json (render_instructions)

```json
{
  "format": "png_sequence",
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "duration_frames": null,
  "quality": 90
}
```

---

## Migration

```powershell
# Supabase CLI로 마이그레이션 적용
supabase db push

# 또는 원격 DB에 직접 적용
supabase db push --db-url postgresql://postgres:PASSWORD@HOST:5432/postgres
```

---

## File Location

- Migration: `supabase/migrations/20250108000000_initial_schema.sql`
- Legacy: `scripts/init-db.sql` (Docker local용)
