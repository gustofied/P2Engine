from __future__ import annotations
import os
import math
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from cli.handlers.conversation import stack_view
from infra.async_utils import run_async
from infra.logging.logging_config import logger
from runtime.rollout.engine import run_rollout
from runtime.rollout.spec import MultiRolloutSpec
from runtime.rollout.store import RolloutStore
from runtime.rollout.expander import expand_variants
from services.services import ServiceContainer

# Rerun viz helpers
from infra.observability import rerun_rollout as rr_viz
from infra.observability import rerun_obs as rr_obs

app = typer.Typer(help="Run roll-outs and show a summary.")
console = Console()

_CONTAINER = ServiceContainer()
_RDS = _CONTAINER.get_redis_client()
_STREAM = "stream:rollout_results"
_STYLES = {"header": "bold cyan", "value": "white", "increase": "bold green", "decrease": "bold red"}

# --------------------------- Rerun init ------------------------------------ #
def _init_rerun_for_cli(rollout_id: str, *, spawn: bool = True) -> bool:
    try:
        spawn_effective = spawn and (os.getenv("RERUN_SPAWNED", "0") != "1")
        ok = rr_obs.start_recording(rollout_id, spawn=spawn_effective)
        if ok and spawn_effective:
            os.environ["RERUN_SPAWNED"] = "1"
        if ok:
            logger.info("Rerun ready for rollout_id=%s (spawned=%s)", rollout_id, spawn_effective)
        return ok
    except Exception as e:
        logger.warning("Failed to prepare Rerun for rollout %s: %s", rollout_id, e)
        return False

# -------------------------------- Utilities -------------------------------- #
def _flatten(d: Dict, prefix: str = "") -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in d.items():
        key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v)
    return out

def _collect_cfg_keys(rows: List[Dict]) -> List[str]:
    keys: Set[str] = set()
    for r in rows:
        keys.update(_flatten(r.get("overrides", {})).keys())
    return sorted(keys)

def _rows_to_table(rows: List[Dict[str, Any]], *, with_config: bool = False) -> Table:
    tbl = Table(show_lines=False)
    base_cols = ("team", "variant", "score", "tokens", "cost $", "elapsed s")
    if any(r.get("final_balance") is not None for r in rows):
        base_cols = base_cols + ("final balance", "net flow", "tx count")
    for col in base_cols + (("config",) if with_config else ()):
        tbl.add_column(col, style=_STYLES["value"], justify="right")
    for r in sorted(rows, key=lambda d: (d.get("team_id", ""), d.get("variant_id", ""))):
        score_val = float(r.get("score", 0.0))
        if score_val >= 0.8:
            score_txt = Text(f"{score_val:.3f}", style="bold green")
        elif score_val >= 0.3:
            score_txt = Text(f"{score_val:.3f}", style="yellow")
        else:
            score_txt = Text(f"{score_val:.3f}", style="red")
        row: List[Any] = [
            str(r.get("team_id", "?")),
            str(r.get("variant_id", "?")),
            score_txt,
            f"{int(r.get('tokens', 0)):,}",
            f"{float(r.get('cost', 0.0)):.4f}",
            f"{float(r.get('wall_time', 0.0)):.1f}",
        ]
        if r.get("final_balance") is not None:
            net_flow = float(r.get("net_flow", 0.0))
            if net_flow > 0:
                flow_txt = Text(f"+{net_flow:.2f}", style=_STYLES["increase"])
            elif net_flow < 0:
                flow_txt = Text(f"{net_flow:.2f}", style=_STYLES["decrease"])
            else:
                flow_txt = Text("0.00", style=_STYLES["value"])
            row.extend([f"{float(r.get('final_balance', 0.0)):.2f}", flow_txt, str(r.get("transaction_count", 0))])
        if with_config:
            cfg_preview = r.get("overrides", {})
            if not isinstance(cfg_preview, str):
                cfg_preview = json.dumps(cfg_preview, separators=(",", ":"), ensure_ascii=False)
            if len(cfg_preview) > 40:
                cfg_preview = cfg_preview[:37] + "…"
            row.append(cfg_preview)
        tbl.add_row(*row)
    return tbl

def _render_table_text(table: Table, width: int = 100) -> str:
    tmp = Console(width=width, record=True)
    tmp.print(table)
    return tmp.export_text()

def _config_table(rows: List[Dict[str, Any]]) -> Table:
    keys = _collect_cfg_keys(rows)
    tbl = Table(show_lines=False, header_style=_STYLES["header"])
    tbl.add_column("team"); tbl.add_column("variant")
    for k in keys: tbl.add_column(k, overflow="fold")
    for r in sorted(rows, key=lambda d: (d.get("team_id", ""), d.get("variant_id", ""))):
        flat = _flatten(r.get("overrides", {}))
        cells = [r.get("team_id", "?"), r.get("variant_id", "?")]
        for k in keys:
            v = flat.get(k, "–")
            if len(v) > 25: v = v[:22] + "…"
            cells.append(v)
        tbl.add_row(*cells)
    return tbl

def _flow_markdown(team_id: str, variant_id: str, lines) -> str:
    buf = [f"{team_id} / {variant_id}", ""]
    for ln in lines or []:
        content = ln.content if len(ln.content) <= 120 else (ln.content[:117] + "…")
        buf.append(f"{ln.idx:>3}  {ln.kind:<12}  {content}")
    return "```text\n" + "\n".join(buf) + "\n```"

def _print_flow(rows: List[Dict[str, Any]], *, n: int = 15) -> None:
    console.rule(f"[bold]Flow / stack preview (last {n} steps)")
    for r in rows:
        cid = r.get("conversation_id")
        if not cid:
            continue
        lines = stack_view(_CONTAINER, cid, n=n)
        if not lines:
            continue
        tbl = Table(show_lines=False)
        tbl.add_column(f"{r['variant_id']}", style="cyan")
        for ln in lines:
            snippet = ln.content if len(ln.content) < 60 else ln.content[:57] + "…"
            tbl.add_row(f"[dim]{ln.idx:>3}[/dim]  {ln.kind:<12}  {snippet}")
        console.print(Panel(tbl, title=f"{r['team_id']} / {r['variant_id']}"))

def _aggregate_summary(rows: List[Dict[str, Any]]) -> Table:
    summary: Dict[str, Dict[str, float | int]] = {}
    for r in rows:
        team = r.get("team_id", "—")
        t = summary.setdefault(team, {"variants": 0, "best_score": 0.0, "tokens": 0, "cost": 0.0, "wall_time": 0.0, "total_paid": 0.0, "total_received": 0.0})
        t["variants"] += 1
        t["best_score"] = max(t["best_score"], float(r.get("score", 0.0)))
        t["tokens"] += int(r.get("tokens", 0))
        t["cost"] += float(r.get("cost", 0.0))
        t["wall_time"] = max(t["wall_time"], float(r.get("wall_time", 0.0)))
        net_flow = float(r.get("net_flow", 0.0))
        if net_flow > 0: t["total_received"] += net_flow
        else: t["total_paid"] += abs(net_flow)
    tbl = Table(header_style=_STYLES["header"])
    cols = ["team", "variants", "best score", "tokens", "cost $", "wall-time (s)"]
    if any(t.get("total_paid", 0) > 0 or t.get("total_received", 0) for t in summary.values()):
        cols.extend(["paid out", "received"])
    for col in cols: tbl.add_column(col, style=_STYLES["value"], justify="right")
    for team, m in summary.items():
        row = [team, str(m["variants"]), f"{m['best_score']:.3f}", f"{m['tokens']:,}", f"{m['cost']:.4f}", f"{m['wall_time']:.1f}"]
        if "paid out" in cols: row.extend([f"{m['total_paid']:.2f}", f"{m['total_received']:.2f}"])
        tbl.add_row(*row)
    return tbl

def _parse_fields(fields: Dict[str, str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in fields.items():
        try: out[k] = json.loads(v)
        except Exception: out[k] = v
    return out

# --------------------------- Graph builder ---------------------------------- #
class _GraphBuilder:
    """
    Builds a global node/edge list across all variants and generates
    per-edge 'events' with monotonically increasing times for playback.
    - Colors by VARIANT (handled in rr_viz).
    - Node size by step latency (if timestamps are present on lines).
    """
    def __init__(self, variant_order: List[Tuple[str, str]], *, step_sec: float = 0.15):
        self.positions: List[Tuple[float, float]] = []
        self.meta: List[Dict[str, str]] = []     # [{team, variant, kind, latency}]
        self.edges: List[Tuple[int, int]] = []
        self._node_idx: Dict[str, int] = {}
        self._centers: Dict[Tuple[str, str], Tuple[float, float, float]] = {}
        self._make_centers(variant_order)
        self._t: float = 0.0
        self._step: float = max(0.01, float(step_sec))

    def _make_centers(self, variant_order: List[Tuple[str, str]]) -> None:
        n = max(1, len(variant_order))
        R = 600.0
        for i, pair in enumerate(variant_order):
            theta = 2.0 * math.pi * (i / n)
            cx = R * math.cos(theta)
            cy = R * math.sin(theta)
            self._centers[pair] = (cx, cy, theta)

    def _node_key(self, team: str, variant: str, idx: int) -> str:
        return f"{team}|{variant}|{idx}"

    def add_flow(self, team: str, variant: str, lines: List[Any]) -> List[Dict[str, Any]]:
        """
        Add a flow; returns a list of edge events:
          [{i, j, t, variant, p1:[x,y], p2:[x,y]}, ...]
        """
        events: List[Dict[str, Any]] = []
        if not lines:
            return events

        cx, cy, theta0 = self._centers.get((team, variant), (0.0, 0.0, 0.0))
        r0, dr, dtheta = 40.0, 7.0, 0.35
        prev_global: Optional[int] = None
        prev_ts: Optional[float] = None

        for j, ln in enumerate(lines):
            key = self._node_key(team, variant, int(ln.idx))
            # latency estimate (requires ln.ts if present)
            ts = getattr(ln, "ts", None)
            latency = None
            if ts is not None and prev_ts is not None:
                try:
                    latency = max(0.0, float(ts) - float(prev_ts))
                except Exception:
                    latency = None
            prev_ts = ts if ts is not None else prev_ts

            if key in self._node_idx:
                cur = self._node_idx[key]
            else:
                r = r0 + dr * j
                theta = theta0 + dtheta * j
                x = cx + r * math.cos(theta)
                y = cy + r * math.sin(theta)
                cur = len(self.positions)
                self._node_idx[key] = cur
                self.positions.append((x, y))
                self.meta.append({
                    "team": team,
                    "variant": variant,
                    "kind": getattr(ln, "kind", ""),
                    "latency": str(latency if latency is not None else 0.0),
                })

            if prev_global is not None and prev_global != cur:
                p1 = self.positions[prev_global]; p2 = self.positions[cur]
                events.append({"i": prev_global, "j": cur, "t": self._t, "variant": variant, "p1": [p1[0], p1[1]], "p2": [p2[0], p2[1]]})
                self.edges.append((prev_global, cur))
                self._t += self._step

            prev_global = cur

        return events

# -----------------------------------------------------------------------------
# Streaming collector (prints & updates rerun)
# -----------------------------------------------------------------------------
def _collect_rows(
    team_id: Optional[str],
    rollout_id: str,
    *,
    refresh: float = 2.0,
    to_rerun: bool = False,
    teams_for_tabs: Optional[List[str]] = None,
    variants_for_tabs: Optional[List[Tuple[str, str]]] = None,
    step_sec: float = 0.15,
    animate: bool = True,
) -> List[Dict[str, Any]]:
    store = RolloutStore(_RDS)
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    last_id = "0-0"

    # Build single team doc + graph
    team_docs: Dict[str, List[str]] = {t: [f"# {t}\n"] for t in (teams_for_tabs or [])}
    gb = _GraphBuilder(variants_for_tabs or [], step_sec=step_sec)

    with Live(console=console, refresh_per_second=max(1, int(1 / refresh))) as live:
        while not store.is_done(rollout_id):
            resp = _RDS.xread({_STREAM: last_id}, block=int(refresh * 1000), count=50)
            for _stream, msgs in resp:
                for sid, fields in msgs:
                    last_id = sid
                    data = _parse_fields(fields)
                    if data.get("rollout_id") != rollout_id:
                        continue
                    if team_id and data.get("team_id") != team_id:
                        continue
                    var_id = str(data.get("variant_id"))
                    if var_id in seen:
                        continue
                    seen.add(var_id)
                    rows.append(data)

                    if to_rerun:
                        try:
                            team = str(data.get("team_id", "?"))
                            cid = data.get("conversation_id")
                            lines = stack_view(_CONTAINER, cid, n=15) if cid else None

                            if lines:
                                # aggregate team doc only (no per-variant flow pane)
                                team_docs.setdefault(team, [f"# {team}\n"])
                                team_docs[team].append(f"\n## {var_id}\n")
                                team_docs[team].append(_flow_markdown(team, var_id, lines))
                                rr_viz.log_team_stack_doc(rollout_id, team, "".join(team_docs[team]))

                                # graph
                                events = gb.add_flow(team, var_id, lines)
                                rr_viz.log_graph_static(rollout_id, gb.positions, gb.meta, gb.edges)
                                if animate and events:
                                    rr_viz.log_graph_events(rollout_id, events, timeline="step")
                        except Exception:
                            pass

            live.update(_rows_to_table(rows))

    # Drain late messages
    resp = _RDS.xread({_STREAM: last_id}, block=10, count=50)
    for _stream, msgs in resp:
        for _sid, fields in msgs:
            data = _parse_fields(fields)
            if data.get("rollout_id") != rollout_id:
                continue
            if team_id and data.get("team_id") != team_id:
                continue
            var_id = str(data.get("variant_id"))
            if var_id not in seen:
                rows.append(data)
                seen.add(var_id)
                if to_rerun:
                    try:
                        team = str(data.get("team_id", "?"))
                        cid = data.get("conversation_id")
                        lines = stack_view(_CONTAINER, cid, n=15) if cid else None
                        if lines:
                            team_docs.setdefault(team, [f"# {team}\n"])
                            team_docs[team].append(f"\n## {var_id}\n")
                            team_docs[team].append(_flow_markdown(team, var_id, lines))
                            rr_viz.log_team_stack_doc(rollout_id, team, "".join(team_docs[team]))

                            events = gb.add_flow(team, var_id, lines)
                            rr_viz.log_graph_static(rollout_id, gb.positions, gb.meta, gb.edges)
                            if animate and events:
                                rr_viz.log_graph_events(rollout_id, events, timeline="step")
                    except Exception:
                        pass

    return rows

# --------------------------------- Command --------------------------------- #
@app.command("start")
def start(
    spec_path: Path = typer.Argument(..., exists=True, readable=True),
    parallel: int | None = typer.Option(None, "--parallel", "-p", help="Desired parallelism hint"),
    nowait: bool = typer.Option(False, "--nowait", help="Launch and return immediately"),
    show_config: bool = typer.Option(False, "--show-config", help="Print the expanded rollout spec and exit"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Live-update while running (all teams together)"),
    refresh: float = typer.Option(2.0, "--refresh", "-r", help="Polling interval while following (seconds)"),
    strict_tools: bool = typer.Option(False, "--strict-tools", help="Enforce strict persona/tool validation"),
    rerun: bool = typer.Option(False, "--rerun", help="Open/attach Rerun and visualize config + metrics/graph/team"),
    step_sec: float = typer.Option(0.15, "--step-sec", help="Seconds-per-step for graph timeline (larger = slower)"),
    animate: bool = typer.Option(True, "--animate/--no-animate", help="Log timeline playhead for the graph"),
) -> None:
    multi_spec: MultiRolloutSpec = MultiRolloutSpec.load(spec_path)
    if show_config:
        console.print(multi_spec.model_dump_json(indent=2))
        raise typer.Exit()

    # Prepare data for views
    variants_for_tabs: list[tuple[str, str]] = []
    teams_for_tabs: list[str] = []
    for team_id, team_spec in multi_spec.teams.items():
        teams_for_tabs.append(team_id)
        variants = expand_variants(team_spec)
        for idx, _ in enumerate(variants):
            variants_for_tabs.append((team_id, f"{team_id}:v{idx:03d}"))

    console.print(f"[{_STYLES['header']}]▶ Launching roll-out with {len(multi_spec.teams)} teams…[/{_STYLES['header']}]")
    rollout_id = run_rollout(multi_spec, parallel_hint=parallel, strict_tools=strict_tools)

    # Optional Rerun visualization
    to_rerun = False
    if rerun:
        to_rerun = _init_rerun_for_cli(rollout_id, spawn=True)
        if to_rerun:
            try:
                rr_viz.send_rollout_blueprint(rollout_id, spec_path.name, variants_for_tabs, teams_for_tabs)
                yaml_text = spec_path.read_text(encoding="utf-8", errors="ignore")
                rr_viz.log_rollout_yaml(rollout_id, str(spec_path), yaml_text)
            except Exception:
                pass

    if nowait:
        console.print(f"Roll-out launched – rollout_id = [bold]{rollout_id}[/bold]")
        raise typer.Exit()

    store = RolloutStore(_RDS)

    if follow:
        rows = _collect_rows(
            None,
            rollout_id,
            refresh=refresh,
            to_rerun=to_rerun,
            teams_for_tabs=teams_for_tabs,
            variants_for_tabs=variants_for_tabs,
            step_sec=step_sec,
            animate=animate,
        )
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            transient=True,
        ) as progress:
            completed, total = store.progress(rollout_id)
            task = progress.add_task("Running variants…", total=max(total, 1), completed=completed)
            while not store.is_done(rollout_id):
                new_completed, total = store.progress(rollout_id)
                progress.update(task, total=max(total, 1), completed=new_completed)
                time.sleep(refresh)
        rows = _collect_rows(
            None,
            rollout_id,
            refresh=refresh,
            to_rerun=to_rerun,
            teams_for_tabs=teams_for_tabs,
            variants_for_tabs=variants_for_tabs,
            step_sec=step_sec,
            animate=animate,
        )

    # After run completes, mirror the table in Rerun
    if to_rerun:
        try:
            metrics_text = _render_table_text(_rows_to_table(rows))
            rr_viz.log_cli_metrics(rollout_id, metrics_text)
        except Exception:
            pass

    # READ ONLY snapshots (final "after" is produced by finalise_rollout)
    bj = _RDS.get(f"rollout:{rollout_id}:snapshot:before")
    aj = _RDS.get(f"rollout:{rollout_id}:snapshot:after")
    before_snapshot = json.loads(bj) if bj else None
    after_snapshot = json.loads(aj) if aj else None
    del before_snapshot, after_snapshot  # retained if you want to display diffs

    # Console output
    console.rule("[bold]Roll-out Metrics (per variant)")
    console.print(_rows_to_table(rows))

    console.rule("[bold]Variant Configuration")
    console.print(_config_table(rows))

    console.rule("[bold]Team Aggregate")
    console.print(_aggregate_summary(rows))

    _print_flow(rows)
