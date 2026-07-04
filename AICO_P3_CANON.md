# AICO_P3_CANON.md

프로젝트명: `aico`
상태: P3 Canon / API Worker 4 설계 단계
기준 문서: `AICO_MASTER_CANON.md`, `AICO_V0_CANON.md`, `P2_REVIEW.md`, `HANDOFF.md`

---

# 1. P3 목적

P3는 P2 v0 dry-run harness 위에 실제 API worker 4개를 연결하기 위한 단계다.

P3 목표:

```text
manager 1
worker 4
auditor 1
reserve 1
```

P3는 구성 요소를 실제 API 호출 가능한 구조로 확장한다.
단, 이 P3 Canon 작성 단계에서는 API client, provider 연결, 실제 key 사용, 실제 모델 호출, P3 코드 구현을 하지 않는다.

---

# 2. 문서 우선순위

```text
1. AICO_MASTER_CANON.md
2. AICO_V0_CANON.md
3. AICO_P3_CANON.md
4. P2_REVIEW.md
5. HANDOFF.md
6. AGENTS.md / CLAUDE.md
7. CONTEXT_NOTES.md
```

P3 구현 중 충돌이 있으면 상위 문서를 따른다.

---

# 3. P3 범위

P3 포함:

```text
1. 실제 API worker 4개 연결 설계
2. manager 1 / worker 4 / auditor 1 / reserve 1 구조
3. key slot 기반 실행
4. raw API key 미노출
5. masked_raw_output 기본 저장
6. MODEL_ERROR / SCHEMA_ERROR / WORKER_BAD_OUTPUT 분리
7. provider timeout / 429 / 500 처리 정책
8. API 호출 수와 token 기록
9. run_log.jsonl 확장 규칙
10. P3 Required Tests
11. P3 완료 조건
```

P3 제외:

```text
1. 22개 키 전체 사용
2. repair loop 실행
3. semantic_preflight 실행
4. 파일 수정권 부여
5. shell 실행권 부여
6. 웹 검색
7. 외부 URL 접근
8. repo clone
9. GitHub Issue 연동
10. 웹 대시보드
11. CLI agent orchestration
12. 자동 PR / merge
```

---

# 4. P2에서 유지해야 할 규칙

P3에서도 다음 P2 규칙을 유지한다.

```text
1. final_report.md와 failed_draft.md는 상호배타다.
2. 모든 실행은 ceo_report.md 생성을 시도한다.
3. ceo_report.md 생성 실패 시 REPORT_ERROR를 run_log.jsonl에 기록한다.
4. run_log.jsonl의 failure event에는 failure_type을 기록한다.
5. AGENTS.md와 CLAUDE.md는 byte-identical이어야 한다.
6. failed_draft.md는 정본이 아니다.
7. worker 파일 수정은 금지한다.
8. worker shell 실행은 금지한다.
9. 외부 URL / 웹 검색 / repo clone은 금지한다.
10. semantic_preflight는 실행하지 않는다.
11. repair loop는 실행하지 않는다.
12. raw key 또는 secret은 산출물에 기록하지 않는다.
13. confidence < 0.5인 worker 결과는 단독 근거로 final_report.md에 반영하지 않는다.
14. mid-flight failure 시 이미 생성된 worker_results.jsonl은 보존한다.
```

---

# 5. Runtime 구성

P3 runtime 구성:

```text
Harness
Manager API Slot      manager_1
Worker API Slot 1     worker_1
Worker API Slot 2     worker_2
Worker API Slot 3     worker_3
Worker API Slot 4     worker_4
Auditor API Slot      auditor_1
Reserve API Slot      reserve_1
```

규칙:

```text
1. Harness만 key raw value를 관리한다.
2. Manager, Worker, Auditor는 raw key 값을 알 수 없다.
3. API 호출 로그에는 raw key 대신 key_slot만 기록한다.
4. reserve_1은 provider/key failure 대응용 예비 slot이다.
5. reserve_1 사용도 budget과 run_log 규칙을 따른다.
6. worker는 WorkOrder 범위 안에서만 응답한다.
7. worker는 파일 수정, shell 실행, 외부 URL 접근, 웹 검색, repo clone을 요청하거나 수행할 수 없다.
```

---

# 6. API Key / Secret 정책

raw API key는 다음 위치에 절대 기록하지 않는다.

```text
1. prompt
2. run_log.jsonl
3. report
4. worker output
5. manager_summary.json
6. audit_report.json
7. final_report.md
8. failed_draft.md
9. ceo_report.md
10. masked_raw_output
```

key 관리 규칙:

```text
1. key는 Harness가 관리한다.
2. worker는 key 값을 알 수 없다.
3. log에는 key raw value가 아니라 key_slot만 기록한다.
4. key_slot 예시는 manager_1, worker_1, worker_2, worker_3, worker_4, auditor_1, reserve_1이다.
5. secret scan은 P3에서도 유지한다.
6. raw key가 산출물에 나타나면 SECURITY_BLOCKED로 처리한다.
7. raw key가 prompt에 들어가려는 경우 호출 전에 SECURITY_BLOCKED로 중단한다.
8. raw key가 provider response나 worker output에 나타나면 masking 또는 SECURITY_BLOCKED로 처리한다.
```

secret baseline:

```text
API key
token
credential
secret
sk-*
ghp_*
gho_*
ghu_*
ghs_*
```

---

# 7. API Failure Types

P3는 provider/model/schema/worker/security/budget/report 실패를 구분한다.

## MODEL_ERROR

MODEL_ERROR 조건:

```text
1. provider timeout
2. 429 rate limit
3. 500 provider error
4. provider unavailable
5. malformed provider response before schema stage
6. model call transport failure
```

정책:

```text
1. MODEL_ERROR는 API 호출 이벤트와 연결한다.
2. provider status, sanitized error, key_slot, model, token count를 run_log.jsonl에 기록한다.
3. raw provider response는 저장하지 않는다.
4. retry는 budget 범위 안에서만 허용한다.
5. max_consecutive_model_errors 초과 시 중단한다.
```

## SCHEMA_ERROR

SCHEMA_ERROR 조건:

```text
1. JSON parse 실패
2. 필수 필드 누락
3. 타입 불일치
4. schema validation 실패
5. malformed provider response가 schema stage에서 발견됨
```

정책:

```text
1. schema validation 실패 시 downstream promotion을 중단한다.
2. worker_results.jsonl에 이미 저장된 이전 worker 결과는 보존한다.
3. schema error는 MODEL_ERROR와 분리한다.
```

## WORKER_BAD_OUTPUT

WORKER_BAD_OUTPUT 조건:

```text
1. schema는 맞지만 내용 없음
2. 역할 밖 응답
3. forbidden 위반
4. WorkOrder 범위 밖 응답
5. 낮은 confidence로 단정
6. required evidence 없이 final conclusion 시도
```

정책:

```text
1. schema-valid bad output은 SCHEMA_ERROR가 아니다.
2. confidence < 0.5인 결과는 단독 근거로 final_report.md에 반영하지 않는다.
3. bad output worker id는 manager_summary.json의 rejected_worker_results에 기록한다.
```

## SECURITY_BLOCKED

SECURITY_BLOCKED 조건:

```text
1. raw key 노출
2. shell/file/network 권한 요청
3. 외부 URL 접근 시도
4. repo clone 시도
5. web search 시도
6. prompt/log/report/output에 secret 포함
```

정책:

```text
1. SECURITY_BLOCKED는 즉시 중단 가능한 failure_type이다.
2. ceo_report.md 생성을 시도한다.
3. run_log.jsonl에 sanitized error를 기록한다.
4. raw secret value는 기록하지 않는다.
```

## BUDGET_EXCEEDED

BUDGET_EXCEEDED 조건:

```text
1. max_model_calls 초과
2. max_workers 초과
3. max_input_tokens 초과
4. max_output_tokens 초과
5. max_runtime_seconds 초과
6. max_retries_per_call 초과
7. max_consecutive_model_errors 초과
```

정책:

```text
1. budget 초과 시 남은 API 호출은 실행하지 않는다.
2. 이미 생성된 worker_results.jsonl은 보존한다.
3. 조건을 충족하지 않으면 manager_summary.json, audit_report.json, final_report.md, failed_draft.md는 생성하지 않는다.
4. ceo_report.md 생성을 시도한다.
5. run_log.jsonl에 BUDGET_EXCEEDED를 기록한다.
```

---

# 8. P3 Budget

P3 budget 값은 Phase Canon에서 조정 가능하다.

기본 제안:

```text
max_workers = 4
max_repair_loops = 0
max_model_calls = 6
max_input_tokens = Phase Canon에서 조정 가능
max_output_tokens = Phase Canon에서 조정 가능
max_runtime_seconds = Phase Canon에서 조정 가능
max_retries_per_call = 1
max_consecutive_model_errors = 2
```

규칙:

```text
1. max_workers는 worker slot 수와 일치하는 4를 기본값으로 한다.
2. max_repair_loops는 P3에서 0이다.
3. semantic_preflight는 P3에서 실행하지 않는다.
4. max_model_calls는 manager 1 + worker 4 + auditor 1 = 6을 기본값으로 한다.
5. reserve_1 사용은 max_model_calls와 retry budget 안에서만 가능하다.
6. token count를 알 수 없으면 run_log field는 null을 허용한다.
7. budget 초과 시 BUDGET_EXCEEDED로 중단한다.
```

---

# 9. API 호출 기록

`run_log.jsonl` 이벤트 필드:

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

규칙:

```text
1. 모든 이벤트는 위 필드를 가진다.
2. failure가 아닌 이벤트에서는 failure_type = null이다.
3. API 호출 이벤트는 model, key_slot, input_tokens, output_tokens를 기록한다.
4. token count를 알 수 없으면 null 허용. 단 필드는 존재해야 한다.
5. raw key는 절대 기록하지 않는다.
6. provider/model/infra/schema/report 실패는 failure_type으로 구분한다.
7. retry 이벤트는 parent_event_id로 원래 API 호출 이벤트와 연결한다.
8. ceo_report.md 생성 실패는 REPORT_ERROR로 기록한다.
```

API 호출 이벤트 예시:

```json
{
  "timestamp": "2026-07-05T00:00:00Z",
  "event_type": "API_CALL_COMPLETED",
  "actor": "worker_1",
  "model": "provider-model-name",
  "key_slot": "worker_1",
  "input_tokens": 1200,
  "output_tokens": 300,
  "status": "ok",
  "failure_type": null,
  "error": null,
  "artifact_path": "worker_results.jsonl",
  "parent_event_id": null
}
```

---

# 10. masked_raw_output

P3에서도 `masked_raw_output`을 기본 저장 필드로 유지한다.

worker result 필수 필드:

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

규칙:

```text
1. raw output 저장 금지가 기본이다.
2. raw_output_saved = false가 기본이다.
3. raw output을 그대로 저장하지 않는다.
4. provider response는 secret scan 후 masked_raw_output으로만 저장한다.
5. secret 감지 시 masking 또는 SECURITY_BLOCKED로 처리한다.
6. masked_raw_output에도 raw key가 남아 있으면 SECURITY_BLOCKED다.
7. mask_reason에는 masking 또는 raw output 미저장 사유를 기록한다.
```

---

# 11. Mid-flight Failure

P3에서도 mid-flight failure 처리 규칙을 유지한다.

규칙:

```text
1. 일부 worker만 성공한 상태에서 API failure가 발생하면 기존 worker_results.jsonl은 보존한다.
2. 실패 이후 남은 worker는 실행하지 않는다.
3. 조건을 충족하지 않으면 manager_summary.json, audit_report.json, final_report.md, failed_draft.md는 생성하지 않는다.
4. ceo_report.md 생성을 시도한다.
5. ceo_report.md 생성 실패 시 REPORT_ERROR를 기록한다.
6. 원래 failure_type은 run_log.jsonl에 보존한다.
7. REPORT_ERROR가 추가로 발생하면 parent_event_id 또는 previous failure event로 원래 failure_type을 추적 가능해야 한다.
```

예시:

```text
worker_1 success
worker_2 success
worker_3 MODEL_ERROR timeout
worker_4 not executed
worker_results.jsonl preserves worker_1 and worker_2
manager_summary.json not created
audit_report.json not created
final_report.md not created
failed_draft.md not created
ceo_report.md attempted
run_log.jsonl records MODEL_ERROR
```

---

# 12. Report Promotion

P3 final_report 승격 조건은 P2 규칙을 유지한다.

`final_report.md` 생성 조건:

```text
1. deterministic_preflight pass
2. worker_results.jsonl 존재
3. manager_summary.json 존재
4. audit_report.json 존재
5. audit status = pass 또는 conditional
6. blocking 없음
7. required_fixes 없음
8. 최종 ceo_decision_needed = false
9. raw key/secret leak 없음
10. confidence < 0.5 결과가 단독 근거가 아님
```

상호배타 규칙:

```text
1. final_report.md와 failed_draft.md는 동시에 생성하지 않는다.
2. failed_draft.md는 검토용 산출물이며 정본이 아니다.
3. failed_draft.md를 final_report.md로 취급하지 않는다.
```

---

# 13. P3 Required Tests

P3 구현 전후에 최소 다음 테스트를 작성해야 한다.

```text
1. API key raw value never appears in logs/reports/artifacts
2. key_slot is logged instead of raw key
3. API timeout becomes MODEL_ERROR
4. provider 429 becomes MODEL_ERROR
5. provider 500 becomes MODEL_ERROR
6. provider unavailable becomes MODEL_ERROR
7. malformed provider response becomes MODEL_ERROR before schema stage
8. malformed provider response becomes SCHEMA_ERROR at schema stage
9. worker JSON parse failure becomes SCHEMA_ERROR
10. missing required worker field becomes SCHEMA_ERROR
11. worker field type mismatch becomes SCHEMA_ERROR
12. schema-valid but empty worker output becomes WORKER_BAD_OUTPUT
13. role-out-of-scope worker output becomes WORKER_BAD_OUTPUT
14. WorkOrder-out-of-scope output becomes WORKER_BAD_OUTPUT
15. low confidence assertion is not used as sole final_report support
16. masked_raw_output is saved by default
17. raw_output_saved is false by default
18. secret in provider output is masked or SECURITY_BLOCKED
19. raw key in provider output becomes SECURITY_BLOCKED
20. final_report and failed_draft remain mutually exclusive
21. ceo_report exists or REPORT_ERROR is logged
22. REPORT_ERROR preserves original failure trace
23. semantic_preflight is still not executed
24. repair loop is still not executed
25. worker cannot request shell/file edit
26. worker cannot request network access
27. external URL remains blocked
28. web search remains blocked
29. repo clone remains blocked
30. mid-flight API failure preserves partial worker_results
31. mid-flight API failure does not execute remaining workers
32. mid-flight API failure skips unavailable downstream artifacts
33. budget max_model_calls exceeded becomes BUDGET_EXCEEDED
34. budget max_input_tokens exceeded becomes BUDGET_EXCEEDED
35. budget max_output_tokens exceeded becomes BUDGET_EXCEEDED
36. budget max_runtime_seconds exceeded becomes BUDGET_EXCEEDED
37. max_retries_per_call is enforced
38. max_consecutive_model_errors is enforced
39. API call events record model and key_slot
40. API call events record input_tokens and output_tokens or null fields
41. failure events include failure_type
42. AGENTS.md and CLAUDE.md remain byte-identical
```

---

# 14. P3 완료 조건

P3 완료 조건:

```text
1. manager 1 / worker 4 / auditor 1 / reserve 1 구조가 구현된다.
2. 실제 API worker 4개 연결이 가능하다.
3. raw API key가 prompt, log, report, worker output, masked_raw_output에 기록되지 않는다.
4. key_slot 기반 logging이 동작한다.
5. MODEL_ERROR / SCHEMA_ERROR / WORKER_BAD_OUTPUT이 분리된다.
6. timeout / 429 / 500 / provider unavailable 처리가 테스트된다.
7. API 호출 수와 token count가 run_log.jsonl에 기록된다.
8. token count를 알 수 없는 경우에도 field는 존재한다.
9. masked_raw_output, raw_output_saved, mask_reason이 worker result에 존재한다.
10. final_report.md와 failed_draft.md 상호배타가 유지된다.
11. ceo_report.md 생성 실패 시 REPORT_ERROR가 기록된다.
12. mid-flight API failure가 partial worker_results를 보존한다.
13. semantic_preflight는 실행되지 않는다.
14. repair loop는 실행되지 않는다.
15. worker 파일 수정권과 shell 실행권이 부여되지 않는다.
16. 외부 URL / 웹 검색 / repo clone이 차단된다.
17. P3 Required Tests가 통과한다.
18. AGENTS.md와 CLAUDE.md가 byte-identical이다.
```

---

# 15. P3 진입 전 구현 금지

이 Canon 작성 작업에서는 다음을 하지 않는다.

```text
1. API client 구현 금지
2. provider 연결 금지
3. 실제 key 사용 금지
4. .env 요구 추가 금지
5. 실제 모델 호출 금지
6. 테스트에서 네트워크 호출 금지
7. P3 코드 구현 금지
8. 기존 P2 harness 구조 변경 금지
```

---

# 16. P3 구현 시작 조건

P3 구현은 별도 명시 지시 후 시작한다.

시작 전 확인:

```text
1. git status clean
2. main == origin/main
3. P2 tests pass
4. AICO_P3_CANON.md exists
5. HANDOFF.md reflects P3 Canon completion
6. AGENTS.md and CLAUDE.md byte-identical
```
