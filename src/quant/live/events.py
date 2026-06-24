import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


class EventJournal:
    def __init__(
        self,
        path: Path,
        timezone: str = "Asia/Shanghai",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = path
        self.timezone = ZoneInfo(timezone)
        self.clock = clock or (lambda: datetime.now(self.timezone))
        self._seq = self._load_last_seq()

    @property
    def last_seq(self) -> int:
        return self._seq

    def append(self, event_type: str, payload: dict[str, object]) -> int:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq += 1
        written_at = self.clock()
        if written_at.tzinfo is None or written_at.utcoffset() is None:
            written_at = written_at.replace(tzinfo=self.timezone)
        event = {
            "seq": self._seq,
            "type": event_type,
            "written_at": written_at.isoformat(),
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        return self._seq

    def _load_last_seq(self) -> int:
        if not self.path.exists():
            return 0
        last_seq = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last_seq = int(json.loads(line)["seq"])
        return last_seq
