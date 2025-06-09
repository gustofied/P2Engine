from .dedup import BaseDedupPolicy, NoDedupPolicy, PenaltyDedupPolicy, StrictDedupPolicy  # noqa: F401 – re-export for convenience

__all__ = [
    "BaseDedupPolicy",
    "NoDedupPolicy",
    "PenaltyDedupPolicy",
    "StrictDedupPolicy",
]
