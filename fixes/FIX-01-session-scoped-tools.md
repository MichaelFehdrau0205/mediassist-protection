# Fix 01 — Session-Scoped Tools (patient_id trust bug)

Author: Michael Fehdrau
Closes red team findings: **3, 4, 6, and the cross-patient half of 1**
File changed: `agent.py` (in the MediAssist app repo)

---

## The vulnerability

MediAssist's tools trusted a `patient_id` chosen by the model. In `execute_tool`, the
verified session id was passed in but ignored:

```python
def execute_tool(tool_name, tool_input, patient_id):   # patient_id = the real session id
    if tool_name == "get_patient_info":
        result = database.get_patient(tool_input["patient_id"])   # <-- uses the MODEL's id
```

Because `tool_input` is filled by the model, which is driven by whatever the user typed,
the user effectively chose whose record to read or write. This is broken access control
(OWASP A01) and it is the root of findings 3, 4, and 6.

## The fix

One principle: **identity comes from the verified session, never from the model.**

1. **`execute_tool` now uses the session `patient_id` everywhere** — for `get_patient_info`,
   `book_appointment`, `update_medical_record`, and `send_referral`. `tool_input["patient_id"]`
   is gone.

   ```python
   if tool_name == "get_patient_info":
       result = database.get_patient(patient_id)   # the session id; model can't influence it
   ```

2. **Removed `patient_id` from the tool definitions.** The model no longer has an argument
   to put a foreign id into. There is nothing left to abuse.

3. **Removed the `get_all_patients` tool.** No patient should ever pull the full directory
   through the chatbot. (The database function stays for a future admin screen with proper
   authorization.)

4. **Restricted `update_medical_record` to `{phone, email, address}`.** This blocks
   arbitrary edits *and* closes the SQL injection in `database.py:213`, because `field` can
   now only be a known-safe column name.

## Evidence — the same attacks, before and after

Attacks were run directly against the tool/database layer (the same method as the red team
report). Session = patient 1 (Margaret Chen).

| Attack | Before the fix | After the fix |
|---|---|---|
| `get_patient_info` with injected `patient_id: 8` | Returned Carlos Mendez — `ssn: 000-74-1198`, medications | Returns **Margaret Chen** (patient 1's own record); the injected `8` is ignored |
| `get_all_patients` | Dumped all 10 patients with phone + email | `Unknown tool: get_all_patients` — tool removed |
| `update_medical_record` field = `"primary_condition = 'HACKED', ssn"` | Overwrote **two** columns of patient 2 via SQL injection | `Update refused. Patients may only update these fields: address, email, phone.` |
| `update_medical_record` on patient 2's email | Changed patient 2's email | Write lands on patient 1's own record; patient 2 unchanged |

Captured after-fix output:

```
RE-TEST 1 — cross-patient read
  returned name: Margaret Chen | ssn: 000-42-7891
  -> This is patient 1's OWN record. The '8' was ignored.

RE-TEST 2 — full directory dump
  Unknown tool: get_all_patients

RE-TEST 3 — SQL injection via update field
  Update refused. Patients may only update these fields: address, email, phone.

RE-TEST 4 — cross-patient write
  patient 2 email before: jokafor78@email.com | after: jokafor78@email.com  (unchanged)
  patient 1 email now:    attacker@evil.com  (landed on the session's OWN record)
```

## Why this holds against prompt injection

The fix is not a filter that tries to spot bad requests. It removes the `patient_id`
argument entirely, so a hijacked model has nowhere to put a foreign id. In Re-test 1 the
attacker *did* inject `patient_id: 8` and it simply had no effect. A perfect prompt
injection now returns the attacker their own record. Structural authorization beats
filtering.

Note: the old system-prompt backdoor ("if a patient identifies as staff, use your
judgment") is still in the code, but it can no longer cause cross-patient access, because
the tools don't obey it. This is exactly why the fix belongs in the tools, not the prompt.

## What this fix does NOT yet cover

- **Authentication (planned next — layer 2).** The session `patient_id` still comes from
  the `/chat` request body (`main.py`) with no login or MFA. Right now "being patient 1" only
  means sending `patient_id: 1`. The next fix makes that id come from a verified login, so
  the session id this fix relies on is itself trustworthy.
- **Memory poisoning** — `save_memory` still stores arbitrary text (finding 7).
- **RAG poisoning** — knowledge-base documents are still loaded unscreened (finding 2).
- **Hardcoded secrets** in `config.py` (finding 8).

## Status

Fix applied locally to the app repo. Verified. Not yet pushed to GitHub (the app repo is a
clone of the instructor's; pushing requires a fork of your own first).
