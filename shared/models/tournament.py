"""토너먼트 데이터 모델

automation_sub에서 WSOP+ CSV를 파싱하여 저장하는 토너먼트 정보.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BlindLevel(BaseModel):
    """블라인드 레벨 정보"""
    level: int
    small_blind: int
    big_blind: int
    ante: int = 0
    duration_minutes: int = 60


class PayoutEntry(BaseModel):
    """상금 배분 정보"""
    position: int           # 순위 (1, 2, 3, ...)
    position_end: Optional[int] = None  # 범위인 경우 (예: 10-12위)
    amount: int             # 상금액
    percentage: Optional[float] = None  # 전체 상금 대비 %


class PlayerStanding(BaseModel):
    """플레이어 순위 정보"""
    rank: int
    name: str
    nationality: str = ""   # ISO 3166-1 alpha-2
    chips: int = 0
    table_id: Optional[str] = None
    seat: Optional[int] = None


class Tournament(BaseModel):
    """토너먼트 데이터"""

    # 필수 필드
    id: Optional[int] = None
    name: str
    event_code: str         # 예: "WSOP2025-001"

    # 대회 정보
    event_type: str = "HOLDEM"  # HOLDEM, PLO, etc.
    buy_in: int = 0
    prize_pool: int = 0

    # 현재 상태
    total_entries: int = 0
    remaining_players: int = 0
    current_level: int = 1

    # 블라인드 구조
    blinds: list[BlindLevel] = Field(default_factory=list)
    current_blinds: Optional[BlindLevel] = None

    # 상금 구조
    payouts: list[PayoutEntry] = Field(default_factory=list)
    places_paid: int = 0

    # 순위 정보
    standings: list[PlayerStanding] = Field(default_factory=list)

    # 메타데이터
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    source: str = "csv"     # csv, manual, api
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def to_db_dict(self) -> dict:
        """DB 저장용 딕셔너리"""
        return {
            "name": self.name,
            "event_code": self.event_code,
            "event_type": self.event_type,
            "buy_in": self.buy_in,
            "prize_pool": self.prize_pool,
            "total_entries": self.total_entries,
            "remaining_players": self.remaining_players,
            "current_level": self.current_level,
            "blinds_json": [b.model_dump() for b in self.blinds],
            "current_blinds_json": self.current_blinds.model_dump() if self.current_blinds else None,
            "payouts_json": [p.model_dump() for p in self.payouts],
            "places_paid": self.places_paid,
            "standings_json": [s.model_dump() for s in self.standings],
            "start_date": self.start_date,
            "end_date": self.end_date,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "Tournament":
        """DB 행에서 생성"""
        blinds = [BlindLevel(**b) for b in row.get("blinds_json", [])]
        payouts = [PayoutEntry(**p) for p in row.get("payouts_json", [])]
        standings = [PlayerStanding(**s) for s in row.get("standings_json", [])]
        current_blinds = (
            BlindLevel(**row["current_blinds_json"])
            if row.get("current_blinds_json")
            else None
        )

        return cls(
            id=row.get("id"),
            name=row["name"],
            event_code=row["event_code"],
            event_type=row.get("event_type", "HOLDEM"),
            buy_in=row.get("buy_in", 0),
            prize_pool=row.get("prize_pool", 0),
            total_entries=row.get("total_entries", 0),
            remaining_players=row.get("remaining_players", 0),
            current_level=row.get("current_level", 1),
            blinds=blinds,
            current_blinds=current_blinds,
            payouts=payouts,
            places_paid=row.get("places_paid", 0),
            standings=standings,
            start_date=row.get("start_date"),
            end_date=row.get("end_date"),
            source=row.get("source", "csv"),
            created_at=row.get("created_at", datetime.now()),
            updated_at=row.get("updated_at", datetime.now()),
        )
