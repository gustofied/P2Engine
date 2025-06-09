from copy import deepcopy
from typing import Any, Dict, List
import itertools
from .spec import TeamSpec


def _deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = deepcopy(dst)
    for k, v in src.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def expand_variants(team_spec: TeamSpec) -> List[Dict[str, Any]]:
    if isinstance(team_spec.variants, list):
        return [_deep_merge(team_spec.base, v) for v in team_spec.variants]
    if isinstance(team_spec.variants, dict):
        keys = list(team_spec.variants.keys())
        values: List[List[Any]] = [team_spec.variants[k] for k in keys]
        combos = (dict(zip(keys, combo)) for combo in itertools.product(*values))
        return [_deep_merge(team_spec.base, c) for c in combos]
    raise TypeError(f"Unsupported variants type: {type(team_spec.variants).__name__}")
