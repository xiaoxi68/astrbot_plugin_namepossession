import asyncio
import json
import os
import tempfile
from typing import Any

from astrbot.api import logger


class StateStore:
    """Async, concurrency-safe JSON state store for per-group possession info.

    Schema example (in-file):
    {
      "taken": { "<self_id>#<group_id>": {"user_id": 123456, "name": "某某"} }
    }
    Note: Feature flags (like auto_enabled) belong to AstrBotConfig, not here.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._state: dict[str, Any] = {"taken": {}}
        self._lock = asyncio.Lock()
        self._ensure_dir()

    async def initialize(self) -> None:
        """Load from disk once at startup, non-blocking for event loop."""
        await self._load()

    def _ensure_dir(self) -> None:
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    async def _load(self) -> None:
        if not os.path.exists(self.file_path):
            await self._save()
            logger.info(f"namepossession: state file created at {self.file_path}")
            return
        try:
            data = await asyncio.to_thread(self._read_json_file)
            if isinstance(data, dict):
                async with self._lock:
                    # only accepted top-level keys
                    taken = data.get("taken") or {}
                    if isinstance(taken, dict):
                        self._state["taken"] = taken
        except Exception as e:
            # keep defaults if corrupted, but do not swallow silently
            logger.warning(
                "namepossession: failed to load state file %s: %s",
                self.file_path,
                e,
            )

    def _read_json_file(self) -> dict:
        with open(self.file_path, encoding="utf-8") as f:
            return json.load(f)

    async def _save(self) -> None:
        async with self._lock:
            state = json.dumps(self._state, ensure_ascii=False, indent=2)
        try:
            await asyncio.to_thread(self._atomic_write, state)
        except Exception as e:
            logger.error(
                "namepossession: failed to save state file %s: %s",
                self.file_path,
                e,
            )
            raise

    def _atomic_write(self, content: str) -> None:
        dir_name = os.path.dirname(self.file_path)
        base_name = os.path.basename(self.file_path)
        fd, tmp_path = tempfile.mkstemp(prefix=f".{base_name}.", dir=dir_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp:
                tmp.write(content)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, self.file_path)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    def key(self, self_id: str, group_id: str) -> str:
        return f"{self_id}#{group_id}"

    async def set_taken(
        self, self_id: str, group_id: str, user_id: int, name: str
    ) -> None:
        async with self._lock:
            k = self.key(self_id, group_id)
            self._state.setdefault("taken", {})[k] = {"user_id": user_id, "name": name}
        await self._save()

    async def get_taken(self, self_id: str, group_id: str) -> dict | None:
        async with self._lock:
            return self._state.get("taken", {}).get(self.key(self_id, group_id))

    async def clear_taken(self, self_id: str, group_id: str) -> None:
        async with self._lock:
            self._state.get("taken", {}).pop(self.key(self_id, group_id), None)
        await self._save()
