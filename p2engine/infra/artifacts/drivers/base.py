from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

# NOTE:  The interface now passes the full header *including mime* to give
#        drivers access to compression flags, raw_len, etc.


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
