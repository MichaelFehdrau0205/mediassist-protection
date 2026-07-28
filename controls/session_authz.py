"""
session_authz.py  —  Session-scoped authorization

THE MOST IMPORTANT FILE IN THIS REPO. Read the comments; they explain the idea.

The problem
-----------
An AI agent decides which tools to call and what arguments to pass. If a tool
accepts a patient_id from the model, then convincing the model to pass a
DIFFERENT patient_id is enough to steal someone's records. Prompt injection is
exactly the art of convincing the model to do that.

The fix
-------
Never let the model choose whose data it gets. The tool reads the patient's
identity from the *verified session* — the thing established at login, which the
model cannot influence. The model can still be fully hijacked and it does not
matter, because the hijacked model has no way to change the session.

This single idea defends: prompt injection (#1), unauthorized disclosure (#3),
privilege escalation (#4), and cross-patient modification (#2) — the entire top
of the ranked threat list.

This module has no external dependencies so it can drop into any Python app.
"""

from dataclasses import dataclass
from functools import wraps


class AccessDenied(Exception):
    """Raised when a request tries to reach data it is not entitled to."""
    pass


@dataclass(frozen=True)
class Session:
    """
    Represents a verified, logged-in user. Created by the auth layer AFTER
    password + MFA succeed. `frozen=True` means it cannot be modified after
    creation — the model cannot reach in and change patient_id mid-request.

    role is "patient" or "provider". A patient may only ever see their own
    record. A provider may see patients on their care team (checked separately).
    """
    patient_id: str
    role: str = "patient"
    care_team_patient_ids: tuple = ()


def patient_scoped(func):
    """
    Decorator for any tool that touches patient data.

    The wrapped function MUST take `session` as its first argument and MUST NOT
    take a patient_id from the caller. Identity is derived from the session
    inside the function body. This makes it structurally impossible for the
    model to request another patient's data — there is no argument to abuse.
    """
    @wraps(func)
    def wrapper(session: Session, *args, **kwargs):
        if not isinstance(session, Session):
            raise AccessDenied("No valid session — request rejected.")
        if not session.patient_id:
            raise AccessDenied("Session has no verified patient identity.")
        return func(session, *args, **kwargs)
    return wrapper


def assert_can_access(session: Session, target_patient_id: str) -> None:
    """
    The authorization check itself. Call this whenever a target patient_id is
    genuinely unavoidable (e.g. a provider workflow that legitimately spans
    patients). For the normal patient-facing path, prefer patient_scoped so this
    question never even comes up.

    Rules:
      - A patient may access ONLY their own record.
      - A provider may access their own record and care-team patients.
      - Everything else raises AccessDenied.
    """
    if target_patient_id == session.patient_id:
        return  # your own record — always allowed

    if session.role == "provider" and target_patient_id in session.care_team_patient_ids:
        return  # provider reaching a patient on their care team

    # Anything else is denied. This is the line that stops URL/ID tampering
    # (GET /api/patient/1002 with someone else's id) AND a hijacked model that
    # was tricked into asking for another patient.
    raise AccessDenied(
        f"Session for patient {session.patient_id!r} may not access "
        f"patient {target_patient_id!r}."
    )


# ---------------------------------------------------------------------------
# Example tools. In the real MediAssist these would query the database. Here
# they use a tiny fake store so the tests can run with no dependencies.
# ---------------------------------------------------------------------------

_FAKE_RECORDS = {
    "1001": {"name": "Test Patient A", "allergies": ["penicillin"], "notes": "..."},
    "1002": {"name": "Test Patient B", "allergies": [], "notes": "..."},
}


@patient_scoped
def get_my_record(session: Session) -> dict:
    """
    SAFE tool. Notice there is no patient_id parameter at all. The model calls
    get_my_record(session); it cannot ask for anyone else because there is
    nowhere to put someone else's id.
    """
    return _FAKE_RECORDS.get(session.patient_id, {})


def get_patient_record_UNSAFE(patient_id: str) -> dict:
    """
    ANTI-PATTERN — shown so you can recognize it in the MediAssist code and
    delete it. The model supplies patient_id, so prompt injection wins. Do not
    ship anything shaped like this. Kept here only as a teaching contrast.
    """
    return _FAKE_RECORDS.get(patient_id, {})
