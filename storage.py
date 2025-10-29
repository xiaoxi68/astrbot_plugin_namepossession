import json
import os


class StateStore:
    """A minimal JSON-based state store for per-group possession info.

    Schema example:
    {
        "auto_enabled": false,
        "taken": {
            "<self_id>#<group_id>": {
                "user_id": 123456,
                "name": "某某"
            }
        }
    }
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._state: dict = {"auto_enabled": False, "taken": {}}
        self._ensure_dir()
        self._load()

    def _ensure_dir(self) -> None:
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def _load(self) -> None:
        if not os.path.exists(self.file_path):
            self._save()
            return
        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._state.update(data)
        except Exception:
            # keep defaults if corrupted
            pass

    def _save(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)

    def key(self, self_id: str, group_id: str) -> str:
        return f"{self_id}#{group_id}"

    def set_taken(self, self_id: str, group_id: str, user_id: int, name: str) -> None:
        k = self.key(self_id, group_id)
        self._state.setdefault("taken", {})[k] = {"user_id": user_id, "name": name}
        self._save()

    def get_taken(self, self_id: str, group_id: str) -> dict | None:
        return self._state.get("taken", {}).get(self.key(self_id, group_id))

    def clear_taken(self, self_id: str, group_id: str) -> None:
        self._state.get("taken", {}).pop(self.key(self_id, group_id), None)
        self._save()

    def set_auto_enabled(self, enabled: bool) -> None:
        self._state["auto_enabled"] = bool(enabled)
        self._save()

    def is_auto_enabled(self) -> bool:
        return bool(self._state.get("auto_enabled", False))

