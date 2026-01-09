# Schema Changelog

모든 스키마 변경 이력을 기록합니다.

## [1.0.0] - 2025-01-08

### Added

#### Common Schemas
- `common/enums.schema.json` - 모든 프로젝트 공유 enum 타입
  - GameVariant, GameClass, BetStructure, AnteType
  - EventType, HandRank, HandRankValue
  - SourceType, RenderStatus, OutputFormat
  - TournamentEventType, AnalysisStatus
  - LayerType, FootageType, CaptionPriority
- `common/card.schema.json` - 플레잉 카드 포맷 정의
  - Card, CardRank, CardSuit
  - HoleCards, CommunityCards, BoardCards

#### GFX Schemas (PokerGFX)
- `gfx/session.schema.json` - 세션 최상위 구조
- `gfx/hand.schema.json` - 핸드 데이터 + BlindsInfo
- `gfx/player.schema.json` - 플레이어 정보 + PlayerStats
- `gfx/event.schema.json` - 게임 이벤트 (조건부 검증 포함)

#### WSOP Schemas
- `wsop/tournament.schema.json` - 토너먼트 정보
  - PayoutEntry, PlayerStanding 내장 정의
- `wsop/blind_level.schema.json` - 블라인드 레벨 구조

#### Render Schemas
- `render/instruction.schema.json` - 렌더링 지시서
  - OutputSettings 내장 정의

#### Caption Schemas
- `caption/types.schema.json` - 26개 자막 타입 정의
  - CaptionCategory, CaptionType 정의

#### Supabase Migrations
- `20250108000000_initial_schema.sql` - 기존 hub 테이블 (hands, tournaments, render_*)
- `20250108100000_add_gfx_tables.sql` - GFX 테이블 추가
  - poker_sessions, poker_hands, poker_players, poker_events, hand_results

#### Validators
- `shared/validators/schema_validator.py` - JSON Schema 런타임 검증기

### Registry
- `registry.json` - 스키마 메타데이터 레지스트리

---

## Migration Guide

### From v0 (No Schema) to v1.0.0

1. 기존 Pydantic 모델은 그대로 사용 가능
2. JSON Schema 검증을 추가하려면:
   ```python
   from shared.validators import SchemaValidator

   # GFX 세션 데이터 검증
   valid, errors = SchemaValidator.validate_gfx_session(gfx_data)
   if not valid:
       print(f"Validation errors: {errors}")
   ```

3. Supabase 마이그레이션:
   ```bash
   supabase db push
   ```
