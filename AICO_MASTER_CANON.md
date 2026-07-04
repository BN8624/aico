# AICO_MASTER_CANON.md

프로젝트명: `aico`
한글명: 아이코
상태: Master Canon / FREEZE

---

# 1. 목적

aico는 `mission.md`를 입력받아 작업을 분해하고, worker 실행 결과를 취합·감사한 뒤, 최종 산출물과 대표 보고서를 생성하는 파일 기반 하네스다.

기본 흐름:

```text id="h6v44e"
mission.md
→ Harness
→ Manager
→ work_orders.json
→ Worker Pool
→ worker_results.jsonl
→ Manager
→ manager_summary.json
→ Auditor
→ audit_report.json
→ final_report.md 또는 failed_draft.md
→ ceo_report.md
→ run_log.jsonl
```

목표:

```text id="twk5rg"
1. 사용자는 mission과 최종 보고만 다룬다.
2. worker는 작은 작업만 수행한다.
3. manager는 작업 분해, 결과 취합, 압축을 담당한다.
4. auditor는 mission 기준으로 검산한다.
5. 실패는 숨기지 않고 ceo_report에 보고한다.
6. 모든 실행은 파일과 로그로 남긴다.
```

---

# 2. Canon 운영

```text id="99pk5u"
AICO_MASTER_CANON.md
→ AICO_V0_CANON.md
→ v0 구현
→ v0 실행 결과 기록
→ AICO_MASTER_CANON.md 수정
→ AICO_V1_CANON.md
```

규칙:

```text id="fdwtob"
1. Master Canon은 프로젝트 방향의 최상위 기준이다.
2. Phase Canon은 Master Canon에서 추출한다.
3. Phase Canon은 해당 Phase의 구현 범위만 다룬다.
4. Phase 결과는 Master Canon 수정 근거가 된다.
5. 구현 결과가 Master Canon을 자동 대체하지 않는다.
6. v0를 작게 만들되 전체 목표를 v0 수준으로 축소하지 않는다.
```

---

# 3. Runtime Components

```text id="6y054w"
Harness
Manager
Worker Pool
Auditor
```

## Harness

책임:

```text id="h2e01e"
1. run_id 생성
2. runs/<run_id>/ 생성
3. 실행 순서 통제
4. 스키마 검사
5. deterministic_preflight 실행
6. semantic_preflight 허용 여부 적용
7. worker 수 제한
8. repair loop 제한
9. budget 제한 적용
10. audit status 처리
11. final_report.md / failed_draft.md 생성 조건 처리
12. ceo_report.md 생성 시도
13. 산출물 저장
14. run_log 기록
15. key/secret 보호
```

## Manager

책임:

```text id="gpa9qx"
1. mission.md 해석
2. internal MissionBrief 생성
3. work_orders.json 생성
4. work_orders.json에 manager_self_check 포함
5. WorkerResult 취합
6. 중복 제거
7. 충돌 정리
8. 누락 확인
9. worker 결과 품질 판정
10. manager_summary.json 생성
11. draft_report 작성
12. 대표 판단 필요 여부 표시
```

규칙:

```text id="erccut"
1. Manager 출력은 지정된 JSON artifact로만 수용한다.
2. work_orders.json과 manager_summary.json은 schema validation을 통과해야 한다.
3. schema validation 실패 시 worker 실행 또는 final_report 승격을 중단한다.
```

금지:

```text id="t8j9e4"
1. mission.md 임의 변경
2. worker 원문 그대로 붙여넣기
3. audit 생략
4. 무한 repair
5. final_report 직접 승격
```

## Worker Pool

규칙:

```text id="n6e9mx"
1. worker는 고정 직책이 아니라 실행 슬롯이다.
2. role은 WorkOrder마다 임시 배정한다.
3. worker는 WorkOrder 범위 안에서만 답한다.
4. worker는 최종 결론을 작성하지 않는다.
5. worker는 mission을 수정하지 않는다.
6. worker는 파일을 수정하지 않는다.
7. worker는 shell을 실행하지 않는다.
8. worker끼리 직접 대화하지 않는다.
9. 모르면 unknown으로 표시한다.
10. confidence를 표시한다.
```

## Auditor

책임:

```text id="lhh5tv"
1. mission 반영 여부 확인
2. must_include 누락 확인
3. must_avoid 위반 확인
4. output_format 충족 확인
5. 내부 모순 확인
6. 근거 없는 핵심 주장 확인
7. 대표 판단 필요 항목 확인
8. BLOCKING / WARNING 분류
9. required_fixes 기록
10. audit_report.json 생성
```

---

# 4. File Priority

프로젝트 기준:

```text id="lv8b39"
1. AICO_MASTER_CANON.md
2. 현재 Phase Canon
3. AGENTS.md / CLAUDE.md
4. HANDOFF.md
5. CONTEXT_NOTES.md
```

실행 기준:

```text id="klco9b"
1. mission.md
2. internal MissionBrief
3. work_orders.json
4. preflight_audit.json
5. worker_results.jsonl
6. manager_summary.json
7. audit_report.json
8. final_report.md / failed_draft.md
9. ceo_report.md
10. run_log.jsonl
```

규칙:

```text id="omoxgt"
1. 상위 문서를 하위 문서가 바꾸지 않는다.
2. 프로젝트 방향 충돌은 Master Canon 기준으로 해결한다.
3. 실행 내부 충돌은 mission.md 기준으로 해결한다.
```

---

# 5. Repository Documents

Core docs:

```text id="h31g6r"
AICO_MASTER_CANON.md
AGENTS.md
CLAUDE.md
HANDOFF.md
CONTEXT_NOTES.md
```

Phase docs:

```text id="zqugxj"
AICO_V0_CANON.md
AICO_V1_CANON.md
...
```

규칙:

```text id="d8jtqg"
1. AGENTS.md와 CLAUDE.md는 byte-identical이어야 한다.
2. AGENTS.md와 CLAUDE.md는 문서 지도와 작업 규칙만 담는다.
3. AGENTS.md와 CLAUDE.md가 달라지면 documentation sync failure로 간주한다.
4. HANDOFF.md는 현재 상태와 다음 작업만 담는다.
5. CONTEXT_NOTES.md는 판단 배경과 보류 아이디어만 담는다.
6. 구현 규칙은 Master Canon 또는 Phase Canon에 둔다.
```

---

# 6. Run Directory

기본 구조:

```text id="3wpbp7"
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

```text id="j6l8qc"
1. final_report.md와 failed_draft.md는 같은 run에서 동시에 생성하지 않는다.
2. pass 또는 conditional이면 final_report.md 생성 가능.
3. fail 또는 needs_decision이면 final_report.md 생성 금지.
4. fail 또는 needs_decision에서 draft_report가 존재하면 failed_draft.md 생성 가능.
5. fail 또는 needs_decision에서 draft_report가 없으면 failed_draft.md를 생성하지 않는다.
6. failed_draft.md는 검토용 산출물이며 정본이 아니다.
7. 모든 상태에서 ceo_report.md 생성을 시도한다.
8. ceo_report.md 생성 실패 시 REPORT_ERROR를 run_log.jsonl에 기록한다.
9. 모든 상태에서 run_log.jsonl 생성을 시도한다.
```

---

# 7. Execution Flow

```text id="8l16ax"
1. mission.md 입력
2. Harness가 run_id 생성
3. Harness가 runs/<run_id>/ 생성
4. Manager가 internal MissionBrief 생성
5. Manager가 work_orders.json 생성
6. Harness가 deterministic_preflight 실행
7. Phase Canon이 허용한 경우 semantic_preflight 실행
8. preflight pass이면 worker 실행
9. worker_results.jsonl 생성
10. Manager가 manager_summary.json 생성
11. Auditor가 audit_report.json 생성
12. Harness가 audit status와 ceo_decision_needed 병합 규칙 처리
13. final_report.md 또는 failed_draft.md 생성 조건 처리
14. ceo_report.md 생성 시도
15. run_log.jsonl 기록
```

실패 중단 지점:

```text id="9a0r7p"
1. mission 모순
2. preflight fail
3. worker schema fail
4. worker 실행 중 실패
5. manager_summary 생성 실패
6. audit fail
7. security block
8. budget exceeded
9. human decision required
10. report generation failure
```

실패 중단 시:

```text id="whh00x"
1. 가능한 산출물 저장
2. failure_type 기록
3. ceo_report.md 생성 시도
4. run_log.jsonl 기록
```

Worker 실행 중 일부 worker만 성공한 상태에서 실패가 발생하면, 이미 생성된 `worker_results.jsonl`은 보존한다. `manager_summary.json`, `audit_report.json`, `final_report.md`, `failed_draft.md`는 생성 조건을 충족하지 않으면 만들지 않는다. Harness는 `ceo_report.md` 생성을 시도하고, 실패 시 `REPORT_ERROR`를 `run_log.jsonl`에 기록한다.

---

# 8. mission.md

권장 필드:

```text id="4z39qj"
goal
output
must_include
must_avoid
constraints
references
decision_needed
```

처리 규칙:

```text id="62rm0x"
1. mission.md는 실행 단위의 최상위 기준이다.
2. mission.md가 불명확하면 internal MissionBrief로 정리한다.
3. internal MissionBrief는 mission.md보다 우선하지 않는다.
4. mission.md가 모순되면 HUMAN_DECISION_REQUIRED.
5. must_include와 must_avoid가 충돌하면 HUMAN_DECISION_REQUIRED.
6. references는 사용자 제공 텍스트, 허용된 workspace/run directory 내부 경로, 또는 명시적으로 허용된 자료만 의미한다.
7. 외부 URL 접근, 웹 검색, repo clone은 Phase Canon에서 명시적으로 허용된 경우에만 수행한다.
```

---

# 9. internal MissionBrief

필드:

```text id="48xezv"
title
goal
must_include
must_avoid
success_criteria
output_format
constraints
budget
stop_conditions
```

저장 규칙:

```text id="io47cw"
1. 별도 파일 생성은 Phase Canon에서 정한다.
2. v0에서는 manager_summary.json의 mission_interpretation에 포함 가능.
3. mission.md와 충돌하면 mission.md가 우선한다.
```

---

# 10. Budget

budget 항목:

```text id="476l88"
max_workers
max_repair_loops
max_model_calls
max_input_tokens
max_output_tokens
max_runtime_seconds
```

규칙:

```text id="ajh8gs"
1. budget 값은 Phase Canon에서 정의한다.
2. budget 초과 시 BUDGET_EXCEEDED로 중단한다.
3. v0 max_model_calls = 0.
4. repair loop는 Phase Canon에서 허용된 경우에만 실행한다.
```

---

# 11. work_orders.json

기본 구조:

```json id="2s6fb7"
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

```text id="px84vn"
1. worker 호출은 work_orders 배열의 WorkOrder를 통해서만 수행한다.
2. manager_self_check는 semantic_preflight를 대체하지 않는다.
3. v0에서는 manager_self_check의 존재와 형식만 deterministic_preflight로 검사한다.
4. semantic_preflight는 Phase Canon에서 허용한 경우에만 의미론적 판단으로 수행한다.
```

---

# 12. WorkOrder

필수 필드:

```text id="dsf3g6"
work_id
role
task
input_scope
output_schema
forbidden
acceptance_condition
```

금지 패턴:

```text id="5gbfgg"
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

예시:

```json id="fcgx2t"
{
  "work_id": "W001",
  "role": "risk_finder",
  "task": "mission.md와 internal MissionBrief 기준으로 실패 가능성이 높은 지점만 찾아라.",
  "input_scope": ["mission.md", "internal_mission_brief"],
  "output_schema": {
    "risks": [
      {
        "risk": "string",
        "why": "string",
        "fix_hint": "string"
      }
    ]
  },
  "forbidden": [
    "final answer",
    "rewrite whole plan",
    "file edit",
    "shell execution",
    "mission modification"
  ],
  "acceptance_condition": "구체적 risk, why, fix_hint가 있어야 한다."
}
```

---

# 13. Preflight Audit

Preflight Audit은 두 층으로 나눈다.

```text id="hx397t"
deterministic_preflight
semantic_preflight
```

## deterministic_preflight

Harness가 코드로 수행한다.

체크 항목:

```text id="zogfr3"
1. WorkOrder 수가 Phase 한도 안인가
2. 필수 필드가 모두 있는가
3. 필드 타입이 맞는가
4. output_schema가 있는가
5. forbidden이 있는가
6. manager_self_check가 있는가
7. worker에게 최종 판단을 시키지 않았는가
8. 파일 수정권을 주지 않았는가
9. shell 실행권을 주지 않았는가
10. secret/API key가 포함되지 않았는가
11. budget을 초과하지 않았는가
```

## semantic_preflight

의미론적 판단 항목:

```text id="z4xtnh"
1. role과 task가 적절한가
2. input_scope가 과도하게 넓지 않은가
3. mission 핵심 요구가 WorkOrder에 반영됐는가
4. WorkOrder 중복이 과도하지 않은가
5. known_gaps가 허용 가능한가
```

규칙:

```text id="f5t8wo"
1. semantic_preflight는 Phase Canon에서 허용한 경우에만 수행한다.
2. v0에서는 API 호출 0회 원칙 때문에 LLM 기반 semantic_preflight를 수행하지 않는다.
3. v0에서는 manager_self_check의 존재와 형식만 deterministic_preflight로 검사한다.
```

처리:

```text id="jueh1b"
pass:
- worker 실행

fail:
- worker 실행 중단
- preflight_audit.json 저장
- ceo_report.md 생성 시도
- run_log.jsonl 기록
```

가능 failure_type:

```text id="k58j65"
MANAGER_BAD_PLAN
SCHEMA_ERROR
SECURITY_BLOCKED
BUDGET_EXCEEDED
```

---

# 14. WorkerResult

`worker_results.jsonl`의 각 line은 공통 wrapper를 따른다.
worker별 고유 산출물은 `payload`에 저장한다.

필수 필드:

```text id="4w3k04"
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

```json id="6rm5s5"
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

```text id="l96y08"
1. confidence는 0.0~1.0 숫자 또는 null.
2. confidence < 0.5인 결과는 단독 근거로 final_report에 반영하지 않는다.
3. confidence가 null이면 낮은 confidence와 동일하게 취급한다.
4. 낮은 confidence는 짧게 다룬다.
```

Manager 품질 판정:

```text id="w6ztb8"
usable: yes | partial | no
reason
used_by_manager: yes | no
discarded_reason
```

저장 규칙:

```text id="gy68h8"
1. worker output은 참고자료다.
2. worker output은 정본이 아니다.
3. discarded result도 reason을 남긴다.
4. masked_raw_output을 기본 저장 필드로 사용한다.
5. raw_output 저장 여부는 raw_output_saved로 표시한다.
6. raw_output 저장 금지가 기본이다.
7. API key, token, credential 감지 시 SECURITY_BLOCKED 또는 masking 처리한다.
```

---

# 15. SCHEMA_ERROR / WORKER_BAD_OUTPUT

SCHEMA_ERROR:

```text id="3lriik"
1. JSON 파싱 실패
2. 필수 필드 누락
3. 필드 타입 불일치
4. JSONL line 파싱 실패
5. schema validation 실패
```

WORKER_BAD_OUTPUT:

```text id="yld9k2"
1. schema는 맞지만 내용이 비어 있음
2. role/task와 무관한 응답
3. forbidden 위반
4. confidence 없이 단정
5. WorkOrder 범위 밖 응답
```

---

# 16. manager_summary.json

필수 필드:

```text id="i9zxho"
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

```text id="y9zp0s"
1. draft_report는 manager_summary.json 내부 필드다.
2. draft_report는 별도 파일이 아니다.
3. draft_report는 final_report가 아니다.
4. fail 또는 needs_decision에서 failed_draft.md가 필요한 경우 Harness가 draft_report를 추출해 failed_draft.md로 저장한다.
```

기타 규칙:

```text id="qstlri"
1. worker 원문 그대로 붙여넣기 금지.
2. used/rejected 결과를 분리한다.
3. conflicts와 gaps를 명시한다.
4. ceo_decision_needed를 명시한다.
5. repair 실행 여부와 무관하게 repair_needed는 기록할 수 있다.
```

---

# 17. Repair

Master 규칙:

```text id="scndw5"
1. repair loop는 Phase Canon에서 허용 여부를 정한다.
2. repair loop는 항상 횟수 제한을 가진다.
3. v0에서는 repair 실행 금지.
4. v0에서는 repair_needed와 repair_orders 기록만 허용.
```

repair 가능:

```text id="yv68mg"
1. mission 핵심 요구 누락
2. worker 결과 간 충돌
3. output_format 불일치
4. auditor required_fix 존재
5. 대표 판단 없이 자동 보완 가능
```

repair 금지:

```text id="ky6r0h"
1. mission 자체 모순
2. 대표 취향/사업판단 필요
3. 예산 초과
4. 같은 문제 반복
5. 외부 최신 정보 필요하지만 검색 권한 없음
```

---

# 18. Audit

audit 체크 항목:

```text id="wmszbx"
1. must_include 반영
2. must_avoid 위반 없음
3. output_format 충족
4. 내부 모순 없음
5. 근거 없는 핵심 주장 없음
6. worker 결과와 핵심 충돌 없음
7. 대표 판단 필요 항목 표시
8. 남은 위험 표시
```

audit status:

```text id="l3sb23"
pass
conditional
fail
```

audit_report 필수 필드:

```text id="bhuajz"
status
blocking
warnings
mission_coverage
required_fixes
ceo_decision_needed
summary
```

required_fixes 규칙:

```text id="enq5fs"
1. required_fixes가 비어 있지 않으면 final_report 승격 금지.
2. Phase에서 repair가 허용되고 자동 수정 가능한 경우 repair로 보낼 수 있다.
3. v0에서는 repair 실행 금지이므로 required_fixes 존재 시 final_report 승격 금지.
```

ceo_decision_needed 병합 규칙:

```text id="2kcfm4"
1. manager_summary.ceo_decision_needed 또는 audit_report.ceo_decision_needed 중 하나라도 true이면 최종 상태는 NEEDS_DECISION으로 처리한다.
2. 둘 다 false일 때만 자동 pass/conditional/fail 처리를 계속한다.
3. audit_report.ceo_decision_needed = true는 manager_summary 판단을 덮어쓸 수 있다.
```

---

# 19. BLOCKING / WARNING

BLOCKING:

```text id="muw3t8"
1. mission 핵심 요구 누락
2. must_avoid 위반
3. 내부 모순
4. output_format 불일치
5. 근거 없는 핵심 주장
6. 대표 판단 없이 임의 결정
7. 금지된 권한 사용 시도
```

WARNING:

```text id="segc3q"
1. 일부 근거 약함
2. 후속 검토 필요
3. 작업 범위 밖 잠재 리스크
4. mission 핵심을 깨지 않는 불확실성
```

처리:

```text id="j9pwe1"
BLOCKING 존재:
- audit status = fail
- final_report.md 생성 금지

WARNING만 존재:
- audit status = conditional 가능
- final_report.md 생성 가능
- ceo_report.md에 표시
```

---

# 20. final_report 승격

생성 조건:

```text id="ykwfrl"
1. preflight audit pass
2. worker_results 존재
3. manager_summary 존재
4. audit status = pass 또는 conditional
5. BLOCKING 없음
6. required_fixes 없음
7. 최종 ceo_decision_needed = false
```

상호배타 규칙:

```text id="6y7uxq"
1. final_report.md와 failed_draft.md는 동시에 생성하지 않는다.
2. final_report.md는 승격 산출물이다.
3. failed_draft.md는 검토용 산출물이며 정본이 아니다.
```

fail / needs_decision 처리:

```text id="qcw87g"
1. final_report.md 생성 금지
2. draft_report가 있으면 failed_draft.md 생성 가능
3. draft_report가 없으면 failed_draft.md 생성하지 않음
4. ceo_report.md 생성 시도 필수
```

---

# 21. ceo_report.md

필수 섹션:

```text id="4lxuhe"
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

```text id="55oubg"
1. 기본 600자 이내 목표
2. 최대 1,200자
3. 핵심 결정 최대 5개
4. 남은 위험 최대 5개
5. 대표 판단 필요 항목 최대 3개
6. worker 원문 금지
7. 내부 JSON 덤프 금지
```

상태 규칙:

```text id="4hi9it"
PASS:
- final_report 생성됨
- BLOCKING 없음
- required_fixes 없음
- 최종 ceo_decision_needed = false

CONDITIONAL:
- final_report 생성 가능
- WARNING 존재 가능
- BLOCKING 없음
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

생성 규칙:

```text id="tji4mm"
1. 모든 실행은 ceo_report.md 생성을 시도한다.
2. ceo_report.md 생성 실패 시 REPORT_ERROR를 run_log.jsonl에 기록한다.
```

---

# 22. FAIL / NEEDS_DECISION 구분

FAIL:

```text id="qg5w94"
1. schema 오류
2. manager plan 오류
3. worker output 오류
4. audit fail
5. security block
6. config/model/provider 오류
7. 산출물 생성 실패
```

NEEDS_DECISION:

```text id="i7guq6"
1. mission.md 자체 모순
2. must_include와 must_avoid 충돌
3. output_format 불명확
4. 취향/사업판단 의존 선택
5. 자동 해소 불가능한 worker 간 핵심 사실 충돌
6. 외부 최신 정보 필요하지만 검색 권한 없음
7. 보안/계정/결제/배포 결정 필요
8. mission 범위 밖 추가 작업 필요
9. manager_summary 또는 audit_report에서 ceo_decision_needed = true
```

worker 간 핵심 사실 충돌 처리:

```text id="177pfo"
1. manager/auditor가 mission과 제공 근거 기준으로 해소 가능하면 FAIL 또는 CONDITIONAL.
2. 대표 선택, 외부 정보, 취향 판단 없이는 해소 불가하면 NEEDS_DECISION.
```

audit fail 처리:

```text id="o9c8uq"
audit fail + 자동 수정 불가 + 대표 선택 필요:
- ceo_report status = NEEDS_DECISION
- failure_type = HUMAN_DECISION_REQUIRED

audit fail + 명백한 시스템/산출물 실패:
- ceo_report status = FAIL
- failure_type = AUDIT_FAIL
```

---

# 23. Failure Types

```text id="s0vehm"
CONFIG_ERROR
- 키, 환경 변수, 설정 누락

MODEL_ERROR
- 모델 호출 실패, 429, 500, timeout

SCHEMA_ERROR
- JSON 파싱 실패, 필수 필드 누락, 필드 타입 불일치

MANAGER_BAD_PLAN
- 잘못된 WorkOrder 생성

WORKER_BAD_OUTPUT
- worker 결과 없음, 역할 밖 응답, 형식은 맞지만 내용 불량

AUDIT_FAIL
- final audit 실패

BUDGET_EXCEEDED
- worker 수, 토큰, repair loop, runtime 한도 초과

HUMAN_DECISION_REQUIRED
- 대표 판단 없이는 진행 불가

SECURITY_BLOCKED
- 금지된 파일 수정, shell 실행, key 노출, 외부 실행 시도

REPORT_ERROR
- ceo_report.md, final_report.md, failed_draft.md 등 보고 산출물 생성 실패

UNKNOWN_ERROR
- 분류되지 않은 오류
```

규칙:

```text id="8f7caq"
1. 모든 failure는 run_log.jsonl에 기록.
2. 모든 failure는 ceo_report.md에 요약을 시도.
3. infra/provider/model/schema/report 실패를 구분.
```

---

# 24. run_log.jsonl

이벤트 필드:

```text id="g78qci"
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

규칙:

```text id="v0ly8x"
1. failure_type은 Failure Types에 정의된 enum 값만 사용한다.
2. failure가 아닌 이벤트에서는 failure_type = null을 허용한다.
3. raw API key 기록 금지.
4. key slot만 기록.
5. 실패 원인 기록.
6. provider/model/infra/report 실패 분리.
7. ceo_report 생성 실패도 기록.
```

---

# 25. Security

금지:

```text id="jbjzf8"
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

규칙:

```text id="ft4gsn"
1. key는 Harness가 관리.
2. worker는 key 값을 알 수 없어야 함.
3. log/report에는 key slot만 기록.
```

---

# 26. Phase Plan

## P0 — Canon Setup

산출물:

```text id="hky0lb"
AICO_MASTER_CANON.md
AGENTS.md
CLAUDE.md
HANDOFF.md
CONTEXT_NOTES.md
```

완료 조건:

```text id="we1g91"
1. AICO_V0_CANON.md 추출 가능.
2. AGENTS.md와 CLAUDE.md byte-identical.
3. HANDOFF.md에 현재 Phase와 다음 작업 기록.
```

## P1 — V0 Spec Extraction

v0 포함:

```text id="i4ew5k"
1. API 호출 0회 dry-run
2. mock manager
3. mock worker 4개
4. mock auditor
5. work_orders.json
6. preflight_audit.json
7. worker_results.jsonl
8. manager_summary.json
9. audit_report.json
10. final_report.md
11. failed_draft.md
12. ceo_report.md
13. run_log.jsonl
14. pass/fail/conditional/needs_decision 기본 분기
15. final_report 승격 규칙
16. budget 기본값
```

v0 제외:

```text id="sojtxu"
1. 실제 API 연결
2. LLM 기반 semantic_preflight
3. repair loop 실행
4. 22개 키 사용
5. GitHub Issue 보고
6. CLI agent orchestration
7. 파일 수정권
8. shell 실행권
9. 웹 대시보드
```

## P2 — V0 Dry-run Implementation

완료 조건:

```text id="f2f5kq"
1. API 호출 0회
2. mission.md 입력
3. runs/<run_id>/ 생성
4. work_orders.json 생성
5. deterministic_preflight 실행
6. LLM 기반 semantic_preflight 미실행
7. preflight_audit.json 생성
8. worker_results.jsonl 생성
9. manager_summary.json 생성
10. audit_report.json 생성
11. ceo_report.md 생성 시도
12. pass case에서 final_report.md 생성
13. conditional case에서 final_report.md 생성 및 ceo_report warning 표시
14. fail case에서 final_report.md 미생성
15. needs_decision case에서 final_report.md 미생성
16. required_fixes 존재 시 final_report.md 미생성
17. mid-flight failure 시 partial worker_results 보존
18. v0 max_model_calls = 0
```

## P3 — API Worker 4

구성:

```text id="3cb4qw"
manager 1
worker 4
auditor 1
reserve 1
```

완료 조건:

```text id="w7smz8"
1. key raw value 미노출
2. MODEL_ERROR / SCHEMA_ERROR / WORKER_BAD_OUTPUT 분리
3. worker 품질 판정 가능
4. ceo_report 1,200자 이내 유지
5. masked_raw_output 기본 저장
```

## P4 — Repair 1

완료 조건:

```text id="evqoqt"
1. repair loop 최대 1회
2. 반복 실패 시 HUMAN_DECISION_REQUIRED 또는 BUDGET_EXCEEDED
3. repair 결과가 manager_summary와 audit_report에 반영
4. repair 후 audit 재실행
```

## P5 — Report Channel

목표:

```text id="5fm8e6"
ceo_report.md를 모바일 확인용 최종 보고 형식으로 고정.
```

## P6 — GitHub Issue Channel

목표:

```text id="6yx34r"
Issue 하나 = mission 하나
ceo_report를 Issue 댓글로 요약
사용자가 모바일에서 승인/반려
```

## P7 — Code Execution Extension

검토 대상:

```text id="7nr7h9"
1. 파일 수정권
2. shell 실행권
3. worktree 격리
4. CLI agent orchestration
5. 자동 PR 여부
```

---

# 27. Expansion Rules

4 workers → 8 workers 조건:

```text id="ij3npo"
1. worker 결과 유효율 60% 이상
2. auditor pass/conditional 비율 70% 이상
3. manager_summary가 worker 결과를 압축
4. ceo_report만으로 상태 이해 가능
5. run_log 누락 없음
6. repair loop 폭주 없음
```

8 workers → 22 workers 조건:

```text id="7nmd1h"
1. 중복 worker 결과 제거 가능
2. worker 원문 없이 final 검수 가능
3. audit fail 원인 추적 가능
4. 토큰/비용 기록 가능
5. ceo_report 길이 증가 없음
6. 실패 시 중단과 보고 정상 작동
```

---

# 28. Required Tests

```text id="q379z1"
1. dry-run creates run directory
2. invalid WorkOrder fails deterministic_preflight
3. v0 does not run LLM-based semantic_preflight
4. worker output schema error becomes SCHEMA_ERROR
5. schema-valid but empty/irrelevant worker output becomes WORKER_BAD_OUTPUT
6. audit fail creates no final_report
7. audit fail creates failed_draft only if draft_report exists
8. audit pass creates final_report
9. audit conditional creates final_report and ceo_report includes warnings
10. required_fixes prevents final_report when repair is not allowed
11. needs_decision creates ceo_report and no final_report
12. manager_summary.ceo_decision_needed true creates NEEDS_DECISION
13. audit_report.ceo_decision_needed true creates NEEDS_DECISION
14. ceo_report exists or REPORT_ERROR is logged
15. run_log failure event includes failure_type
16. raw API key never appears in logs
17. worker cannot request shell/file edit
18. repair loop is not executed before allowed Phase
19. mission.md has highest priority within a run
20. AGENTS.md and CLAUDE.md are byte-identical
21. v0 makes zero API calls
22. final_report.md and failed_draft.md are mutually exclusive
23. raw_output is masked or blocked when secrets are detected
24. references cannot access paths outside allowed workspace/run scope
25. confidence < 0.5 is not used as sole support for final_report
26. budget exceeded becomes BUDGET_EXCEEDED
27. mid-flight failure preserves partial worker_results and skips unavailable downstream artifacts
```

---

# 29. Success Criteria

```text id="ww5qg3"
1. Supported entrypoint accepts mission input.
2. runs/<run_id>/ is created.
3. Required artifacts are generated according to status.
4. Failure path produces ceo_report.md or logs REPORT_ERROR.
5. Failure path produces run_log.jsonl.
6. No raw key appears in artifacts.
7. final_report is generated only by promotion rules.
8. worker performs bounded tasks only.
9. manager records used/rejected worker results.
10. auditor records BLOCKING/WARNING/required_fixes.
11. failed_draft is never treated as final_report.
12. Master Canon → Phase Canon → implementation → result → Master revision loop is maintained.
```
