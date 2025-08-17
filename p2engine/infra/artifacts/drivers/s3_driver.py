from __future__ import annotations

from typing import Any, Dict

from .base import BaseStorageDriver


class S3StorageDriver(BaseStorageDriver):
    """
    Stub retained – signature updated to match BaseStorageDriver.
    """

    def __init__(self, bucket: str):
        self.bucket = bucket

    def write_payload(self, session_id: str, ref: str, payload: Any, mime: str, header: Dict[str, Any]) -> None:
        raise NotImplementedError("S3 support not implemented yet")

    def read_payload(self, session_id: str, ref: str, mime: str) -> Any:
        raise NotImplementedError("S3 support not implemented yet")

    def delete_payload(self, session_id: str, ref: str, mime: str, compressed: bool) -> None:
        raise NotImplementedError("S3 support not implemented yet")
