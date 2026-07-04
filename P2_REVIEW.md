# AICO P2 V0 Dry-Run Hardening Review

## 검토 기준

1. `AICO_MASTER_CANON.md`
2. `AICO_V0_CANON.md`
3. `P2_REVIEW.md`
4. `HANDOFF.md`

## 판정

P3 진입 가능 여부: **YES**

근거.

- V0 Canon Runtime Tests 42개를 `tests/test_v0_harness.py`에 직접 매핑했다.
- `ceo_report.md` 작성 실패 시 `run_log.jsonl`에 `failure_type=REPORT_ERROR`가 기록된다.
- 원래 실패 원인은 별도 failure event와 `REPORT_ERROR.parent_event_id`로 추적 가능하다.
- API 호출 0회, LLM 호출 0회, `semantic_preflight` 미실행, repair loop 미실행 테스트가 통과한다.
- 네트워크, repo clone, web dashboard, GitHub Issue 연동 구현 경로가 없다.

## 변경 요약

- `aico_v0/harness.py`에 `ceo_report.md` 작성 실패 fallback을 추가했다.
- worker result 검증을 추가해 schema error와 bad output을 분리했다.
- secret raw output masking 경로를 테스트 가능하게 만들었다.
- low confidence worker output이 `final_report.md` 승격 근거가 되지 않도록 manager summary에서 reject 처리했다.
- P2 review의 누락 테스트 목록을 기준으로 scenario fixture와 tests를 보강했다.

## V0 Canon Runtime Tests 매핑표

| # | Runtime Test | 직접 테스트 |
|---|---|---|
| 1 | dry-run creates run directory | `test_required_scenarios_are_deterministic_and_offline` |
| 2 | missing mission input/path creates run directory and becomes CONFIG_ERROR | `test_config_error_creates_only_failure_reports` |
| 3 | invalid WorkOrder fails deterministic_preflight | `test_invalid_work_order_fails_preflight_without_semantic_checks` |
| 4 | deterministic_preflight uses only schema, forbidden keywords, permission flags, path scope, secret regex, and budget checks | `test_deterministic_preflight_direct_check_types` |
| 5 | v0 does not run LLM-based semantic_preflight | `test_required_scenarios_are_deterministic_and_offline` |
| 6 | semantic_preflight trace does not exist in v0 run | `test_required_scenarios_are_deterministic_and_offline` |
| 7 | worker output schema error becomes SCHEMA_ERROR | `test_worker_schema_error_becomes_schema_error` |
| 8 | schema-valid but empty/irrelevant worker output becomes WORKER_BAD_OUTPUT | `test_schema_valid_empty_worker_output_becomes_worker_bad_output` |
| 9 | audit fail creates no final_report | `test_fail_scenario_creates_failed_draft_only` |
| 10 | audit fail creates failed_draft only if draft_report exists | `test_fail_scenario_creates_failed_draft_only`, `test_fail_without_draft_creates_no_failed_draft` |
| 11 | audit pass creates final_report | `test_pass_scenario_creates_final_report` |
| 12 | audit conditional creates final_report and ceo_report includes warnings | `test_conditional_scenario_creates_final_report_and_warning` |
| 13 | required_fixes prevents final_report | `test_required_fixes_prevent_final_report_and_false_decision_becomes_fail` |
| 14 | required_fixes + ceo_decision_needed=false becomes FAIL | `test_required_fixes_prevent_final_report_and_false_decision_becomes_fail` |
| 15 | required_fixes + ceo_decision_needed=true becomes NEEDS_DECISION | `test_required_fixes_with_decision_needed_becomes_needs_decision` |
| 16 | needs_decision creates ceo_report and no final_report | `test_needs_decision_scenario_creates_ceo_report_and_no_final` |
| 17 | manager_summary.ceo_decision_needed true creates NEEDS_DECISION | `test_single_source_ceo_decision_needed_becomes_needs_decision` |
| 18 | audit_report.ceo_decision_needed true creates NEEDS_DECISION | `test_single_source_ceo_decision_needed_becomes_needs_decision` |
| 19 | ceo_report exists or REPORT_ERROR is logged | `test_required_scenarios_are_deterministic_and_offline`, `test_ceo_report_write_failure_logs_report_error_and_preserves_original_failure` |
| 20 | run_log failure event includes failure_type | `test_required_scenarios_are_deterministic_and_offline` |
| 21 | raw API key never appears in logs | `test_secret_mission_and_raw_output_are_masked_or_blocked` |
| 22 | worker cannot request shell/file edit | `test_worker_permission_flags_are_blocked`, `test_deterministic_preflight_direct_check_types` |
| 23 | repair loop is not executed | `test_required_scenarios_are_deterministic_and_offline` |
| 24 | mission.md has highest priority within a run | `test_mission_path_is_copied_to_run_mission_md` |
| 25 | v0 makes zero API calls | `test_required_scenarios_are_deterministic_and_offline` |
| 26 | v0 never emits MODEL_ERROR | `test_required_scenarios_are_deterministic_and_offline` |
| 27 | final_report.md and failed_draft.md are mutually exclusive | `test_required_scenarios_are_deterministic_and_offline` |
| 28 | raw_output is masked or blocked when secrets are detected | `test_secret_mission_and_raw_output_are_masked_or_blocked` |
| 29 | references cannot access paths outside allowed workspace/run scope | `test_deterministic_preflight_direct_check_types` |
| 30 | confidence < 0.5 is not used as sole support for final_report | `test_low_confidence_worker_results_are_not_sole_support_for_final_report` |
| 31 | budget exceeded becomes BUDGET_EXCEEDED | `test_budget_exceeded_stops_after_preflight`, `test_more_than_four_work_orders_becomes_budget_exceeded` |
| 32 | mid-flight failure preserves partial worker_results and skips unavailable downstream artifacts | `test_mid_flight_failure_preserves_partial_worker_results` |
| 33 | v0 happy path creates 4 WorkOrders | `test_pass_scenario_creates_final_report` |
| 34 | deterministic_preflight allows 1~4 WorkOrders | `test_deterministic_preflight_allows_one_to_four_work_orders` |
| 35 | more than 4 WorkOrders becomes BUDGET_EXCEEDED | `test_more_than_four_work_orders_becomes_budget_exceeded` |
| 36 | pass scenario is deterministic | `test_required_scenarios_produce_deterministic_artifacts` |
| 37 | conditional scenario is deterministic | `test_required_scenarios_produce_deterministic_artifacts` |
| 38 | fail scenario is deterministic | `test_required_scenarios_produce_deterministic_artifacts` |
| 39 | needs_decision scenario is deterministic | `test_required_scenarios_produce_deterministic_artifacts` |
| 40 | config_error scenario is deterministic | `test_required_scenarios_produce_deterministic_artifacts` |
| 41 | budget_exceeded scenario is deterministic | `test_required_scenarios_produce_deterministic_artifacts` |
| 42 | mid_flight_failure scenario is deterministic | `test_required_scenarios_produce_deterministic_artifacts` |

## 직접 테스트된 항목

- mission input/path 처리와 run directory 생성.
- deterministic preflight의 schema, forbidden keyword, permission, path scope, secret regex, budget 검사.
- `semantic_preflight` trace 부재.
- repair loop 미실행.
- worker schema error와 bad output 실패 분기.
- pass, conditional, fail, needs_decision, config_error, budget_exceeded, mid_flight_failure 결정성.
- `final_report.md`와 `failed_draft.md` 상호배타.
- `ceo_report.md` 생성 성공 또는 `REPORT_ERROR` fallback.
- failure event의 `failure_type` 기록.
- raw key/secret masking 또는 blocking.
- low confidence 결과의 final promotion 차단.
- 외부 capability import 부재.

## 아직 직접 테스트하지 못한 항목

없음. V0 Canon Runtime Tests 42개는 현재 테스트 파일에 직접 매핑되어 있다.

## 남은 위험

- 테스트는 정적 import 문자열 검사로 외부 capability 추가를 막는다. 향후 동적 import나 새 파일이 추가되면 같은 guard를 확장해야 한다.
- `ceo_report.md` fallback은 log write가 가능한 상황을 전제로 한다. 디스크 전체 쓰기 실패처럼 `run_log.jsonl`도 쓸 수 없는 상황은 v0 범위를 벗어난다.
- 현재 fixture 기반 mock은 P2 dry-run에 맞게 의도적으로 단순하다. P3에서는 API worker를 추가하기 전에 v0 offline guard를 유지하는 별도 테스트가 필요하다.

## 검증 결과

- `pytest -q` 결과: `42 passed`.
- API call count: 0.
- LLM call count: 0.
- `semantic_preflight` 실행 흔적: 없음.
- repair loop 실행 흔적: 없음.
- `AGENTS.md`와 `CLAUDE.md`: byte-identical 유지.

## P3 진입 가능 여부

P3 진입 가능 여부: **YES**
