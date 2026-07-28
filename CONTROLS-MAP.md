# Controls Map — Threat → Control → Test → Where It Goes in MediAssist

This is the spine of the project. It takes each ranked threat from your threat model and
answers three questions: what defends it, what proves the defense works, and where the code
has to live inside MediAssist (not this repo — MediAssist).

Priority order below matches the ranked threat list in `docs/threat-model.md`.

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

## The build backlog, in order

Do these one branch at a time. Smallest blast radius first.

1. **Audit logging** — install first. It's low-risk to add and it's how you'll *see* whether the other controls work during red teaming. `audit_log.py` → wrap every tool call.
2. **Session-scoped tools** — the big one. Find every tool that takes a `patient_id` argument and refactor it to read identity from the session. Delete anything shaped like `get_patient_record_UNSAFE`. This closes threats 1–4.
3. **RAG ingest screening** — add `screen_document` to whatever loads documents into the knowledge base. Closes threat 7's plant step.
4. **Output filter** — add `scrub_response` as the final step before a reply renders. The net under threats 1 and 3.
5. **Confirmation step** — booking/cancel/modify require a real user click, not just model intent. Finishes threat 2.
6. **Memory validation** — once you've seen the memory store, apply the "no permissions in memory" rule. Closes threat 5.

After each one: run the matching red team payload from `redteam/payload-playbook.md` and
confirm it now fails at the tool, not just in chat. That's the loop — attack, fix, re-attack,
prove it's blocked.

## In Cursor

Reference the relevant doc when you ask for a fix, e.g.:

> `@docs/threat-model.md @CONTROLS-MAP.md` — refactor the patient record tool so identity
> comes from the session, following the session_authz pattern. Then show me the diff.

One change per request. Read the diff before you accept it — on a deliberately vulnerable
app, understanding each hole you close is the whole point.
