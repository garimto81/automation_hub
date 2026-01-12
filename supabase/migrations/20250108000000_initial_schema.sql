-- ============================================================
-- WSOP Automation Hub - Supabase Schema
-- Version: 1.0.0
-- Date: 2025-01-08
-- ============================================================

-- ============================================================
-- PART 1: ENUM Types
-- ============================================================

-- 데이터 소스 타입
CREATE TYPE source_type AS ENUM ('rfid', 'csv', 'manual');

-- 포커 핸드 랭킹
CREATE TYPE hand_rank AS ENUM (
    'royal_flush',
    'straight_flush',
    'four_of_a_kind',
    'full_house',
    'flush',
    'straight',
    'three_of_a_kind',
    'two_pair',
    'one_pair',
    'high_card'
);

-- 렌더링 상태
CREATE TYPE render_status AS ENUM ('pending', 'processing', 'completed', 'failed');

-- 출력 형식
CREATE TYPE output_format AS ENUM ('png_sequence', 'mov_alpha', 'mp4');

-- 토너먼트 이벤트 타입
CREATE TYPE event_type AS ENUM ('HOLDEM', 'PLO', 'PLO8', 'RAZZ', 'STUD', 'HORSE', 'MIXED');

-- ============================================================
-- PART 2: Core Tables
-- ============================================================

-- ------------------------------------------------------------
-- 2.1 hands - 포커 핸드 데이터 (feature_table → DB)
-- ------------------------------------------------------------
CREATE TABLE hands (
    id BIGSERIAL PRIMARY KEY,
    table_id VARCHAR(50) NOT NULL,
    hand_number INTEGER NOT NULL,
    source source_type NOT NULL DEFAULT 'rfid',

    -- 핸드 정보
    hand_rank hand_rank,
    pot_size INTEGER DEFAULT 0,
    winner VARCHAR(100),

    -- 상세 정보 (JSONB)
    players_json JSONB DEFAULT '[]'::jsonb,
    community_cards_json JSONB DEFAULT '[]'::jsonb,
    actions_json JSONB DEFAULT '[]'::jsonb,

    -- 메타데이터
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 유니크 제약
    CONSTRAINT uq_hands_table_hand UNIQUE (table_id, hand_number)
);

-- 인덱스
CREATE INDEX idx_hands_table_id ON hands(table_id);
CREATE INDEX idx_hands_hand_rank ON hands(hand_rank) WHERE hand_rank IS NOT NULL;
CREATE INDEX idx_hands_created_at ON hands(created_at DESC);
CREATE INDEX idx_hands_source ON hands(source);

-- Premium hands (Full House 이상) 부분 인덱스
CREATE INDEX idx_hands_premium ON hands(hand_rank, created_at DESC)
    WHERE hand_rank IN ('royal_flush', 'straight_flush', 'four_of_a_kind', 'full_house');

-- JSONB GIN 인덱스 (플레이어 검색용)
CREATE INDEX idx_hands_players_gin ON hands USING GIN (players_json);

-- 코멘트
COMMENT ON TABLE hands IS '포커 핸드 데이터 - RFID/CSV/수작업 소스에서 수집';
COMMENT ON COLUMN hands.players_json IS 'PlayerInfo[] - {seat, name, stack, hole_cards[]}';
COMMENT ON COLUMN hands.community_cards_json IS 'string[] - 커뮤니티 카드 (예: ["As", "Kh", "Qd"])';
COMMENT ON COLUMN hands.actions_json IS 'Action[] - 베팅 액션 기록';

-- ------------------------------------------------------------
-- 2.2 tournaments - 토너먼트 정보 (sub → CSV 파싱)
-- ------------------------------------------------------------
CREATE TABLE tournaments (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    event_code VARCHAR(50) NOT NULL,
    event_type event_type DEFAULT 'HOLDEM',

    -- 대회 정보
    buy_in INTEGER DEFAULT 0,
    prize_pool BIGINT DEFAULT 0,
    total_entries INTEGER DEFAULT 0,
    remaining_players INTEGER DEFAULT 0,
    current_level INTEGER DEFAULT 1,

    -- 블라인드 구조 (JSONB)
    blinds_json JSONB DEFAULT '[]'::jsonb,
    current_blinds_json JSONB,

    -- 상금 구조 (JSONB)
    payouts_json JSONB DEFAULT '[]'::jsonb,
    places_paid INTEGER DEFAULT 0,

    -- 순위 정보 (JSONB)
    standings_json JSONB DEFAULT '[]'::jsonb,

    -- 일정
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,

    -- 메타데이터
    source VARCHAR(20) DEFAULT 'csv',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 유니크 제약
    CONSTRAINT uq_tournaments_event_code UNIQUE (event_code)
);

-- 인덱스
CREATE INDEX idx_tournaments_event_code ON tournaments(event_code);
CREATE INDEX idx_tournaments_start_date ON tournaments(start_date DESC);
CREATE INDEX idx_tournaments_event_type ON tournaments(event_type);
CREATE INDEX idx_tournaments_active ON tournaments(remaining_players DESC)
    WHERE remaining_players > 0;

-- 코멘트
COMMENT ON TABLE tournaments IS '토너먼트 정보 - WSOP+ CSV에서 파싱';
COMMENT ON COLUMN tournaments.blinds_json IS 'BlindLevel[] - {level, small_blind, big_blind, ante, duration_minutes}';
COMMENT ON COLUMN tournaments.payouts_json IS 'PayoutEntry[] - {position, position_end, amount, percentage}';
COMMENT ON COLUMN tournaments.standings_json IS 'PlayerStanding[] - {rank, name, nationality, chips, table_id, seat}';

-- ------------------------------------------------------------
-- 2.3 render_instructions - 렌더링 지시서 (sub → ae)
-- ------------------------------------------------------------
CREATE TABLE render_instructions (
    id BIGSERIAL PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL,

    -- 레이어 데이터 (AE 템플릿 주입)
    layer_data_json JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- 출력 설정
    output_settings_json JSONB NOT NULL DEFAULT '{
        "format": "png_sequence",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "quality": 90
    }'::jsonb,
    output_path VARCHAR(500),
    output_filename VARCHAR(200),

    -- 상태
    status render_status NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),

    -- 트리거 정보
    trigger_type VARCHAR(50),
    trigger_id VARCHAR(100),

    -- 에러 처리
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- 타임스탬프
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- 인덱스
CREATE INDEX idx_render_instructions_status ON render_instructions(status);
CREATE INDEX idx_render_instructions_priority ON render_instructions(priority ASC, created_at ASC);

-- Pending 작업 polling용 복합 인덱스 (ae가 주로 사용)
CREATE INDEX idx_render_instructions_pending_poll ON render_instructions(priority ASC, created_at ASC)
    WHERE status = 'pending';

-- Processing 작업 모니터링용
CREATE INDEX idx_render_instructions_processing ON render_instructions(started_at)
    WHERE status = 'processing';

-- 트리거 기반 조회용
CREATE INDEX idx_render_instructions_trigger ON render_instructions(trigger_type, trigger_id)
    WHERE trigger_type IS NOT NULL;

-- 코멘트
COMMENT ON TABLE render_instructions IS '렌더링 지시서 - sub가 생성, ae가 polling 후 처리';
COMMENT ON COLUMN render_instructions.layer_data_json IS 'AE 템플릿에 주입할 레이어 데이터';
COMMENT ON COLUMN render_instructions.output_settings_json IS 'OutputSettings - {format, width, height, fps, duration_frames, quality}';
COMMENT ON COLUMN render_instructions.priority IS '우선순위: 1(최고) - 10(최저)';

-- ------------------------------------------------------------
-- 2.4 render_outputs - 렌더링 결과 (ae → 저장)
-- ------------------------------------------------------------
CREATE TABLE render_outputs (
    id BIGSERIAL PRIMARY KEY,
    instruction_id BIGINT NOT NULL,

    -- 출력 정보
    output_path VARCHAR(500) NOT NULL,
    file_size BIGINT DEFAULT 0,
    frame_count INTEGER,

    -- 상태
    status render_status DEFAULT 'completed',
    error_message TEXT,

    -- 타임스탬프
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ DEFAULT NOW(),

    -- FK
    CONSTRAINT fk_render_outputs_instruction
        FOREIGN KEY (instruction_id)
        REFERENCES render_instructions(id)
        ON DELETE CASCADE
);

-- 인덱스
CREATE INDEX idx_render_outputs_instruction_id ON render_outputs(instruction_id);
CREATE INDEX idx_render_outputs_status ON render_outputs(status);
CREATE INDEX idx_render_outputs_created_at ON render_outputs(created_at DESC);

-- 코멘트
COMMENT ON TABLE render_outputs IS '렌더링 결과 - ae가 완료 후 저장';

-- ============================================================
-- PART 3: Views (편의용)
-- ============================================================

-- 최근 프리미엄 핸드
CREATE VIEW v_premium_hands AS
SELECT
    h.*,
    CASE h.hand_rank
        WHEN 'royal_flush' THEN 1
        WHEN 'straight_flush' THEN 2
        WHEN 'four_of_a_kind' THEN 3
        WHEN 'full_house' THEN 4
        ELSE 5
    END as rank_order
FROM hands h
WHERE h.hand_rank IN ('royal_flush', 'straight_flush', 'four_of_a_kind', 'full_house')
ORDER BY rank_order, h.created_at DESC;

COMMENT ON VIEW v_premium_hands IS '프리미엄 핸드 조회용 뷰 (Full House 이상)';

-- 대기 중인 렌더링 작업
CREATE VIEW v_pending_renders AS
SELECT
    ri.*,
    (SELECT COUNT(*) FROM render_outputs ro WHERE ro.instruction_id = ri.id) as output_count
FROM render_instructions ri
WHERE ri.status = 'pending'
ORDER BY ri.priority ASC, ri.created_at ASC;

COMMENT ON VIEW v_pending_renders IS 'Pending 렌더링 작업 조회용 뷰';

-- 활성 토너먼트
CREATE VIEW v_active_tournaments AS
SELECT
    t.*,
    ROUND((t.total_entries - t.remaining_players)::numeric / NULLIF(t.total_entries, 0) * 100, 1) as elimination_pct
FROM tournaments t
WHERE t.remaining_players > 0
ORDER BY t.remaining_players DESC;

COMMENT ON VIEW v_active_tournaments IS '활성 토너먼트 (남은 플레이어 > 0)';

-- ============================================================
-- PART 4: Functions & Triggers
-- ============================================================

-- updated_at 자동 갱신 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- hands 테이블 트리거
CREATE TRIGGER tr_hands_updated_at
    BEFORE UPDATE ON hands
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- tournaments 테이블 트리거
CREATE TRIGGER tr_tournaments_updated_at
    BEFORE UPDATE ON tournaments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 렌더링 시작 시 started_at 자동 설정
CREATE OR REPLACE FUNCTION set_render_started_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'processing' AND OLD.status = 'pending' THEN
        NEW.started_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_render_instructions_started
    BEFORE UPDATE ON render_instructions
    FOR EACH ROW
    EXECUTE FUNCTION set_render_started_at();

-- 렌더링 완료 시 completed_at 자동 설정
CREATE OR REPLACE FUNCTION set_render_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status IN ('completed', 'failed') AND OLD.status IN ('pending', 'processing') THEN
        NEW.completed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_render_instructions_completed
    BEFORE UPDATE ON render_instructions
    FOR EACH ROW
    EXECUTE FUNCTION set_render_completed_at();

-- ============================================================
-- PART 5: RLS (Row Level Security) - Supabase 권장
-- ============================================================

-- RLS 활성화
ALTER TABLE hands ENABLE ROW LEVEL SECURITY;
ALTER TABLE tournaments ENABLE ROW LEVEL SECURITY;
ALTER TABLE render_instructions ENABLE ROW LEVEL SECURITY;
ALTER TABLE render_outputs ENABLE ROW LEVEL SECURITY;

-- 서비스 역할용 전체 접근 정책 (anon/authenticated는 제한)
-- 현재는 서버 간 통신이므로 service_role 사용

-- hands: 모든 서비스가 읽기/쓰기 가능
CREATE POLICY "Service role full access on hands"
    ON hands
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- 인증된 사용자 읽기 전용 (대시보드용)
CREATE POLICY "Authenticated read access on hands"
    ON hands
    FOR SELECT
    TO authenticated
    USING (true);

-- tournaments: 동일한 정책
CREATE POLICY "Service role full access on tournaments"
    ON tournaments
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Authenticated read access on tournaments"
    ON tournaments
    FOR SELECT
    TO authenticated
    USING (true);

-- render_instructions: 동일한 정책
CREATE POLICY "Service role full access on render_instructions"
    ON render_instructions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Authenticated read access on render_instructions"
    ON render_instructions
    FOR SELECT
    TO authenticated
    USING (true);

-- render_outputs: 동일한 정책
CREATE POLICY "Service role full access on render_outputs"
    ON render_outputs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Authenticated read access on render_outputs"
    ON render_outputs
    FOR SELECT
    TO authenticated
    USING (true);

-- ============================================================
-- PART 6: Supabase Realtime 설정
-- ============================================================

-- Realtime 활성화 (대시보드 실시간 업데이트용)
ALTER PUBLICATION supabase_realtime ADD TABLE hands;
ALTER PUBLICATION supabase_realtime ADD TABLE render_instructions;

-- ============================================================
-- 완료 메시지
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '====================================================';
    RAISE NOTICE 'WSOP Automation Hub - Supabase Schema Initialized!';
    RAISE NOTICE '====================================================';
    RAISE NOTICE 'Tables: hands, tournaments, render_instructions, render_outputs';
    RAISE NOTICE 'Views: v_premium_hands, v_pending_renders, v_active_tournaments';
    RAISE NOTICE 'RLS: Enabled with service_role full access';
    RAISE NOTICE 'Realtime: hands, render_instructions';
    RAISE NOTICE '====================================================';
END $$;
