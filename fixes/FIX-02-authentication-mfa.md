# Fix 02 — Authentication + MFA (trustworthy session identity)

Author: Michael Fehdrau
Closes red team findings: **the root cause of 4** (no authentication), and the
spoofing threat (Finding 5 in the threat model's ranked list)
Files changed: `main.py`, `database.py`, `static/index.html`; new file `auth.py`

---

## The vulnerability

MediAssist had no real login. The old flow took a `patient_id` straight from the
client: you typed a number 1–10 and every request trusted it (`main.py` old
`/chat`, `ChatRequest.patient_id`). "Being patient 8" required nothing but sending
`patient_id: 8`.

That is the ground Fix 01 stood on. Fix 01 made the tools trust the *session*
identity — but the session identity itself was a lie the client told. This fix
makes that identity real.

## The fix

A two-step login, then a session token that the server derives identity from.

1. **Passwords (`auth.py`).** Each patient has a user account. Passwords are stored
   as PBKDF2-HMAC-SHA256 hashes with a per-user salt (200,000 rounds). Plaintext
   passwords are never stored or compared.

2. **MFA (`auth.py`, `/login` + `/verify-mfa`).** After the password checks out, the
   server generates a cryptographically-random 6-digit code with a 5-minute
   expiry and "sends" it to the patient's email/phone on record. A **session is
   issued only after the code is verified** — the password step alone gives you
   nothing.

3. **Session tokens (`auth.py`, `main.py`).** On success the server issues a random,
   expiring session token. `/chat`, `/reset`, `/me`, and `/logout` read identity
   from `auth.get_session_patient_id(token)` — the single source of truth for
   "who is this." **`patient_id` was removed from the request body entirely.**

4. **Frontend (`static/index.html`).** Real two-step login UI (username/password →
   code → chat). The session token is sent in the `Authorization: Bearer` header
   on every request.

### Honest scope note — MFA delivery is stubbed

Actually texting or emailing the code needs a paid Twilio/SendGrid account and,
for real patient data, a signed BAA. So `auth.deliver_mfa_code` prints the code to
the **server terminal** and shows the user a masked destination
(`m********@email.com`). The security mechanism is fully real — random code,
expiry, verify-before-session. Only the last-mile send is stubbed, at one clearly
marked line where a real API call plugs in.

## Evidence — tested with FastAPI's test client

```
TEST A — wrong password rejected                     401 Invalid username or password
TEST B — correct password starts MFA, NO session yet 200 {login_token, mfa_sent_to}
         [MFA] Code for m********@email.com: 943742   (printed to server terminal)
TEST C — wrong MFA code rejected                     401 Invalid or expired code
TEST D — correct code issues session token           200 {session_token, patient_name}
TEST E — /chat with no token                          401 Not authenticated
TEST F — CORE: token beats forged body patient_id     agent served patient 1, not 8
TEST G — invalid token                                401 Not authenticated
```

**Test F is the one that matters.** A request arrived carrying `patient_id: 8` in
the body plus a valid session token for patient 1. The server served patient 1.
The forged id was ignored, because identity now comes only from the token.

## Demo login credentials (synthetic data)

Username = the email local-part; password = `MediPass<id>!`. Examples:

| Patient | Username | Password |
|---|---|---|
| 1 — Margaret Chen | `mchen1965` | `MediPass1!` |
| 2 — James Okafor | `jokafor78` | `MediPass2!` |
| 3 — Sofia Ramirez | `sramirez92` | `MediPass3!` |
| … | (email before the @) | `MediPass<id>!` |

When you log in, the 6-digit code appears in the terminal running the app
(`[MFA] Code for ...`). Enter it to reach the chat.

## How Fix 01 and Fix 02 work together

- **Fix 01** — tools trust the session's `patient_id`, not the model's.
- **Fix 02** — that session `patient_id` now comes from a verified password + MFA
  login, not the request body.

Together: a request must prove who it is (Fix 02), and even a hijacked model can't
reach beyond that proven identity (Fix 01). Neither is enough alone.

## What this fix does NOT yet cover

- **Login rate-limiting / lockout** — no cap on password or code attempts yet (brute-force).
- **Session storage** — sessions live in memory, so they reset when the app restarts. Fine for the exercise; a real deployment uses a durable store.
- **Memory poisoning** (Finding 7), **RAG poisoning** (Finding 2), and **hardcoded secrets** (Finding 8) are still open.

## Status

Applied locally to the app repo. All 7 auth tests pass. Not yet pushed (the app
repo needs a fork of your own first — see below).
