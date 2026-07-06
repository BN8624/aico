# P3X가 second-call 및 확장 호출 시도를 artifact 주입으로 차단하는지 검증한다.
from __future__ import annotations

import pytest

from aico_v0.controlled_live_smoke import P3WLiveSmokeError
from aico_v0.negative_safety import validate_p3x_bad_artifact


@pytest.mark.parametrize(
    "payload",
    [
        {"actual_provider_call_count": 2},
        {"call_model_count_after": 2},
        {"model_call_count_after": 2},
        {"call_model_count": 2},
        {"model_call_count": 2},
        {"retry_count": 1},
        {"reserve_used": True},
        {"fallback_used": True},
        {"second_call_attempted": True},
        {"status": "retry_success"},
        {"status": "fallback_success"},
        {"status": "reserve_success"},
    ],
)
def test_second_call_retry_reserve_fallback_injection_blocks(payload: dict[str, object]) -> None:
    with pytest.raises(P3WLiveSmokeError) as exc_info:
        validate_p3x_bad_artifact(payload)
    assert exc_info.value.failure_type == "SECURITY_BLOCKED"
