-- WSOP Automation 공유 DB 초기화 스크립트
-- 모든 프로젝트가 공유하는 테이블 정의

-- ============================================================
-- 1. hands 테이블 (feature_table이 저장)
-- ============================================================
CREATE TABLE IF NOT EXISTS hands (
    id SERIAL PRIMARY KEY,
    table_id VARCHAR(50) NOT NULL,
    hand_number INTEGER NOT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'rfid',  -- rfid, csv, manual

    -- 핸드 정보
    hand_rank VARCHAR(30),  -- royal_flush, straight_flush, etc.
    pot_size INTEGER DEFAULT 0,
    winner VARCHAR(100),

    -- 상세 정보 (JSON)
    players_json JSONB DEFAULT '[]'::jsonb,
    community_cards_json JSONB DEFAULT '[]'::jsonb,
    actions_json JSONB DEFAULT '[]'::jsonb,

    -- 메타데이터
    duration_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 유니크 제약 (같은 테이블의 같은 핸드 번호)
    UNIQUE (table_id, hand_number)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_hands_table_id ON hands(table_id);
CREATE INDEX IF NOT EXISTS idx_hands_hand_rank ON hands(hand_rank);
CREATE INDEX IF NOT EXISTS idx_hands_created_at ON hands(created_at DESC);

-- ============================================================
-- 2. tournaments 테이블 (sub가 CSV에서 파싱)
-- ============================================================
CREATE TABLE IF NOT EXISTS tournaments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    event_code VARCHAR(50) NOT NULL UNIQUE,
    event_type VARCHAR(30) DEFAULT 'HOLDEM',

    -- 대회 정보
    buy_in INTEGER DEFAULT 0,
    prize_pool INTEGER DEFAULT 0,
    total_entries INTEGER DEFAULT 0,
    remaining_players INTEGER DEFAULT 0,
    current_level INTEGER DEFAULT 1,

    -- JSON 데이터
    blinds_json JSONB DEFAULT '[]'::jsonb,
    current_blinds_json JSONB,
    payouts_json JSONB DEFAULT '[]'::jsonb,
    places_paid INTEGER DEFAULT 0,
    standings_json JSONB DEFAULT '[]'::jsonb,

    -- 일정
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,

    -- 메타데이터
    source VARCHAR(20) DEFAULT 'csv',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_tournaments_event_code ON tournaments(event_code);
CREATE INDEX IF NOT EXISTS idx_tournaments_start_date ON tournaments(start_date DESC);

-- ============================================================
-- 3. render_instructions 테이블 (sub가 생성 → ae가 처리)
-- ============================================================
CREATE TABLE IF NOT EXISTS render_instructions (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL,

    -- 레이어 데이터
    layer_data_json JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- 출력 설정
    output_settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_path VARCHAR(500),
    output_filename VARCHAR(200),

    -- 상태
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    priority INTEGER DEFAULT 5,  -- 1(최고) - 10(최저)

    -- 트리거 정보
    trigger_type VARCHAR(50),
    trigger_id VARCHAR(100),

    -- 에러 처리
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- 타임스탬프
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_render_instructions_status ON render_instructions(status);
CREATE INDEX IF NOT EXISTS idx_render_instructions_priority ON render_instructions(priority, created_at);
CREATE INDEX IF NOT EXISTS idx_render_instructions_pending ON render_instructions(status, priority, created_at)
    WHERE status = 'pending';

-- ============================================================
-- 4. render_outputs 테이블 (ae가 저장)
-- ============================================================
CREATE TABLE IF NOT EXISTS render_outputs (
    id SERIAL PRIMARY KEY,
    instruction_id INTEGER NOT NULL REFERENCES render_instructions(id) ON DELETE CASCADE,

    -- 출력 정보
    output_path VARCHAR(500) NOT NULL,
    file_size BIGINT DEFAULT 0,
    frame_count INTEGER,

    -- 상태
    status VARCHAR(20) DEFAULT 'completed',
    error_message TEXT,

    -- 타임스탬프
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_render_outputs_instruction_id ON render_outputs(instruction_id);

-- ============================================================
-- 5. 업데이트 트리거 (updated_at 자동 갱신)
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- hands 테이블 트리거
DROP TRIGGER IF EXISTS update_hands_updated_at ON hands;
CREATE TRIGGER update_hands_updated_at
    BEFORE UPDATE ON hands
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- tournaments 테이블 트리거
DROP TRIGGER IF EXISTS update_tournaments_updated_at ON tournaments;
CREATE TRIGGER update_tournaments_updated_at
    BEFORE UPDATE ON tournaments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 완료 메시지
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE 'WSOP Automation DB initialized successfully!';
END $$;
