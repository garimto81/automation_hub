-- ============================================================
-- WSOP Automation Hub - GFX Tables Migration
-- Version: 1.0.0
-- Date: 2025-01-08
-- Description: PokerGFX 관련 테이블 추가 (automation_ae에서 이관)
-- ============================================================

-- ============================================================
-- PART 1: poker_sessions 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS poker_sessions (
    id BIGSERIAL PRIMARY KEY,
    gfx_session_id BIGINT NOT NULL,
    event_title VARCHAR(255),
    table_type VARCHAR(50) NOT NULL DEFAULT 'FEATURE_TABLE',
    software_version VARCHAR(50),
    payouts JSONB,
    created_at_utc TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_poker_sessions_gfx_id UNIQUE (gfx_session_id)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_poker_sessions_gfx_id ON poker_sessions(gfx_session_id);
CREATE INDEX IF NOT EXISTS idx_poker_sessions_created ON poker_sessions(created_at DESC);

-- 코멘트
COMMENT ON TABLE poker_sessions IS 'PokerGFX 세션 데이터 - RFID 시스템에서 수집';
COMMENT ON COLUMN poker_sessions.gfx_session_id IS 'PokerGFX 고유 세션 ID (638961999170907267 형태)';

-- ============================================================
-- PART 2: poker_hands 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS poker_hands (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL,
    hand_num INTEGER NOT NULL,
    game_variant VARCHAR(20) DEFAULT 'HOLDEM',
    game_class VARCHAR(10) DEFAULT 'FLOP',
    bet_structure VARCHAR(10) DEFAULT 'NOLIMIT',
    duration_seconds FLOAT,
    started_at_utc TIMESTAMPTZ,
    num_boards INTEGER DEFAULT 1,
    run_it_num_times INTEGER DEFAULT 1,
    community_cards JSONB DEFAULT '[]'::jsonb,

    -- 블라인드 정보
    button_seat INTEGER,
    sb_seat INTEGER,
    sb_amount INTEGER,
    bb_seat INTEGER,
    bb_amount INTEGER,
    ante_type VARCHAR(20) DEFAULT 'NONE',
    blind_level INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_poker_hands_session
        FOREIGN KEY (session_id)
        REFERENCES poker_sessions(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_poker_hands_session_num UNIQUE (session_id, hand_num)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_poker_hands_session ON poker_hands(session_id);
CREATE INDEX IF NOT EXISTS idx_poker_hands_created ON poker_hands(created_at DESC);

-- 코멘트
COMMENT ON TABLE poker_hands IS 'PokerGFX 핸드 데이터';
COMMENT ON COLUMN poker_hands.community_cards IS 'string[] - 커뮤니티 카드 (예: ["As", "Kh", "Qd"])';

-- ============================================================
-- PART 3: poker_players 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS poker_players (
    id BIGSERIAL PRIMARY KEY,
    hand_id BIGINT NOT NULL,
    seat_num INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    long_name VARCHAR(255),
    start_stack INTEGER DEFAULT 0,
    end_stack INTEGER DEFAULT 0,
    cumulative_winnings INTEGER DEFAULT 0,
    hole_cards JSONB DEFAULT '[]'::jsonb,
    sitting_out BOOLEAN DEFAULT FALSE,
    elimination_rank INTEGER DEFAULT -1,

    -- 플레이어 통계
    vpip_percent FLOAT,
    pfr_percent FLOAT,
    af_percent FLOAT,
    wtsd_percent FLOAT,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_poker_players_hand
        FOREIGN KEY (hand_id)
        REFERENCES poker_hands(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_poker_players_hand_seat UNIQUE (hand_id, seat_num)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_poker_players_hand ON poker_players(hand_id);
CREATE INDEX IF NOT EXISTS idx_poker_players_name ON poker_players(name);

-- 코멘트
COMMENT ON TABLE poker_players IS '핸드 내 플레이어 정보';
COMMENT ON COLUMN poker_players.hole_cards IS 'string[] - 홀카드 (쇼다운 시 공개)';

-- ============================================================
-- PART 4: poker_events 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS poker_events (
    id BIGSERIAL PRIMARY KEY,
    hand_id BIGINT NOT NULL,
    event_order INTEGER NOT NULL,
    event_type VARCHAR(20) NOT NULL,
    seat_num INTEGER,
    bet_amount INTEGER,
    pot_amount INTEGER,
    board_cards JSONB,
    board_num INTEGER,
    cards_drawn INTEGER,
    won_amount INTEGER,
    event_at_utc TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_poker_events_hand
        FOREIGN KEY (hand_id)
        REFERENCES poker_hands(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_poker_events_hand_order UNIQUE (hand_id, event_order)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_poker_events_hand ON poker_events(hand_id);
CREATE INDEX IF NOT EXISTS idx_poker_events_type ON poker_events(event_type);

-- 코멘트
COMMENT ON TABLE poker_events IS '게임 이벤트 (베팅 액션, 보드 카드, 결과)';

-- ============================================================
-- PART 5: hand_results 테이블 (핸드 결과)
-- ============================================================
CREATE TABLE IF NOT EXISTS hand_results (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL,
    rank_value INTEGER NOT NULL CHECK (rank_value BETWEEN 1 AND 7462),
    rank_category hand_rank NOT NULL,
    rank_name VARCHAR(50) NOT NULL,
    is_premium BOOLEAN DEFAULT FALSE,
    is_winner BOOLEAN DEFAULT FALSE,
    won_amount INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_hand_results_player
        FOREIGN KEY (player_id)
        REFERENCES poker_players(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_hand_results_player UNIQUE (player_id)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_hand_results_premium ON hand_results(is_premium) WHERE is_premium = TRUE;
CREATE INDEX IF NOT EXISTS idx_hand_results_winner ON hand_results(is_winner) WHERE is_winner = TRUE;
CREATE INDEX IF NOT EXISTS idx_hand_results_rank ON hand_results(rank_category);

-- 코멘트
COMMENT ON TABLE hand_results IS '핸드 결과 - phevaluator 기반 랭킹';
COMMENT ON COLUMN hand_results.rank_value IS 'phevaluator 점수 (1=Royal Flush, 7462=7-5-4-3-2 high)';

-- ============================================================
-- PART 6: 트리거 (updated_at 자동 갱신)
-- ============================================================
CREATE TRIGGER tr_poker_sessions_updated_at
    BEFORE UPDATE ON poker_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- PART 7: RLS 정책
-- ============================================================
ALTER TABLE poker_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE poker_hands ENABLE ROW LEVEL SECURITY;
ALTER TABLE poker_players ENABLE ROW LEVEL SECURITY;
ALTER TABLE poker_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE hand_results ENABLE ROW LEVEL SECURITY;

-- service_role 전체 접근
CREATE POLICY "Service role full access on poker_sessions"
    ON poker_sessions FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on poker_hands"
    ON poker_hands FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on poker_players"
    ON poker_players FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on poker_events"
    ON poker_events FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on hand_results"
    ON hand_results FOR ALL TO service_role USING (true) WITH CHECK (true);

-- authenticated 읽기 전용
CREATE POLICY "Authenticated read access on poker_sessions"
    ON poker_sessions FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated read access on poker_hands"
    ON poker_hands FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated read access on poker_players"
    ON poker_players FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated read access on poker_events"
    ON poker_events FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated read access on hand_results"
    ON hand_results FOR SELECT TO authenticated USING (true);

-- ============================================================
-- PART 8: Realtime 활성화
-- ============================================================
ALTER PUBLICATION supabase_realtime ADD TABLE poker_hands;
ALTER PUBLICATION supabase_realtime ADD TABLE hand_results;

-- ============================================================
-- 완료 메시지
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '====================================================';
    RAISE NOTICE 'GFX Tables Migration Completed!';
    RAISE NOTICE '====================================================';
    RAISE NOTICE 'Tables: poker_sessions, poker_hands, poker_players, poker_events, hand_results';
    RAISE NOTICE 'RLS: Enabled with service_role full access';
    RAISE NOTICE 'Realtime: poker_hands, hand_results';
    RAISE NOTICE '====================================================';
END $$;
