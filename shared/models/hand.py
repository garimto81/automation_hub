"""핸드 데이터 모델

feature_table에서 RFID JSON을 파싱하여 저장하는 핸드 정보.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """데이터 소스 타입"""
    RFID = "rfid"           # PokerGFX RFID
    CSV = "csv"             # WSOP+ 앱 CSV
    MANUAL = "manual"       # 수작업 입력


class HandRank(str, Enum):
    """포커 핸드 랭킹"""
    ROYAL_FLUSH = "royal_flush"
    STRAIGHT_FLUSH = "straight_flush"
    FOUR_OF_A_KIND = "four_of_a_kind"
    FULL_HOUSE = "full_house"
    FLUSH = "flush"
    STRAIGHT = "straight"
    THREE_OF_A_KIND = "three_of_a_kind"
    TWO_PAIR = "two_pair"
    ONE_PAIR = "one_pair"
    HIGH_CARD = "high_card"

    @property
    def display_name(self) -> str:
        return self.value.replace("_", " ").title()

    @property
    def is_premium(self) -> bool:
        """Full House 이상 프리미엄 핸드 여부"""
        premium_ranks = {
            HandRank.ROYAL_FLUSH,
            HandRank.STRAIGHT_FLUSH,
            HandRank.FOUR_OF_A_KIND,
            HandRank.FULL_HOUSE,
        }
        return self in premium_ranks


class PlayerInfo(BaseModel):
    """플레이어 정보"""
    seat: int
    name: str
    stack: int = 0
    hole_cards: list[str] = Field(default_factory=list)


class Hand(BaseModel):
    """핸드 데이터"""

    # 필수 필드
    id: Optional[int] = None
    table_id: str
    hand_number: int
    source: SourceType = SourceType.RFID

    # 핸드 정보
    hand_rank: Optional[HandRank] = None
    pot_size: int = 0
    winner: Optional[str] = None

    # 상세 정보 (JSON으로 저장)
    players: list[PlayerInfo] = Field(default_factory=list)
    community_cards: list[str] = Field(default_factory=list)
    actions: list[dict] = Field(default_factory=list)

    # 메타데이터
    duration_seconds: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def is_premium(self) -> bool:
        """프리미엄 핸드 여부"""
        return self.hand_rank is not None and self.hand_rank.is_premium

    def to_db_dict(self) -> dict:
        """DB 저장용 딕셔너리"""
        return {
            "table_id": self.table_id,
            "hand_number": self.hand_number,
            "source": self.source.value,
            "hand_rank": self.hand_rank.value if self.hand_rank else None,
            "pot_size": self.pot_size,
            "winner": self.winner,
            "players_json": [p.model_dump() for p in self.players],
            "community_cards_json": self.community_cards,
            "actions_json": self.actions,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "Hand":
        """DB 행에서 생성"""
        players = [PlayerInfo(**p) for p in row.get("players_json", [])]
        hand_rank = HandRank(row["hand_rank"]) if row.get("hand_rank") else None

        return cls(
            id=row.get("id"),
            table_id=row["table_id"],
            hand_number=row["hand_number"],
            source=SourceType(row["source"]),
            hand_rank=hand_rank,
            pot_size=row.get("pot_size", 0),
            winner=row.get("winner"),
            players=players,
            community_cards=row.get("community_cards_json", []),
            actions=row.get("actions_json", []),
            duration_seconds=row.get("duration_seconds"),
            created_at=row.get("created_at", datetime.now()),
            updated_at=row.get("updated_at", datetime.now()),
        )
