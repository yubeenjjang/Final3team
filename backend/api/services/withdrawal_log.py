"""탈퇴 기록 — DB 백업과 따로 보관해 복원 뒤 탈퇴 계정을 다시 정리한다 (DB 설계서 7-0 ⑥).

한 줄에 `{"user_id": "...", "deleted_at": "..."}`만 적는다(이메일·닉네임 등 개인정보 없음).
위치는 `WITHDRAWAL_LOG_PATH`이며 DB 볼륨·DB 백업과 다른 곳이어야 한다.
"""
import fcntl
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

_logger = logging.getLogger(__name__)
DEFAULT_KEEP_DAYS = 8  # DB 백업 7일보다 하루 길게


def log_path() -> Path:
    configured = os.environ.get("WITHDRAWAL_LOG_PATH", "").strip()
    if configured:
        return Path(configured)
    state = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state) / "noldaga" / "withdrawals.jsonl"


def keep_days() -> int:
    try:
        return max(1, int(os.environ.get("WITHDRAWAL_LOG_KEEP_DAYS", DEFAULT_KEEP_DAYS)))
    except ValueError:
        return DEFAULT_KEEP_DAYS


def append(user_id: UUID, deleted_at: datetime) -> bool:
    """커밋된 탈퇴를 한 줄 추가한다. 실패해도 탈퇴는 유지되므로 오류를 기록하고 False를 돌려준다."""
    path = log_path()
    line = json.dumps({"user_id": str(user_id), "deleted_at": deleted_at.astimezone(timezone.utc).isoformat()})
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return True
    except OSError:
        _logger.error("Withdrawal log write failed; re-run account cleanup manually after any DB restore.",
                      extra={"user_id": str(user_id)})
        return False


def entries() -> list[tuple[UUID, datetime]]:
    path = log_path()
    if not path.exists():
        return []
    found: list[tuple[UUID, datetime]] = []
    with path.open(encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_SH)
        for raw in handle:
            try:
                row = json.loads(raw)
                found.append((UUID(row["user_id"]), datetime.fromisoformat(row["deleted_at"])))
            except (ValueError, KeyError, TypeError):
                _logger.warning("Skipped an unreadable withdrawal log line.")
    return found


def prune(now: datetime) -> int:
    """보관 기간이 지난 줄을 지운다. 지운 줄 수를 돌려준다."""
    path = log_path()
    if not path.exists():
        return 0
    cutoff = now - timedelta(days=keep_days())
    with path.open("r+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        lines = handle.readlines()
        kept = []
        for raw in lines:
            try:
                if datetime.fromisoformat(json.loads(raw)["deleted_at"]) >= cutoff:
                    kept.append(raw)
            except (ValueError, KeyError, TypeError):
                kept.append(raw)  # 읽을 수 없는 줄은 사람이 확인하도록 남긴다
        handle.seek(0)
        handle.writelines(kept)
        handle.truncate()
        handle.flush()
        os.fsync(handle.fileno())
    return len(lines) - len(kept)
