from __future__ import annotations
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class Conversation:
    id: int
    title: str
    owner_id: str
    created_at: str
    updated_at: str


@dataclass
class Message:
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: str


class MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._conv_id = 0
        self._msg_id = 0
        # owner_id -> conv_id -> Conversation
        self._conversations: Dict[str, Dict[int, Conversation]] = {}
        # conv_id -> List[Message]
        self._messages: Dict[int, List[Message]] = {}

    def _next_conv_id(self) -> int:
        with self._lock:
            self._conv_id += 1
            return self._conv_id

    def _next_msg_id(self) -> int:
        with self._lock:
            self._msg_id += 1
            return self._msg_id

    # Conversations
    def list_conversations(self, owner_id: str) -> List[Dict]:
        with self._lock:
            rows = list(self._conversations.get(owner_id, {}).values())
            rows.sort(key=lambda c: c.updated_at, reverse=True)
            return [asdict(c) for c in rows]

    def create_conversation(self, owner_id: str, title: str) -> Dict:
        now = utcnow_iso()
        conv = Conversation(id=self._next_conv_id(), title=title, owner_id=owner_id, created_at=now, updated_at=now)
        with self._lock:
            self._conversations.setdefault(owner_id, {})[conv.id] = conv
            self._messages.setdefault(conv.id, [])
        return asdict(conv)

    def get_conversation(self, owner_id: str, conv_id: int) -> Optional[Dict]:
        with self._lock:
            conv = self._conversations.get(owner_id, {}).get(conv_id)
            return asdict(conv) if conv else None

    def rename_conversation(self, owner_id: str, conv_id: int, title: str) -> Optional[Dict]:
        with self._lock:
            conv = self._conversations.get(owner_id, {}).get(conv_id)
            if not conv:
                return None
            conv.title = title
            conv.updated_at = utcnow_iso()
            return asdict(conv)

    def delete_conversation(self, owner_id: str, conv_id: int) -> bool:
        with self._lock:
            convs = self._conversations.get(owner_id, {})
            if conv_id not in convs:
                return False
            del convs[conv_id]
            self._messages.pop(conv_id, None)
            return True

    # Messages
    def list_messages(self, owner_id: str, conv_id: int) -> Optional[List[Dict]]:
        with self._lock:
            # Ensure ownership
            conv = self._conversations.get(owner_id, {}).get(conv_id)
            if not conv:
                return None
            msgs = list(self._messages.get(conv_id, []))
            # newest first
            msgs.sort(key=lambda m: m.created_at, reverse=True)
            return [asdict(m) for m in msgs]

    def add_message(self, owner_id: str, conv_id: int, role: str, content: str) -> Optional[Dict]:
        now = utcnow_iso()
        with self._lock:
            conv = self._conversations.get(owner_id, {}).get(conv_id)
            if not conv:
                return None
            msg = Message(id=self._next_msg_id(), conversation_id=conv_id, role=role, content=content, created_at=now)
            self._messages.setdefault(conv_id, []).append(msg)
            conv.updated_at = now
            return asdict(msg)


# Singleton
memory_store = MemoryStore()
