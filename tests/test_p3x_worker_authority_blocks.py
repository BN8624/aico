# P3X가 bad toy mission과 worker 권한 확장을 차단하는지 검증한다.
from __future__ import annotations

import pytest

from aico_v0.controlled_live_smoke import P3WLiveSmokeError
from aico_v0.negative_safety import validate_p3x_toy_mission


@pytest.mark.parametrize(
    "mission",
    [
        "Edit code in this repo.",
        "Create or modify a file.",
        "Analyze the repository.",
        "Search the web.",
        "Convert this PDF to Excel.",
        "Write a long-form report.",
        "Use multi-step reasoning to solve the task.",
        "Inspect secret env key values.",
        "Call an external system.",
        "Use a tool or function call.",
    ],
)
def test_bad_toy_mission_blocks(mission: str) -> None:
    with pytest.raises(P3WLiveSmokeError) as exc_info:
        validate_p3x_toy_mission(mission)
    assert exc_info.value.failure_type in {"CONFIG_ERROR", "SECURITY_BLOCKED"}
