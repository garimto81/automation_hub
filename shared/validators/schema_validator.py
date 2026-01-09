"""JSON Schema 기반 런타임 검증

모든 데이터 입력 시 사용하는 스키마 검증 레이어.
"""

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver
from jsonschema.exceptions import ValidationError

# 스키마 기본 경로
SCHEMA_BASE_PATH = Path(__file__).parent.parent.parent / "schemas" / "v1"


class SchemaValidator:
    """JSON Schema 검증기

    Usage:
        >>> from shared.validators import SchemaValidator
        >>> valid, errors = SchemaValidator.validate_gfx_session(gfx_data)
        >>> if not valid:
        ...     print(f"Validation errors: {errors}")
    """

    _schemas: dict[str, dict[str, Any]] = {}
    _validators: dict[str, Draft202012Validator] = {}
    _resolver: RefResolver | None = None

    @classmethod
    def _get_resolver(cls) -> RefResolver:
        """$ref 해석용 resolver 생성"""
        if cls._resolver is None:
            # 기본 스키마 로드 (common/enums, common/card)
            store: dict[str, dict[str, Any]] = {}

            # 모든 스키마 파일 로드하여 store에 추가
            for schema_file in SCHEMA_BASE_PATH.rglob("*.schema.json"):
                with open(schema_file, encoding="utf-8") as f:
                    schema = json.load(f)
                    if "$id" in schema:
                        store[schema["$id"]] = schema

            # RefResolver 생성
            cls._resolver = RefResolver(
                base_uri=f"file:///{SCHEMA_BASE_PATH.as_posix()}/",
                referrer={},
                store=store,
            )

        return cls._resolver

    @classmethod
    def load_schema(cls, schema_id: str) -> dict[str, Any]:
        """스키마 로드 (캐싱)

        Args:
            schema_id: 스키마 ID (예: "gfx/session", "wsop/tournament")

        Returns:
            로드된 JSON Schema dict
        """
        if schema_id not in cls._schemas:
            schema_path = SCHEMA_BASE_PATH / f"{schema_id}.schema.json"
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema not found: {schema_path}")

            with open(schema_path, encoding="utf-8") as f:
                cls._schemas[schema_id] = json.load(f)

        return cls._schemas[schema_id]

    @classmethod
    def get_validator(cls, schema_id: str) -> Draft202012Validator:
        """Validator 인스턴스 반환 (캐싱)"""
        if schema_id not in cls._validators:
            schema = cls.load_schema(schema_id)
            resolver = cls._get_resolver()
            cls._validators[schema_id] = Draft202012Validator(
                schema, resolver=resolver
            )
        return cls._validators[schema_id]

    @classmethod
    def validate(cls, data: Any, schema_id: str) -> tuple[bool, list[str]]:
        """데이터 검증

        Args:
            data: 검증할 데이터
            schema_id: 스키마 ID (예: "gfx/session")

        Returns:
            (valid, errors) 튜플
            - valid: 검증 성공 여부
            - errors: 에러 메시지 리스트
        """
        validator = cls.get_validator(schema_id)
        errors: list[str] = []

        for error in validator.iter_errors(data):
            path = " -> ".join(str(p) for p in error.absolute_path) or "root"
            errors.append(f"[{path}] {error.message}")

        return (len(errors) == 0, errors)

    @classmethod
    def validate_or_raise(cls, data: Any, schema_id: str) -> None:
        """검증 실패 시 예외 발생

        Args:
            data: 검증할 데이터
            schema_id: 스키마 ID

        Raises:
            ValidationError: 검증 실패 시
        """
        valid, errors = cls.validate(data, schema_id)
        if not valid:
            raise ValidationError(
                f"Schema validation failed for '{schema_id}':\n" +
                "\n".join(f"  - {e}" for e in errors)
            )

    # =========================================================
    # Convenience Methods
    # =========================================================

    @classmethod
    def validate_gfx_session(cls, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """GFX 세션 검증"""
        return cls.validate(data, "gfx/session")

    @classmethod
    def validate_gfx_hand(cls, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """GFX 핸드 검증"""
        return cls.validate(data, "gfx/hand")

    @classmethod
    def validate_gfx_player(cls, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """GFX 플레이어 검증"""
        return cls.validate(data, "gfx/player")

    @classmethod
    def validate_gfx_event(cls, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """GFX 이벤트 검증"""
        return cls.validate(data, "gfx/event")

    @classmethod
    def validate_tournament(cls, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """토너먼트 검증"""
        return cls.validate(data, "wsop/tournament")

    @classmethod
    def validate_render_instruction(
        cls, data: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """렌더링 지시서 검증"""
        return cls.validate(data, "render/instruction")

    # =========================================================
    # Utility Methods
    # =========================================================

    @classmethod
    def list_schemas(cls) -> list[str]:
        """사용 가능한 스키마 목록 반환"""
        schemas: list[str] = []
        for schema_file in SCHEMA_BASE_PATH.rglob("*.schema.json"):
            rel_path = schema_file.relative_to(SCHEMA_BASE_PATH)
            schema_id = str(rel_path).replace("\\", "/").replace(".schema.json", "")
            schemas.append(schema_id)
        return sorted(schemas)

    @classmethod
    def clear_cache(cls) -> None:
        """캐시 초기화 (테스트용)"""
        cls._schemas.clear()
        cls._validators.clear()
        cls._resolver = None
