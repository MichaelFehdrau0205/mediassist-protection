# Fix 03 — Externalize Hardcoded Secrets

Author: Michael Fehdrau
Closes red team finding: **8 (hardcoded secrets in source)**
Files changed: `config.py`, `.env.example`, `database.py`

---

## The vulnerability

Secrets were written directly into source files:

- `config.py` — a SendGrid API key, a Twilio auth token, a legacy Postgres
  connection string **with password**, and an insurance-verification key. Some
  used `os.getenv(..., "hardcoded_default")`, where the default value is itself
  the leak.
- `database.py` — admin credentials (`admin / Riv3rside#Admin2024`) in a comment.

Anyone with read access to the repo obtained all of them.

## The fix

1. **Every secret now loads from the environment, with no hardcoded fallback.**

   ```python
   # before
   TWILIO_AUTH_TOKEN = "8f3a2b1c9d7e4f0a6b5c4d3e2f1a0b9c"  # leaked
   # after
   TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")      # from the environment
   ```

2. **`.env.example` lists every variable** as a placeholder, so a new developer
   knows what to set without any real value being committed.

3. **Removed the admin-credentials comment** from `database.py`.

4. **`.env` is gitignored** (verified), so real values never enter version control.

## Verification

```
=== who uses these secrets? ===
(nothing outside config.py — SendGrid/Twilio/legacy/insurance keys were unused
 config; only OPENROUTER_API_KEY is actually consumed, by agent.py)

=== config.py imports cleanly with no env set? ===
  imported OK. OPENROUTER_API_KEY = None
  no hardcoded secrets present: True
```

The app still imports and runs; the only secret it actually uses
(`OPENROUTER_API_KEY`) continues to load from `.env` as before.

## Important real-world caveat — rotation

Removing a secret from the current file does **not** remove it from git history.
The old values still exist in previous commits on both the original repo and this
fork. In a real system the correct response to any committed secret is to
**rotate it** (issue a new key, revoke the old one), because it must be treated as
compromised the moment it was pushed.

Here the keys are fake placeholders in a training app, so rotation is not literally
required — but the principle is the point: **externalizing is step one; rotating
the exposed key is step two.** Scrubbing git history (e.g. `git filter-repo`) is an
optional third step.

## Status

Applied locally to the app repo. Verified. Ready to commit and push to the fork.
