"""렌더링 지시서 모델

automation_sub에서 생성하여 automation_ae가 처리하는 렌더링 작업.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RenderStatus(str, Enum):
    """렌더링 상태"""
    PENDING = "pending"           # 대기 중 (ae가 polling)
    PROCESSING = "processing"     # 렌더링 중
    COMPLETED = "completed"       # 완료
    FAILED = "failed"             # 실패


class OutputFormat(str, Enum):
    """출력 형식"""
    PNG_SEQUENCE = "png_sequence"
    MOV_ALPHA = "mov_alpha"
    MP4 = "mp4"


class OutputSettings(BaseModel):
    """출력 설정"""
    format: OutputFormat = OutputFormat.PNG_SEQUENCE
    width: int = 1920
    height: int = 1080
    fps: int = 30
    duration_frames: Optional[int] = None
    quality: int = 90


class RenderInstruction(BaseModel):
    """렌더링 지시서

    automation_sub가 생성 → DB에 pending 상태로 저장
    automation_ae가 polling → 렌더링 실행 → completed/failed로 업데이트
    """

    # 필수 필드
    id: Optional[int] = None
    template_name: str          # AE 템플릿 이름

    # 레이어 데이터 (AE 템플릿에 주입)
    layer_data: dict = Field(default_factory=dict)
    # 예: {"player_name": "John Doe", "chip_count": "$1,000,000"}

    # 출력 설정
    output_settings: OutputSettings = Field(default_factory=OutputSettings)
    output_path: Optional[str] = None       # 지정된 출력 경로
    output_filename: Optional[str] = None   # 지정된 파일명

    # 상태
    status: RenderStatus = RenderStatus.PENDING
    priority: int = 5           # 1(최고) - 10(최저)

    # 트리거 정보 (어떤 이벤트로 생성되었는지)
    trigger_type: str = ""      # 예: "premium_hand", "elimination"
    trigger_id: Optional[str] = None  # 관련 핸드/이벤트 ID

    # 처리 정보
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # 타임스탬프
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_db_dict(self) -> dict:
        """DB 저장용 딕셔너리"""
        return {
            "template_name": self.template_name,
            "layer_data_json": self.layer_data,
            "output_settings_json": self.output_settings.model_dump(),
            "output_path": self.output_path,
            "output_filename": self.output_filename,
            "status": self.status.value,
            "priority": self.priority,
            "trigger_type": self.trigger_type,
            "trigger_id": self.trigger_id,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "RenderInstruction":
        """DB 행에서 생성"""
        output_settings = OutputSettings(**row.get("output_settings_json", {}))

        return cls(
            id=row.get("id"),
            template_name=row["template_name"],
            layer_data=row.get("layer_data_json", {}),
            output_settings=output_settings,
            output_path=row.get("output_path"),
            output_filename=row.get("output_filename"),
            status=RenderStatus(row.get("status", "pending")),
            priority=row.get("priority", 5),
            trigger_type=row.get("trigger_type", ""),
            trigger_id=row.get("trigger_id"),
            error_message=row.get("error_message"),
            retry_count=row.get("retry_count", 0),
            max_retries=row.get("max_retries", 3),
            created_at=row.get("created_at", datetime.now()),
            started_at=row.get("started_at"),
            completed_at=row.get("completed_at"),
        )


class RenderOutput(BaseModel):
    """렌더링 결과

    automation_ae가 렌더링 완료 후 저장.
    """

    # 필수 필드
    id: Optional[int] = None
    instruction_id: int         # FK → render_instructions

    # 출력 정보
    output_path: str            # 실제 저장 경로
    file_size: int = 0          # 바이트
    frame_count: Optional[int] = None  # PNG 시퀀스인 경우

    # 상태
    status: RenderStatus = RenderStatus.COMPLETED
    error_message: Optional[str] = None

    # 타임스탬프
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime = Field(default_factory=datetime.now)

    def to_db_dict(self) -> dict:
        """DB 저장용 딕셔너리"""
        return {
            "instruction_id": self.instruction_id,
            "output_path": self.output_path,
            "file_size": self.file_size,
            "frame_count": self.frame_count,
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "RenderOutput":
        """DB 행에서 생성"""
        return cls(
            id=row.get("id"),
            instruction_id=row["instruction_id"],
            output_path=row["output_path"],
            file_size=row.get("file_size", 0),
            frame_count=row.get("frame_count"),
            status=RenderStatus(row.get("status", "completed")),
            error_message=row.get("error_message"),
            created_at=row.get("created_at", datetime.now()),
            completed_at=row.get("completed_at", datetime.now()),
        )
