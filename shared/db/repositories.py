"""데이터 Repository

각 테이블에 대한 CRUD 로직.
"""

from datetime import datetime
from typing import Optional

from shared.db.connection import Database
from shared.models.hand import Hand, HandRank, SourceType
from shared.models.tournament import Tournament
from shared.models.render_instruction import RenderInstruction, RenderOutput, RenderStatus


class HandsRepository:
    """핸드 데이터 Repository"""

    def __init__(self, db: Database):
        self.db = db

    async def insert(self, hand: Hand) -> int:
        """핸드 저장"""
        import json

        query = """
            INSERT INTO hands (
                table_id, hand_number, source, hand_rank, pot_size, winner,
                players_json, community_cards_json, actions_json,
                duration_seconds, created_at, updated_at
            ) VALUES (
                :table_id, :hand_number, :source, :hand_rank, :pot_size, :winner,
                :players_json, :community_cards_json, :actions_json,
                :duration_seconds, :created_at, :updated_at
            ) RETURNING id
        """

        db_dict = hand.to_db_dict()
        db_dict["players_json"] = json.dumps(db_dict["players_json"])
        db_dict["community_cards_json"] = json.dumps(db_dict["community_cards_json"])
        db_dict["actions_json"] = json.dumps(db_dict["actions_json"])

        result = await self.db.execute(query, db_dict)
        return result[0]["id"] if result else 0

    async def get_by_id(self, hand_id: int) -> Optional[Hand]:
        """ID로 조회"""
        query = "SELECT * FROM hands WHERE id = :id"
        result = await self.db.execute(query, {"id": hand_id})
        return Hand.from_db_row(result[0]) if result else None

    async def get_by_table_and_number(
        self, table_id: str, hand_number: int
    ) -> Optional[Hand]:
        """테이블 ID + 핸드 번호로 조회"""
        query = """
            SELECT * FROM hands
            WHERE table_id = :table_id AND hand_number = :hand_number
        """
        result = await self.db.execute(
            query, {"table_id": table_id, "hand_number": hand_number}
        )
        return Hand.from_db_row(result[0]) if result else None

    async def get_recent(self, limit: int = 100) -> list[Hand]:
        """최근 핸드 조회"""
        query = "SELECT * FROM hands ORDER BY created_at DESC LIMIT :limit"
        result = await self.db.execute(query, {"limit": limit})
        return [Hand.from_db_row(row) for row in result]

    async def get_premium_hands(self, limit: int = 50) -> list[Hand]:
        """프리미엄 핸드 조회"""
        premium_ranks = ["royal_flush", "straight_flush", "four_of_a_kind", "full_house"]
        query = """
            SELECT * FROM hands
            WHERE hand_rank = ANY(:ranks)
            ORDER BY created_at DESC
            LIMIT :limit
        """
        result = await self.db.execute(query, {"ranks": premium_ranks, "limit": limit})
        return [Hand.from_db_row(row) for row in result]


class TournamentsRepository:
    """토너먼트 데이터 Repository"""

    def __init__(self, db: Database):
        self.db = db

    async def upsert(self, tournament: Tournament) -> int:
        """토너먼트 저장 또는 업데이트"""
        import json

        db_dict = tournament.to_db_dict()
        for key in ["blinds_json", "current_blinds_json", "payouts_json", "standings_json"]:
            if db_dict.get(key) is not None:
                db_dict[key] = json.dumps(db_dict[key])

        query = """
            INSERT INTO tournaments (
                name, event_code, event_type, buy_in, prize_pool,
                total_entries, remaining_players, current_level,
                blinds_json, current_blinds_json, payouts_json, places_paid,
                standings_json, start_date, end_date, source,
                created_at, updated_at
            ) VALUES (
                :name, :event_code, :event_type, :buy_in, :prize_pool,
                :total_entries, :remaining_players, :current_level,
                :blinds_json, :current_blinds_json, :payouts_json, :places_paid,
                :standings_json, :start_date, :end_date, :source,
                :created_at, :updated_at
            )
            ON CONFLICT (event_code) DO UPDATE SET
                name = EXCLUDED.name,
                total_entries = EXCLUDED.total_entries,
                remaining_players = EXCLUDED.remaining_players,
                current_level = EXCLUDED.current_level,
                current_blinds_json = EXCLUDED.current_blinds_json,
                standings_json = EXCLUDED.standings_json,
                updated_at = EXCLUDED.updated_at
            RETURNING id
        """
        result = await self.db.execute(query, db_dict)
        return result[0]["id"] if result else 0

    async def get_by_event_code(self, event_code: str) -> Optional[Tournament]:
        """이벤트 코드로 조회"""
        query = "SELECT * FROM tournaments WHERE event_code = :event_code"
        result = await self.db.execute(query, {"event_code": event_code})
        return Tournament.from_db_row(result[0]) if result else None

    async def get_active(self) -> list[Tournament]:
        """진행 중인 토너먼트 조회"""
        query = """
            SELECT * FROM tournaments
            WHERE end_date IS NULL OR end_date > NOW()
            ORDER BY start_date DESC
        """
        result = await self.db.execute(query)
        return [Tournament.from_db_row(row) for row in result]


class RenderInstructionsRepository:
    """렌더링 지시서 Repository"""

    def __init__(self, db: Database):
        self.db = db

    async def insert(self, instruction: RenderInstruction) -> int:
        """렌더링 지시서 저장"""
        import json

        db_dict = instruction.to_db_dict()
        db_dict["layer_data_json"] = json.dumps(db_dict["layer_data_json"])
        db_dict["output_settings_json"] = json.dumps(db_dict["output_settings_json"])

        query = """
            INSERT INTO render_instructions (
                template_name, layer_data_json, output_settings_json,
                output_path, output_filename, status, priority,
                trigger_type, trigger_id, error_message,
                retry_count, max_retries, created_at, started_at, completed_at
            ) VALUES (
                :template_name, :layer_data_json, :output_settings_json,
                :output_path, :output_filename, :status, :priority,
                :trigger_type, :trigger_id, :error_message,
                :retry_count, :max_retries, :created_at, :started_at, :completed_at
            ) RETURNING id
        """
        result = await self.db.execute(query, db_dict)
        return result[0]["id"] if result else 0

    async def get_pending(self, limit: int = 10) -> list[RenderInstruction]:
        """pending 상태 지시서 조회 (ae가 polling)"""
        query = """
            SELECT * FROM render_instructions
            WHERE status = 'pending'
            ORDER BY priority ASC, created_at ASC
            LIMIT :limit
        """
        result = await self.db.execute(query, {"limit": limit})
        return [RenderInstruction.from_db_row(row) for row in result]

    async def update_status(
        self,
        instruction_id: int,
        status: RenderStatus,
        error_message: Optional[str] = None,
    ) -> bool:
        """상태 업데이트"""
        now = datetime.now()
        query = """
            UPDATE render_instructions
            SET status = :status, error_message = :error_message
        """
        params = {
            "id": instruction_id,
            "status": status.value,
            "error_message": error_message,
        }

        if status == RenderStatus.PROCESSING:
            query += ", started_at = :started_at"
            params["started_at"] = now
        elif status in (RenderStatus.COMPLETED, RenderStatus.FAILED):
            query += ", completed_at = :completed_at"
            params["completed_at"] = now

        query += " WHERE id = :id"

        rows = await self.db.execute_write(query, params)
        return rows > 0

    async def increment_retry(self, instruction_id: int) -> bool:
        """재시도 횟수 증가"""
        query = """
            UPDATE render_instructions
            SET retry_count = retry_count + 1, status = 'pending'
            WHERE id = :id AND retry_count < max_retries
        """
        rows = await self.db.execute_write(query, {"id": instruction_id})
        return rows > 0

    async def get_stats(self) -> dict:
        """통계 조회 (모니터링용)"""
        query = """
            SELECT
                status,
                COUNT(*) as count
            FROM render_instructions
            GROUP BY status
        """
        result = await self.db.execute(query)
        return {row["status"]: row["count"] for row in result}


class RenderOutputsRepository:
    """렌더링 결과 Repository"""

    def __init__(self, db: Database):
        self.db = db

    async def insert(self, output: RenderOutput) -> int:
        """렌더링 결과 저장"""
        query = """
            INSERT INTO render_outputs (
                instruction_id, output_path, file_size, frame_count,
                status, error_message, created_at, completed_at
            ) VALUES (
                :instruction_id, :output_path, :file_size, :frame_count,
                :status, :error_message, :created_at, :completed_at
            ) RETURNING id
        """
        db_dict = output.to_db_dict()
        result = await self.db.execute(query, db_dict)
        return result[0]["id"] if result else 0

    async def get_by_instruction_id(
        self, instruction_id: int
    ) -> Optional[RenderOutput]:
        """지시서 ID로 조회"""
        query = "SELECT * FROM render_outputs WHERE instruction_id = :instruction_id"
        result = await self.db.execute(query, {"instruction_id": instruction_id})
        return RenderOutput.from_db_row(result[0]) if result else None

    async def get_recent(self, limit: int = 50) -> list[RenderOutput]:
        """최근 결과 조회"""
        query = "SELECT * FROM render_outputs ORDER BY completed_at DESC LIMIT :limit"
        result = await self.db.execute(query, {"limit": limit})
        return [RenderOutput.from_db_row(row) for row in result]
