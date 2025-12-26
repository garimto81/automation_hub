"""모델 테스트"""

import pytest
from datetime import datetime

from shared.models.hand import Hand, HandRank, SourceType, PlayerInfo
from shared.models.tournament import Tournament, BlindLevel, PayoutEntry
from shared.models.render_instruction import (
    RenderInstruction,
    RenderOutput,
    RenderStatus,
    OutputFormat,
    OutputSettings,
)


class TestHandModel:
    """Hand 모델 테스트"""

    def test_create_hand(self):
        """핸드 생성"""
        hand = Hand(
            table_id="feature_1",
            hand_number=42,
            hand_rank=HandRank.FULL_HOUSE,
            pot_size=100000,
            winner="John Doe",
        )

        assert hand.table_id == "feature_1"
        assert hand.hand_number == 42
        assert hand.hand_rank == HandRank.FULL_HOUSE
        assert hand.is_premium is True

    def test_hand_rank_premium(self):
        """프리미엄 핸드 판별"""
        premium_ranks = [
            HandRank.ROYAL_FLUSH,
            HandRank.STRAIGHT_FLUSH,
            HandRank.FOUR_OF_A_KIND,
            HandRank.FULL_HOUSE,
        ]
        for rank in premium_ranks:
            assert rank.is_premium is True

        non_premium_ranks = [
            HandRank.FLUSH,
            HandRank.STRAIGHT,
            HandRank.THREE_OF_A_KIND,
            HandRank.TWO_PAIR,
            HandRank.ONE_PAIR,
            HandRank.HIGH_CARD,
        ]
        for rank in non_premium_ranks:
            assert rank.is_premium is False

    def test_hand_to_db_dict(self):
        """DB 저장용 딕셔너리 변환"""
        hand = Hand(
            table_id="feature_1",
            hand_number=42,
            source=SourceType.RFID,
            players=[PlayerInfo(seat=1, name="John", stack=50000)],
        )

        db_dict = hand.to_db_dict()

        assert db_dict["table_id"] == "feature_1"
        assert db_dict["hand_number"] == 42
        assert db_dict["source"] == "rfid"
        assert len(db_dict["players_json"]) == 1


class TestTournamentModel:
    """Tournament 모델 테스트"""

    def test_create_tournament(self):
        """토너먼트 생성"""
        tournament = Tournament(
            name="WSOP Main Event",
            event_code="WSOP2025-001",
            buy_in=10000,
            prize_pool=100000000,
            total_entries=10000,
        )

        assert tournament.name == "WSOP Main Event"
        assert tournament.event_code == "WSOP2025-001"
        assert tournament.buy_in == 10000

    def test_tournament_with_blinds(self):
        """블라인드 구조 포함"""
        tournament = Tournament(
            name="Test",
            event_code="TEST-001",
            blinds=[
                BlindLevel(level=1, small_blind=100, big_blind=200),
                BlindLevel(level=2, small_blind=200, big_blind=400, ante=50),
            ],
        )

        assert len(tournament.blinds) == 2
        assert tournament.blinds[1].ante == 50


class TestRenderInstructionModel:
    """RenderInstruction 모델 테스트"""

    def test_create_instruction(self):
        """렌더링 지시서 생성"""
        instruction = RenderInstruction(
            template_name="leaderboard",
            layer_data={"player_name": "John Doe", "chips": "1,000,000"},
            priority=1,
        )

        assert instruction.template_name == "leaderboard"
        assert instruction.status == RenderStatus.PENDING
        assert instruction.priority == 1

    def test_instruction_output_settings(self):
        """출력 설정"""
        settings = OutputSettings(
            format=OutputFormat.PNG_SEQUENCE,
            width=1920,
            height=1080,
            fps=30,
        )

        instruction = RenderInstruction(
            template_name="test",
            output_settings=settings,
        )

        assert instruction.output_settings.format == OutputFormat.PNG_SEQUENCE
        assert instruction.output_settings.width == 1920

    def test_instruction_to_db_dict(self):
        """DB 저장용 딕셔너리 변환"""
        instruction = RenderInstruction(
            template_name="leaderboard",
            layer_data={"name": "test"},
            trigger_type="premium_hand",
        )

        db_dict = instruction.to_db_dict()

        assert db_dict["template_name"] == "leaderboard"
        assert db_dict["status"] == "pending"
        assert db_dict["trigger_type"] == "premium_hand"


class TestRenderOutputModel:
    """RenderOutput 모델 테스트"""

    def test_create_output(self):
        """렌더링 결과 생성"""
        output = RenderOutput(
            instruction_id=1,
            output_path="/nas/renders/job_001/result.png",
            file_size=1024000,
            frame_count=120,
        )

        assert output.instruction_id == 1
        assert output.status == RenderStatus.COMPLETED
        assert output.file_size == 1024000
