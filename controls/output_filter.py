"""
output_filter.py  —  Last-resort check before a response reaches the patient

This is a NET, not a WALL. Its job is to catch a leak that slipped past the real
control (session-scoped tools). If this filter is ever the thing that saves you,
something upstream already failed and should be fixed. Keep it anyway — defense
in depth means the last layer still holds when an earlier one cracks.

What it does
------------
Before a model response is sent to the patient, check that it does not contain
PHI belonging to anyone other than the authenticated session patient, and does
not contain obvious system-prompt leakage.
"""

import re

from .session_authz import Session


# Very rough PHI-shaped patterns. In production you would use a proper PHI
# detector; this is enough to catch blatant leaks in the exercise.
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_MRN = re.compile(r"\bMRN[:#]?\s*\d+\b", re.IGNORECASE)
_SYSTEM_LEAK = re.compile(
    r"(system prompt|you are mediassist|your instructions are|BEGIN_RETRIEVED_DATA)",
    re.IGNORECASE,
)


class OutputBlocked(Exception):
    """Raised when a response must not be delivered as written."""
    pass


def scrub_response(session: Session, response: str, *,
                   allowed_names: list[str] | None = None) -> str:
    """
    Inspect an outgoing response.

    allowed_names: names the session patient is legitimately allowed to see —
    normally just their own. Any OTHER patient name appearing in the output is a
    red flag, but name-matching is unreliable, so we focus on hard identifiers
    (SSN, MRN) and system leakage, which are unambiguous.

    Returns the response if clean. Raises OutputBlocked if it must not be sent.
    Logging of the block should happen at the call site (see audit_log.py).
    """
    if _SYSTEM_LEAK.search(response):
        raise OutputBlocked("Response appears to leak system instructions.")

    if _SSN.search(response):
        raise OutputBlocked("Response contains an SSN-shaped identifier.")

    if _MRN.search(response):
        raise OutputBlocked("Response contains a medical record number.")

    return response


def safe_fallback() -> str:
    """
    The message shown to the patient when a response is blocked. Matches the
    fallback tone in the Agent Operating Profile.
    """
    return ("I'm not able to complete that request automatically. "
            "I can help route this to a care team member for review.")
