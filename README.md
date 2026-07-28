# MediAssist Protection

Security analysis, red team evidence, and reference security controls for **MediAssist** — a deliberately vulnerable healthcare triage chatbot used as a red team training target.

Author: Michael Fehdrau

---

## What this repo is (and is not)

This repo is **not** the MediAssist application. MediAssist is a separate codebase.

Security controls only work if they run inside the application's request path. You cannot defend an app from a different repo. So this repo holds three things that *can* live separately:

1. **The analysis** — attack surface map, threat model, STRIDE worksheets
2. **The evidence** — red team payloads, findings, and what actually broke
3. **Reference controls** — standalone, tested Python modules meant to be *copied or imported into* MediAssist

Think of `controls/` as a parts bin, not a shield. The parts do nothing until they're installed.

---

## Layout

```
Analysis documents (currently at repo root)
  AttackSurfaceMap .md              Input channels, trust boundaries, agent operating profile
  Threat_Model_MediAssist_FINAL.md  STRIDE, ranked threats, mitigation decisions
  RedTeamReport.md                  Findings template — filled in during testing

redteam/
  payload-playbook.md    Concrete test payloads for each finding category
  rules-of-engagement.md What is in scope and what is not

controls/                Reference implementations
  session_authz.py         Session-scoped authorization  <- start here
  rag_guard.py             Treating retrieved content as data
  output_filter.py         Last-resort PHI leak check
  audit_log.py             Tamper-evident access logging

tests/
  test_controls.py       Tests that prove each control blocks a real attack

CONTROLS-MAP.md          Threat -> control -> test, in one table
```

---

## The core principle

Most of the top-ranked threats in the threat model — prompt injection, unauthorized
disclosure, privilege escalation, unauthorized modification — collapse into a single
design decision:

> **The model never decides whose data it gets. The tool derives identity from the verified session.**

A vulnerable tool signature:

```python
def get_patient_record(patient_id):     # model supplies this — UNSAFE
    return db.fetch(patient_id)
```

A safe one:

```python
@patient_scoped
def get_patient_record(session):        # identity comes from the session — SAFE
    return db.fetch(session.patient_id)
```

In the safe version, a **fully successful** prompt injection still gets nothing. The
attacker convinces the model to call the tool; the tool hands back the attacker's own
record, because the model was never consulted about identity.

This matters because the intuitive fix — filtering malicious prompts — does not hold.
There is no reliable filter for hostile natural language. You block "ignore previous
instructions," the attacker writes it in Spanish, or base64, or splits it across three
messages. Input filtering is a speed bump. Session-scoped authorization is a wall.

Filtering still has a place. It belongs in `rag_guard.py` at document *ingest* time, and
in `output_filter.py` as a last-resort net — both as defense in depth, neither as the
primary control.

---

## Running the tests

```bash
python3 -m pytest tests/ -v
```

No dependencies beyond `pytest`. The controls are deliberately framework-agnostic so they
can drop into whatever MediAssist is built on.

---

## Status

| Piece | State |
|---|---|
| Attack surface map | Complete |
| Threat model | Complete |
| Red team payloads | Ready to run |
| Red team findings | Not yet collected |
| Reference controls | Implemented + tested |
| Controls installed in MediAssist | Not started |
