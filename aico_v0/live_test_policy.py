# P3E live provider 테스트가 기본 pytest에서 실행되지 않도록 정책 helper를 제공한다.
from __future__ import annotations

LIVE_PROVIDER_MARKER = "live_provider"
LIVE_PROVIDER_DEFAULT_ENABLED = False
LIVE_PROVIDER_SKIP_REASON = "live_provider tests are disabled by default in P3E"
LIVE_SMOKE_MARKER = "live_smoke"
LIVE_SMOKE_DEFAULT_ENABLED = False
LIVE_SMOKE_SKIP_REASON = "live_smoke tests are disabled by default in P3G"


def should_skip_live_provider_test(*, explicit_enable: bool = False) -> bool:
    return not explicit_enable or not LIVE_PROVIDER_DEFAULT_ENABLED


def live_provider_marker_policy() -> dict[str, object]:
    return {
        "marker": LIVE_PROVIDER_MARKER,
        "default_enabled": LIVE_PROVIDER_DEFAULT_ENABLED,
        "default_skip": should_skip_live_provider_test(),
        "skip_reason": LIVE_PROVIDER_SKIP_REASON,
    }


def should_skip_live_smoke_test(*, explicit_enable: bool = False) -> bool:
    return not explicit_enable or not LIVE_SMOKE_DEFAULT_ENABLED


def live_smoke_marker_policy() -> dict[str, object]:
    return {
        "marker": LIVE_SMOKE_MARKER,
        "default_enabled": LIVE_SMOKE_DEFAULT_ENABLED,
        "default_skip": should_skip_live_smoke_test(),
        "skip_reason": LIVE_SMOKE_SKIP_REASON,
    }
