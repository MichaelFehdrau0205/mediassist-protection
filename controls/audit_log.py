"""
audit_log.py  —  Tamper-evident access logging

Why
---
HIPAA and your threat model both require knowing WHO accessed WHAT and WHEN. Logs
are also the only way to detect a breach after the fact, and the "Repudiation"
column in your STRIDE table is highest-risk precisely when logs are missing or
editable.

Two design points from your own documents:
  1. Log the ACCESS EVENT, not the medical content. Logs that contain PHI just
     become a second copy of the data to protect. Record that patient 1001's
     record was read at 10:03 by session X — not what was in it.
  2. Make tampering detectable. Each entry includes a hash chained to the
     previous entry (like a tiny blockchain). If someone edits or deletes a past
     line, the chain breaks and verify_chain() catches it.
"""

import hashlib
import json
import time
from dataclasses import dataclass, asdict, field


@dataclass
class LogEntry:
    timestamp: float
    session_id: str
    actor_patient_id: str
    action: str              # e.g. "read_record", "book_appointment", "denied_access"
    target: str              # e.g. patient id or resource touched
    allowed: bool
    detail: str = ""
    prev_hash: str = ""
    entry_hash: str = field(default="")

    def compute_hash(self) -> str:
        # Hash every field except entry_hash itself. Chaining prev_hash means
        # each line depends on all lines before it.
        payload = {k: v for k, v in asdict(self).items() if k != "entry_hash"}
        blob = json.dumps(payload, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()


class AuditLog:
    """
    An append-only audit log. In production this would write to durable,
    write-once storage. Here it is in memory so tests can run.
    """

    def __init__(self):
        self._entries: list[LogEntry] = []

    def record(self, *, session_id: str, actor_patient_id: str, action: str,
               target: str, allowed: bool, detail: str = "") -> LogEntry:
        prev_hash = self._entries[-1].entry_hash if self._entries else "GENESIS"
        entry = LogEntry(
            timestamp=time.time(),
            session_id=session_id,
            actor_patient_id=actor_patient_id,
            action=action,
            target=target,
            allowed=allowed,
            detail=detail,
            prev_hash=prev_hash,
        )
        entry.entry_hash = entry.compute_hash()
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        """
        Returns True if no entry has been altered or removed. If someone tampers
        with a past line, its hash no longer matches and the next line's
        prev_hash no longer lines up — so this returns False.
        """
        prev_hash = "GENESIS"
        for entry in self._entries:
            if entry.prev_hash != prev_hash:
                return False
            if entry.entry_hash != entry.compute_hash():
                return False
            prev_hash = entry.entry_hash
        return True

    def entries(self) -> list[LogEntry]:
        return list(self._entries)
