# Controls Map — Threat → Control → Test → Where It Goes in MediAssist

This is the spine of the project. It takes each ranked threat from your threat model and
answers three questions: what defends it, what proves the defense works, and where the code
has to live inside MediAssist (not this repo — MediAssist).

Priority order below matches the ranked threat list in `docs/threat-model.md`.

## Remediation status — ALL 8 FINDINGS CLOSED

Every red team finding has been fixed in the app and verified by re-running the attack.
Fix evidence lives in `fixes/FIX-01…06.md`.

| Finding | Fix | Evidence |
|---|---|---|
| 3 — PHI disclosure | Session-scoped tools | FIX-01 |
| 4 — Unauthorized access | Session-scoped tools + auth | FIX-01, FIX-02 |
| 6 — Tool misuse + SQL injection | Session-scoped tools + allowed-field allowlist | FIX-01 |
| 8 — Hardcoded secrets | Externalized to environment | FIX-03 |
| Spoofing / no auth | Password + MFA login, session tokens | FIX-02 |
| 7 — Memory poisoning | Screen on write + label on read | FIX-04 |
| 2 — RAG poisoning | Screen KB docs + label as reference | FIX-05 |
| 5 — Unsafe advice + 1 residual | Output filter + prompt hardening | FIX-06 |

Known residual limitations (documented, not yet addressed): login rate-limiting/lockout,
durable session storage, real MFA delivery, and human clinical oversight. These are noted
in the fix docs as the gap between "demo-complete" and "production-ready."


| # | Threat (from threat model) | Primary control | Reference file | Verifying test | Where it installs in MediAssist |
|---|---|---|---|---|---|
| 1 | Prompt injection against chat / retrieved docs | Session-scoped tools — model never supplies patient identity | `controls/session_authz.py` | `test_hijacked_model_still_cannot_pass_a_foreign_id` | Every tool the agent can call; the tool router |
| 2 | Unauthorized modification of records / appointments | Same session scoping + human confirmation on state changes | `controls/session_authz.py` | `test_patient_cannot_reach_another_via_assert` | Record-write and appointment tools; a confirm step in the UI |
| 3 | Unauthorized disclosure of PHI | Session scoping (primary) + output filter (net) | `session_authz.py`, `output_filter.py` | `test_ssn_leak_blocked`, `test_system_prompt_leak_blocked` | Record-read tools; a final pass before responses render |
| 4 | Privilege escalation (user/AI acts above role) | Role check in `assert_can_access`; deny by default | `controls/session_authz.py` | `test_provider_reaches_care_team_but_not_others` | Auth layer + every privileged tool |
| 5 | Memory poisoning (persists across sessions) | Validate before write; never store permissions/roles in memory | *design rule — see note below* | *(add when memory store exists)* | Memory write path |
| 6 | Patient account spoofing / fake login | MFA at login; short-lived session tokens | *handled by MediAssist auth + IdP* | *(integration test)* | Login flow |
| 7 | RAG poisoning / indirect injection | Ingest screening + retrieval wrapping | `controls/rag_guard.py` | `test_poisoned_document_is_quarantined`, `test_exfil_url_document_is_quarantined` | Knowledge-base ingest pipeline + retrieval step |
| — | Repudiation / missing audit trail | Tamper-evident, chained audit log | `controls/audit_log.py` | `test_tampering_breaks_the_chain`, `test_denied_access_is_logged` | Wrap every tool call |

## Notes on the gaps

**#5 Memory poisoning** has no code module yet on purpose — the right fix depends on how
MediAssist stores memory, which you'll see when you have the app open. The design rule is
fixed regardless: *permissions and identity are never read from memory.* Memory may hold
"patient mentioned a headache last week"; it must never hold "patient has admin access."
Roles come from the session every time. That one rule kills the Variant B memory-poisoning
payload in the playbook.

**#6 Spoofing** is mostly handled by MediAssist's own auth plus an identity provider — this
is the "Transfer" decision from your threat model. Your job is to confirm MFA is actually
enforced and session tokens expire, not to build auth from scratch.

## The build backlog — COMPLETED

Done one at a time, each verified by re-running the matching red team payload.

1. ✅ **Session-scoped tools** — every tool reads identity from the session, not the model. Closed threats 1–4 + 6. (FIX-01)
2. ✅ **Authentication + MFA** — password + 6-digit code; session token is the source of identity. Closed spoofing/no-auth. (FIX-02)
3. ✅ **Secrets externalized** — all keys moved to the environment. (FIX-03)
4. ✅ **Memory validation** — screen on write, label on read. Closed threat 7. (FIX-04)
5. ✅ **RAG screening** — poisoned KB docs quarantined at load; content labeled reference-only. Closed threat 2. (FIX-05)
6. ✅ **Output filter + prompt hardening** — PHI/leak net on responses; backdoor removed; safety rules added. Closed threat 5 + residual 1. (FIX-06)

Not yet done (documented as future work): a per-tool audit log (reference `audit_log.py`
exists in `controls/`), an explicit UI confirmation step on state-changing actions, and the
production-hardening items (rate-limiting, durable sessions, real MFA delivery).

## In Cursor

Reference the relevant doc when you ask for a fix, e.g.:

> `@docs/threat-model.md @CONTROLS-MAP.md` — refactor the patient record tool so identity
> comes from the session, following the session_authz pattern. Then show me the diff.

One change per request. Read the diff before you accept it — on a deliberately vulnerable
app, understanding each hole you close is the whole point.
