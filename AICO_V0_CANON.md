# AICO_V0_CANON.md

프로젝트명: `aico`
한글명: 아이코
상태: V0 Canon
기준 문서: `AICO_MASTER_CANON.md`

---

# 1. V0 목적

v0는 API 호출 없이 aico의 실행 골격을 검증하는 dry-run 하네스다.

목표:

```text
1. mission input 또는 mission path를 받는다.
2. runs/<run_id>/ 디렉터리를 생성한다.
3. mission.md 로드/복사를 시도한다.
4. mock Manager가 work_orders.json을 생성한다.
5. Harness가 deterministic_preflight를 수행한다.
6. mock Worker가 worker_results.jsonl을 생성한다.
7. mock Manager가 manager_summary.json을 생성한다.
8. mock Auditor가 audit_report.json을 생성한다.
9. Harness가 pass / conditional / fail / needs_decision 상태를 처리한다.
10. final_report.md 또는 failed_draft.md 생성 조건을 검증한다.
11. ceo_report.md 생성을 시도한다.
12. run_log.jsonl을 기록한다.
```

v0는 실제 품질 좋은 답변 생성을 목표로 하지 않는다.
v0의 목표는 파일 흐름, 상태 분기, 실패 처리, 승격 규칙, 로그 규칙이 깨지지 않는지 검증하는 것이다.

---

# 2. V0 포함 범위

v0 포함:

```text
1. API 호출 0회 dry-run
2. mock manager
3. mock worker pool
4. mock auditor
5. deterministic scenario fixture
6. mission input 또는 mission path 입력
7. runs/<run_id>/ 생성
8. mission.md 로드/복사 시도
9. work_orders.json 생성
10. deterministic_preflight 실행
11. preflight_audit.json 생성
12. worker_results.jsonl 생성
13. manager_summary.json 생성
14. audit_report.json 생성
15. final_report.md 생성 조건 처리
16. failed_draft.md 생성 조건 처리
17. ceo_report.md 생성 시도
18. run_log.jsonl 기록
19. pass / conditional / fail / needs_decision 기본 분기
20. config_error / budget_exceeded / mid_flight_failure 분기
21. budget 기본값 적용
22. required tests 작성
```

---

# 3. V0 제외 범위

v0 제외:

```text
1. 실제 API 연결
2. 실제 LLM 호출
3. LLM 기반 semantic_preflight
4. mission 의미론적 모순 판단
5. repair loop 실행
6. 22개 키 사용
7. GitHub Issue 보고
8. CLI agent orchestration
9. worker 파일 수정권
10. worker shell 실행권
11. 웹 대시보드
12. 외부 URL 접근
13. 웹 검색
14. repo clone
15. 자동 PR
16. 자동 merge
```

---

# 4. V0 Runtime Components

```text
Harness
Mock Manager
Mock Worker Pool
Mock Auditor
```

## Harness

책임:

```text
1. mission input 또는 mission path 수신
2. run_id 생성
3. runs/<run_id>/ 생성
4. mission.md 로드/복사 시도
5. mission 로드 실패 처리
6. scenario fixture 적용
7. budget 적용
8. deterministic_preflight 실행
9. mock worker 실행 순서 통제
10. mid-flight failure 처리
11. audit status 처리
12. ceo_decision_needed 병합 처리
13. final_report.md / failed_draft.md 상호배타 보장
14. ceo_report.md 생성 시도
15. run_log.jsonl 기록
16. raw key 미노출 검증
```

## Mock Manager

책임:

```text
1. mission.md 해석
2. internal MissionBrief 생성
3. scenario fixture 기준으로 work_orders.json 생성
4. manager_self_check 포함
5. worker_results.jsonl 취합
6. worker 결과 usable 판정
7. manager_summary.json 생성
8. draft_report 필드 생성
9. ceo_decision_needed 표시
```

## Mock Worker Pool

규칙:

```text
1. v0 happy path는 WorkOrder 4개를 생성하고 mock worker 4개를 실행한다.
2. deterministic_preflight는 WorkOrder 1~4개를 허용한다.
3. 테스트/실패 케이스에서는 1~3개 WorkOrder도 허용한다.
4. max_workers = 4를 초과하면 BUDGET_EXCEEDED로 처리한다.
5. 각 worker는 WorkOrder 하나를 처리한다.
6. worker는 파일을 수정하지 않는다.
7. worker는 shell을 실행하지 않는다.
8. worker는 외부 접근을 하지 않는다.
9. worker output은 공통 WorkerResult wrapper를 따른다.
```

## Mock Auditor

책임:

```text
1. manager_summary.json을 읽는다.
2. scenario fixture 기준으로 audit_report.json을 생성한다.
3. status를 pass / conditional / fail 중 하나로 지정한다.
4. blocking / warnings / required_fixes / ceo_decision_needed를 기록한다.
```

---

# 5. V0 Scenario Fixtures

v0의 상태 분기는 의미판단이 아니라 deterministic scenario fixture로 재현한다.

필수 scenario:

```text
pass
conditional
fail
needs_decision
config_error
budget_exceeded
mid_flight_failure
required_fixes
worker_bad_output
schema_error
security_blocked
```

규칙:

```text
1. mock은 랜덤 값을 사용하지 않는다.
2. mock은 LLM 호출을 하지 않는다.
3. mock 결과는 fixture 또는 명시적 scenario 값으로만 결정한다.
4. 같은 scenario는 항상 같은 artifact 구조를 만든다.
5. needs_decision은 mission 의미판단이 아니라 scenario fixture 또는 명시적 marker로만 발생시킨다.
6. v0는 mission의 의미론적 모순을 판단하지 않는다.
7. semantic contradiction 판단은 이후 Phase에서 다룬다.
```

예시:

```text
scenario = pass
scenario = conditional
scenario = fail
scenario = needs_decision
scenario = mid_flight_failure
```

---

# 6. V0 Budget

v0 budget 기본값:

```text
max_workers = 4
max_repair_loops = 0
max_model_calls = 0
max_input_tokens = 0
max_output_tokens = 0
max_runtime_seconds = 30
```

규칙:

```text
1. v0는 API 호출을 하지 않는다.
2. max_model_calls는 반드시 0이다.
3. repair loop는 실행하지 않는다.
4. max_workers를 초과하면 BUDGET_EXCEEDED로 중단한다.
5. runtime budget 초과 시 BUDGET_EXCEEDED로 중단한다.
6. budget 초과 시 ceo_report.md 생성을 시도하고 run_log.jsonl에 기록한다.
```

---

# 7. Run Directory

v0 실행 결과는 다음 구조를 따른다.

```text
runs/<run_id>/
  mission.md
  work_orders.json
  preflight_audit.json
  worker_results.jsonl
  manager_summary.json
  audit_report.json
  final_report.md        # pass/conditional only
  failed_draft.md        # fail/needs_decision only, if draft_report exists
  ceo_report.md
  run_log.jsonl
```

규칙:

```text
1. final_report.md와 failed_draft.md는 같은 run에서 동시에 생성하지 않는다.
2. pass 또는 conditional이면 final_report.md 생성 가능.
3. fail 또는 needs_decision이면 final_report.md 생성 금지.
4. fail 또는 needs_decision에서 draft_report가 존재하면 failed_draft.md 생성 가능.
5. fail 또는 needs_decision에서 draft_report가 없으면 failed_draft.md를 생성하지 않는다.
6. 모든 상태에서 ceo_report.md 생성을 시도한다.
7. ceo_report.md 생성 실패 시 REPORT_ERROR를 run_log.jsonl에 기록한다.
8. 모든 상태에서 run_log.jsonl 생성을 시도한다.
9. mission load 실패 run에서는 runs/<run_id>/mission.md가 없을 수 있다.
10. mission load 실패 run에서는 ceo_report.md와 run_log.jsonl만 생성될 수 있다.
```

---

# 8. Execution Flow

```text
1. Supported entrypoint가 mission input 또는 mission path를 받는다.
2. Harness가 run_id를 생성한다.
3. Harness가 runs/<run_id>/를 생성한다.
4. Harness가 mission.md 로드/복사를 시도한다.
5. mission input이 없거나 로드 실패 시 CONFIG_ERROR로 중단한다.
6. mission 로드 성공 시 scenario fixture를 확정한다.
7. Mock Manager가 internal MissionBrief를 생성한다.
8. Mock Manager가 work_orders.json을 생성한다.
9. Harness가 deterministic_preflight를 실행한다.
10. Harness가 preflight_audit.json을 생성한다.
11. preflight pass이면 mock worker를 실행한다.
12. worker_results.jsonl을 생성한다.
13. Mock Manager가 manager_summary.json을 생성한다.
14. Mock Auditor가 audit_report.json을 생성한다.
15. Harness가 audit status와 ceo_decision_needed를 병합한다.
16. Harness가 final_report.md 또는 failed_draft.md 생성 조건을 처리한다.
17. Harness가 ceo_report.md 생성을 시도한다.
18. Harness가 run_log.jsonl을 기록한다.
```

mission 로드 실패 처리:

```text
1. runs/<run_id>/는 생성된 상태여야 한다.
2. mission.md가 없거나 로드 실패하면 CONFIG_ERROR로 처리한다.
3. runs/<run_id>/mission.md는 없을 수 있다.
4. 가능한 경우 ceo_report.md 생성을 시도한다.
5. run_log.jsonl에 CONFIG_ERROR를 기록한다.
6. worker, manager_summary, audit_report, final_report는 생성하지 않는다.
```

---

# 9. deterministic_preflight

v0에서는 deterministic_preflight만 수행한다.
LLM 기반 semantic_preflight는 수행하지 않는다.

체크 항목:

```text
1. WorkOrder 수가 1~4 범위인가
2. WorkOrder 수가 max_workers 이하인가
3. work_orders.json 필수 필드가 있는가
4. 각 WorkOrder 필수 필드가 있는가
5. 필드 타입이 맞는가
6. output_schema가 있는가
7. forbidden이 있는가
8. manager_self_check가 있는가
9. forbidden keywords 위반이 없는가
10. permission flags가 파일 수정권이나 shell 실행권을 허용하지 않는가
11. references와 input_scope가 허용된 workspace/run scope 안에 있는가
12. secret regex에 걸리는 API key/token/credential이 없는가
13. budget을 초과하지 않았는가
```

v0 deterministic_preflight 범위:

```text
1. schema 검사
2. 필수 필드 검사
3. 타입 검사
4. WorkOrder 개수 검사
5. forbidden keywords 검사
6. permission flags 검사
7. path scope 검사
8. secret regex 검사
9. budget 검사
```

금지:

```text
1. 의미론적 판단 금지
2. mission 핵심 요구 반영 여부를 fail 조건으로 사용 금지
3. input_scope가 과도하게 넓은지 의미 판단 금지
4. WorkOrder 중복 과다 여부를 의미 판단으로 fail 처리 금지
5. role과 task 적절성 의미 판단 금지
```

판단이 애매한 항목은 `manager_self_check`에 기록만 하고 deterministic_preflight fail 조건으로 사용하지 않는다.

처리:

```text
pass:
- worker 실행

fail:
- worker 실행 중단
- preflight_audit.json 저장
- ceo_report.md 생성 시도
- run_log.jsonl 기록
```

가능 failure_type:

```text
MANAGER_BAD_PLAN
SCHEMA_ERROR
SECURITY_BLOCKED
BUDGET_EXCEEDED
```

---

# 10. V0 Forbidden Baseline

forbidden keyword baseline:

```text
final answer
final_report
최종 결론
전체 계획 재작성
알아서
파일 수정
file edit
shell
command
실행해
API key
token
credential
```

permission flag baseline:

```text
allow_file_edit = true
allow_shell = true
allow_network = true
allow_external_url = true
allow_repo_clone = true
```

secret regex baseline:

```text
API key pattern
Bearer token pattern
credential assignment pattern
private key block pattern
```

처리 규칙:

```text
1. forbidden keyword hit은 기본 MANAGER_BAD_PLAN.
2. secret regex hit은 SECURITY_BLOCKED.
3. shell/file/network permission flag hit은 SECURITY_BLOCKED.
4. WorkOrder 수 > max_workers는 BUDGET_EXCEEDED.
5. WorkOrder schema 오류는 SCHEMA_ERROR.
```

---

# 11. semantic_preflight

v0에서는 LLM 기반 semantic_preflight를 실행하지 않는다.

v0 규칙:

```text
1. semantic_preflight는 disabled.
2. semantic_preflight 결과 파일을 별도 생성하지 않는다.
3. manager_self_check의 존재와 형식만 deterministic_preflight로 검사한다.
4. mission 핵심 요구 반영 여부 같은 의미론적 평가는 v0에서 강제하지 않는다.
5. v0 run에서 semantic_preflight 실행 흔적이 있으면 테스트 실패다.
```

---

# 12. mission.md

권장 필드:

```text
goal
output
must_include
must_avoid
constraints
references
decision_needed
scenario
```

v0 처리 규칙:

```text
1. mission.md는 실행 단위의 최상위 기준이다.
2. mission.md가 없으면 CONFIG_ERROR.
3. mission.md가 비어 있으면 CONFIG_ERROR.
4. v0는 mission.md의 의미론적 모순을 판단하지 않는다.
5. needs_decision은 scenario fixture 또는 명시적 marker로만 발생시킨다.
6. references는 사용자 제공 텍스트 또는 허용된 workspace/run directory 내부 경로만 허용한다.
7. 외부 URL 접근, 웹 검색, repo clone은 수행하지 않는다.
```

---

# 13. work_orders.json

기본 구조:

```json
{
  "mission_interpretation": {},
  "work_orders": [],
  "manager_self_check": {
    "mission_coverage_summary": "string",
    "input_scope_rationale": "string",
    "duplicate_risk": "low | medium | high",
    "known_gaps": []
  }
}
```

규칙:

```text
1. work_orders 배열 길이는 1~4.
2. v0 happy path는 work_orders 4개를 생성한다.
3. 테스트/실패 케이스에서는 1~3개 WorkOrder도 허용한다.
4. max_workers = 4를 초과하면 BUDGET_EXCEEDED로 처리한다.
5. 각 WorkOrder는 하나의 mock worker에 대응한다.
6. manager_self_check는 semantic_preflight를 대체하지 않는다.
7. v0에서는 manager_self_check의 존재와 형식만 검사한다.
```

---

# 14. WorkOrder Schema

필수 필드:

```text
work_id
role
task
input_scope
output_schema
forbidden
acceptance_condition
```

금지 패턴:

```text
1. 전체적으로 검토
2. 알아서 정리
3. 좋은 의견 제시
4. 최종 결론 작성
5. 전체 계획 재작성
6. 파일 수정
7. shell 실행
8. mission 수정
9. secret/API key 포함
```

v0 기본 WorkOrder role 예시:

```text
requirements_checker
risk_finder
structure_planner
report_reviewer
```

---

# 15. worker_results.jsonl

각 line은 공통 wrapper를 따른다.
worker별 고유 산출물은 `payload` 필드에 저장한다.

필수 필드:

```text
work_id
role
summary
findings
risks
recommendations
confidence
payload
masked_raw_output
raw_output_saved
mask_reason
```

예시:

```json
{
  "work_id": "W001",
  "role": "risk_finder",
  "summary": "핵심 위험 2개 발견",
  "findings": [],
  "risks": [],
  "recommendations": [],
  "confidence": 0.72,
  "payload": {
    "risks": [
      {
        "risk": "string",
        "why": "string",
        "fix_hint": "string"
      }
    ]
  },
  "masked_raw_output": "...",
  "raw_output_saved": false,
  "mask_reason": null
}
```

confidence 규칙:

```text
1. confidence는 0.0~1.0 숫자 또는 null.
2. confidence < 0.5인 결과는 단독 근거로 final_report에 반영하지 않는다.
3. confidence가 null이면 낮은 confidence와 동일하게 취급한다.
4. 낮은 confidence는 짧게 다룬다.
```

저장 규칙:

```text
1. masked_raw_output을 기본 저장 필드로 사용한다.
2. raw_output 저장 금지가 기본이다.
3. raw_output_saved는 false를 기본값으로 한다.
4. v0 mock output에도 secret masking 검사를 적용한다.
5. secret 감지 시 SECURITY_BLOCKED 또는 masking 처리한다.
```

---

# 16. WorkerResult 품질 판정

Mock Manager는 각 WorkerResult에 대해 품질 판정을 기록한다.

필수 판정 필드:

```text
usable: yes | partial | no
reason
used_by_manager: yes | no
discarded_reason
```

규칙:

```text
1. schema 오류는 SCHEMA_ERROR.
2. schema는 맞지만 내용이 비어 있으면 WORKER_BAD_OUTPUT.
3. role/task와 무관한 응답은 WORKER_BAD_OUTPUT.
4. forbidden 위반은 WORKER_BAD_OUTPUT 또는 SECURITY_BLOCKED.
5. confidence < 0.5인 결과는 단독 근거로 사용하지 않는다.
```

---

# 17. manager_summary.json

필수 필드:

```text
mission_interpretation
used_worker_results
rejected_worker_results
conflicts
gaps
repair_needed
repair_orders
draft_report
remaining_risks
worker_quality_summary
ceo_decision_needed
```

draft_report 규칙:

```text
1. draft_report는 manager_summary.json 내부 필드다.
2. draft_report는 별도 파일이 아니다.
3. draft_report는 final_report가 아니다.
4. fail 또는 needs_decision에서 failed_draft.md가 필요한 경우 Harness가 draft_report를 추출해 failed_draft.md로 저장한다.
```

v0 repair 규칙:

```text
1. repair_needed는 기록 가능.
2. repair_orders는 기록 가능.
3. repair loop는 실행하지 않는다.
```

---

# 18. audit_report.json

필수 필드:

```text
status
blocking
warnings
mission_coverage
required_fixes
ceo_decision_needed
summary
```

status 값:

```text
pass
conditional
fail
```

규칙:

```text
1. blocking이 있으면 status = fail.
2. warnings만 있으면 status = conditional 가능.
3. required_fixes가 비어 있지 않으면 final_report 승격 금지.
4. v0에서는 repair 실행 금지이므로 required_fixes 존재 시 final_report 생성 금지.
5. required_fixes가 있고 ceo_decision_needed = true이면 최종 상태는 NEEDS_DECISION.
6. required_fixes가 있고 ceo_decision_needed = false이면 최종 상태는 FAIL.
7. ceo_decision_needed = true이면 최종 상태는 NEEDS_DECISION.
```

---

# 19. ceo_decision_needed 병합

규칙:

```text
1. manager_summary.ceo_decision_needed 또는 audit_report.ceo_decision_needed 중 하나라도 true이면 최종 상태는 NEEDS_DECISION.
2. 둘 다 false일 때만 pass / conditional / fail 자동 처리를 계속한다.
3. audit_report.ceo_decision_needed = true는 manager_summary 판단을 덮어쓸 수 있다.
```

---

# 20. final_report 승격

final_report.md 생성 조건:

```text
1. deterministic_preflight pass
2. worker_results.jsonl 존재
3. manager_summary.json 존재
4. audit_report.json 존재
5. audit status = pass 또는 conditional
6. blocking 없음
7. required_fixes 없음
8. 최종 ceo_decision_needed = false
```

상호배타 규칙:

```text
1. final_report.md와 failed_draft.md는 동시에 생성하지 않는다.
2. final_report.md는 승격 산출물이다.
3. failed_draft.md는 검토용 산출물이며 정본이 아니다.
```

---

# 21. failed_draft.md

생성 조건:

```text
1. final_report.md 생성 금지 상태
2. manager_summary.json이 존재
3. draft_report가 존재
4. 상태가 fail 또는 needs_decision
```

생성 금지:

```text
1. pass 상태
2. conditional 상태
3. final_report.md가 이미 생성된 상태
4. draft_report가 없는 상태
```

규칙:

```text
1. failed_draft.md는 검토용 산출물이다.
2. failed_draft.md는 final_report.md가 아니다.
3. failed_draft.md를 정본으로 취급하지 않는다.
```

---

# 22. ceo_report.md

필수 섹션:

```text
상태: PASS | CONDITIONAL | FAIL | NEEDS_DECISION

결론
최종 산출물
이번 실행에서 한 일
핵심 결정
남은 위험
감사 결과
대표 판단 필요 여부
다음 행동
```

길이 제한:

```text
1. 기본 600자 이내 목표
2. 최대 1,200자
3. 핵심 결정 최대 5개
4. 남은 위험 최대 5개
5. 대표 판단 필요 항목 최대 3개
6. worker 원문 금지
7. 내부 JSON 덤프 금지
```

생성 규칙:

```text
1. 모든 실행은 ceo_report.md 생성을 시도한다.
2. ceo_report.md 생성 실패 시 REPORT_ERROR를 run_log.jsonl에 기록한다.
```

상태 규칙:

```text
PASS:
- final_report 생성됨
- blocking 없음
- required_fixes 없음
- 최종 ceo_decision_needed = false

CONDITIONAL:
- final_report 생성 가능
- warnings 존재 가능
- blocking 없음
- required_fixes 없음
- 최종 ceo_decision_needed = false

FAIL:
- final_report 없음
- 시스템/산출물 실패
- 자동 진행 불가

NEEDS_DECISION:
- final_report 없음
- 대표 판단 필요
- 시스템 실패가 아니라 선택/충돌/범위 문제
```

---

# 23. Failure Types

```text
CONFIG_ERROR
- mission.md 없음, mission input 없음, 설정 누락, 필수 입력 누락

SCHEMA_ERROR
- JSON 파싱 실패, 필수 필드 누락, 필드 타입 불일치

MANAGER_BAD_PLAN
- 잘못된 WorkOrder 생성

WORKER_BAD_OUTPUT
- worker 결과 없음, 역할 밖 응답, 형식은 맞지만 내용 불량

AUDIT_FAIL
- final audit 실패

BUDGET_EXCEEDED
- worker 수, repair loop, runtime 한도 초과

HUMAN_DECISION_REQUIRED
- 대표 판단 없이는 진행 불가

SECURITY_BLOCKED
- 금지된 파일 수정, shell 실행, key 노출, 외부 실행 시도

REPORT_ERROR
- ceo_report.md, final_report.md, failed_draft.md 등 보고 산출물 생성 실패

UNKNOWN_ERROR
- 분류되지 않은 오류
```

v0에서 발생하지 않아야 하는 failure_type:

```text
MODEL_ERROR
```

규칙:

```text
1. v0는 MODEL_ERROR를 생성하지 않는다.
2. MODEL_ERROR가 run_log.jsonl에 나타나면 v0 구현 실패다.
3. v0에서 모델 호출 시도가 감지되면 테스트 실패다.
```

---

# 24. run_log.jsonl

이벤트 필드:

```text
timestamp
event_type
actor
model
key_slot
input_tokens
output_tokens
status
failure_type
error
artifact_path
parent_event_id
```

v0 규칙:

```text
1. model = null 허용.
2. key_slot = null 허용.
3. input_tokens = 0.
4. output_tokens = 0.
5. failure_type은 정의된 enum 값만 사용한다.
6. failure가 아닌 이벤트에서는 failure_type = null을 허용한다.
7. raw API key 기록 금지.
8. 실패 원인 기록.
9. ceo_report 생성 실패도 기록.
10. MODEL_ERROR는 v0에서 허용하지 않는다.
```

---

# 25. Mid-flight Failure

worker 실행 중 일부 worker만 성공한 상태에서 실패가 발생할 수 있다.

처리 규칙:

```text
1. 이미 생성된 worker_results.jsonl은 보존한다.
2. 실패 이후 남은 worker는 실행하지 않는다.
3. manager_summary.json은 생성 조건을 충족하지 않으면 생성하지 않는다.
4. audit_report.json은 생성 조건을 충족하지 않으면 생성하지 않는다.
5. final_report.md는 생성하지 않는다.
6. draft_report가 없으면 failed_draft.md도 생성하지 않는다.
7. ceo_report.md 생성을 시도한다.
8. ceo_report.md 생성 실패 시 REPORT_ERROR를 run_log.jsonl에 기록한다.
9. run_log.jsonl에는 원래 failure_type을 기록한다.
```

예시:

```text
worker 1 성공
worker 2 성공
worker 3 실패: BUDGET_EXCEEDED
→ worker_results.jsonl에는 worker 1, 2 결과 보존
→ worker 4 실행 안 함
→ manager_summary.json 없음
→ audit_report.json 없음
→ final_report.md 없음
→ failed_draft.md 없음
→ ceo_report.md 생성 시도
→ run_log.jsonl에 BUDGET_EXCEEDED 기록
```

---

# 26. Security

금지:

```text
1. API key를 prompt에 포함
2. raw API key를 log/report에 기록
3. worker에게 shell 실행권 제공
4. worker에게 파일 수정권 제공
5. unknown repo clone 후 자동 실행
6. 외부 URL 임의 실행
7. 보안/계정/결제 작업 자동 수행
8. 감사 없는 final_report 생성
9. 실패 로그 숨김
```

v0 규칙:

```text
1. 실제 API key를 사용하지 않는다.
2. key_slot은 null 또는 mock slot만 허용한다.
3. mock output에도 secret scan을 적용한다.
```

---

# 27. Runtime Tests

```text
1. dry-run creates run directory
2. missing mission input/path creates run directory and becomes CONFIG_ERROR
3. invalid WorkOrder fails deterministic_preflight
4. deterministic_preflight uses only schema, forbidden keywords, permission flags, path scope, secret regex, and budget checks
5. v0 does not run LLM-based semantic_preflight
6. semantic_preflight trace does not exist in v0 run
7. worker output schema error becomes SCHEMA_ERROR
8. schema-valid but empty/irrelevant worker output becomes WORKER_BAD_OUTPUT
9. audit fail creates no final_report
10. audit fail creates failed_draft only if draft_report exists
11. audit pass creates final_report
12. audit conditional creates final_report and ceo_report includes warnings
13. required_fixes prevents final_report
14. required_fixes + ceo_decision_needed=false becomes FAIL
15. required_fixes + ceo_decision_needed=true becomes NEEDS_DECISION
16. needs_decision creates ceo_report and no final_report
17. manager_summary.ceo_decision_needed true creates NEEDS_DECISION
18. audit_report.ceo_decision_needed true creates NEEDS_DECISION
19. ceo_report exists or REPORT_ERROR is logged
20. run_log failure event includes failure_type
21. raw API key never appears in logs
22. worker cannot request shell/file edit
23. repair loop is not executed
24. mission.md has highest priority within a run
25. v0 makes zero API calls
26. v0 never emits MODEL_ERROR
27. final_report.md and failed_draft.md are mutually exclusive
28. raw_output is masked or blocked when secrets are detected
29. references cannot access paths outside allowed workspace/run scope
30. confidence < 0.5 is not used as sole support for final_report
31. budget exceeded becomes BUDGET_EXCEEDED
32. mid-flight failure preserves partial worker_results and skips unavailable downstream artifacts
33. v0 happy path creates 4 WorkOrders
34. deterministic_preflight allows 1~4 WorkOrders
35. more than 4 WorkOrders becomes BUDGET_EXCEEDED
36. pass scenario is deterministic
37. conditional scenario is deterministic
38. fail scenario is deterministic
39. needs_decision scenario is deterministic
40. config_error scenario is deterministic
41. budget_exceeded scenario is deterministic
42. mid_flight_failure scenario is deterministic
```

---

# 28. Repository Tests

```text
1. AGENTS.md and CLAUDE.md are byte-identical
2. AICO_MASTER_CANON.md exists
3. AICO_V0_CANON.md exists
4. HANDOFF.md exists
5. CONTEXT_NOTES.md exists
```

---

# 29. Success Criteria

```text
1. Supported entrypoint accepts mission input.
2. runs/<run_id>/ is created before mission load failure is finalized.
3. Required artifacts are generated according to status.
4. Failure path produces ceo_report.md or logs REPORT_ERROR.
5. Failure path produces run_log.jsonl.
6. No raw key appears in artifacts.
7. final_report is generated only by promotion rules.
8. failed_draft is never treated as final_report.
9. worker performs bounded tasks only.
10. manager records used/rejected worker results.
11. auditor records blocking/warnings/required_fixes.
12. deterministic_preflight blocks invalid WorkOrder.
13. deterministic_preflight performs no semantic judgment.
14. semantic_preflight is not executed in v0.
15. v0 makes zero API calls.
16. v0 can demonstrate pass, conditional, fail, needs_decision, config_error, budget_exceeded, and mid-flight failure paths.
```
