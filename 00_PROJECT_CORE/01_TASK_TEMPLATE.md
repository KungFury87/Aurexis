# AUREXIS CORE — TASK TEMPLATE

Use this template when handing Claude a task. Copy, fill in, and include with the Project Law.

---

## Task

[One sentence. What Claude must do.]

## Objective

[2-3 sentences max. What success looks like.]

## Allowed Subsystems / Files

[List exactly which parts of the codebase Claude may touch.]

- [ ] aurexis_lang/
- [ ] mobile_app/
- [ ] tests/
- [ ] 00_PROJECT_CORE/
- [ ] Other: ___

## Success Criteria

[Concrete, testable conditions that prove the task is done.]

1. ___
2. ___
3. ___

## Non-Goals

[What Claude must NOT do during this task, even if it seems helpful.]

- ___
- ___

## Lane Declaration

This task advances: [which lane — perception, evidence, IR, law, mobile, packaging, etc.]
This task does NOT claim to advance: [what it doesn't touch]

## Architecture Changes

- [ ] No architecture changes allowed (default)
- [ ] Limited architecture changes allowed: ___
- [ ] Architecture change is the point of this task: ___

## Notes

[Any context Claude needs. Keep it short. Do not dump entire conversation history.]

---

**Reminder:** Claude must provide the pre-code compliance statement (Project Law Section 18) before writing any code.
