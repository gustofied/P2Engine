from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict



class BaseStorageDriver(ABC):
    @abstractmethod
    def write_payload(
        self,
        session_id: str,
        ref: str,
        payload: Any,
        mime: str,
        header: Dict[str, Any],
    ) -> None: ...

    @abstractmethod
    def read_payload(
        self,
        session_id: str,
        ref: str,
        mime: str,
    ) -> Any: ...

    @abstractmethod
    def delete_payload(
        self,
        session_id: str,
        ref: str,
        mime: str,
        compressed: bool,
    ) -> None: ...
