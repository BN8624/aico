# P3 key_slot과 환경 변수 이름의 안전한 매핑 skeleton을 제공한다.
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .provider_base import KEY_SLOTS

KEY_SLOT_ENV_VARS = MappingProxyType(
    {
        "manager_1": "AICO_MANAGER_1_API_KEY",
        "worker_1": "AICO_WORKER_1_API_KEY",
        "worker_2": "AICO_WORKER_2_API_KEY",
        "worker_3": "AICO_WORKER_3_API_KEY",
        "worker_4": "AICO_WORKER_4_API_KEY",
        "auditor_1": "AICO_AUDITOR_1_API_KEY",
        "reserve_1": "AICO_RESERVE_1_API_KEY",
    }
)


@dataclass(frozen=True)
class KeySlotStatus:
    key_slot: str
    env_var_name: str
    configured: bool
    failure_type: str | None = None
    error: str | None = None


class KeyRegistry:
    def __init__(self, configured_slots: Mapping[str, bool] | None = None) -> None:
        self._configured_slots = dict(configured_slots or {})

    def env_var_name(self, key_slot: str) -> str:
        _validate_key_slot(key_slot)
        return KEY_SLOT_ENV_VARS[key_slot]

    def has_key(self, key_slot: str) -> bool:
        _validate_key_slot(key_slot)
        return bool(self._configured_slots.get(key_slot, False))

    def describe_slot(self, key_slot: str) -> KeySlotStatus:
        _validate_key_slot(key_slot)
        configured = self.has_key(key_slot)
        if configured:
            return KeySlotStatus(key_slot, KEY_SLOT_ENV_VARS[key_slot], True)
        return KeySlotStatus(
            key_slot,
            KEY_SLOT_ENV_VARS[key_slot],
            False,
            failure_type="CONFIG_ERROR",
            error=f"missing key for key_slot={key_slot}",
        )

    def describe_all(self) -> list[KeySlotStatus]:
        return [self.describe_slot(key_slot) for key_slot in KEY_SLOTS]

    def raw_key_value(self, key_slot: str) -> str:
        _validate_key_slot(key_slot)
        raise RuntimeError(f"raw key access is disabled in P3B skeleton for key_slot={key_slot}")


def _validate_key_slot(key_slot: str) -> None:
    if key_slot not in KEY_SLOT_ENV_VARS:
        raise ValueError(f"unknown key_slot={key_slot}")
