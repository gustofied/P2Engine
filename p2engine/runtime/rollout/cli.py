from __future__ import annotations
import os
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from venv import logger

from cli.handlers.conversation import stack_view
import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from runtime.rollout.engine import run_rollout, capture_ledger_snapshot
from runtime.rollout.spec import MultiRolloutSpec
from runtime.rollout.store import RolloutStore
from services.services import ServiceContainer
from infra.async_utils import run_async

app = typer.Typer(help="Run roll-outs and show a summary.")
console = Console()

_CONTAINER = ServiceContainer()
_RDS = _CONTAINER.get_redis_client()
_STREAM = "stream:rollout_results"
_STYLES = {"header": "bold cyan", "value": "white", "increase": "bold green", "decrease": "bold red"}


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


def _display_ledger_changes(before_snapshot: Dict, after_snapshot: Dict, rollout_start_ts: Optional[float] = None) -> None:
    if not before_snapshot.get("enabled") or not after_snapshot.get("enabled"):
        return
    console.rule("[bold]💰 Ledger State Changes[/bold]")
    metrics_table = Table(title="System Metrics", show_lines=False)
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Before", style="yellow")
    metrics_table.add_column("After", style="green")
    metrics_table.add_column("Change", style="bold")
    before_metrics = before_snapshot.get("metrics", {})
    after_metrics = after_snapshot.get("metrics", {})
    for metric in ["wallet_count", "total_balance", "transaction_count", "total_volume"]:
        before_val = before_metrics.get(metric, 0)
        after_val = after_metrics.get(metric, 0)
        change = after_val - before_val
        if metric in ["total_balance", "total_volume"]:
            before_str = f"{before_val:.2f}"
            after_str = f"{after_val:.2f}"
            change_str = f"+{change:.2f}" if change >= 0 else f"{change:.2f}"
        else:
            before_str = str(int(before_val))
            after_str = str(int(after_val))
            change_str = f"+{int(change)}" if change >= 0 else str(int(change))
        if change > 0:
            change_txt = Text(change_str, style=_STYLES["increase"])
        elif change < 0:
            change_txt = Text(change_str, style=_STYLES["decrease"])
        else:
            change_txt = Text("0", style=_STYLES["value"])
        metrics_table.add_row(metric.replace("_", " ").title(), before_str, after_str, change_txt)
    console.print(metrics_table)
    wallet_table = Table(title="Agent Wallet Changes", show_lines=False)
    wallet_table.add_column("Agent", style="cyan")
    wallet_table.add_column("Before", style="yellow", justify="right")
    wallet_table.add_column("After", style="green", justify="right")
    wallet_table.add_column("Change", style="bold", justify="right")
    wallet_table.add_column("Rollout Txns", style="magenta", justify="center")
    before_wallets = {w["agent_id"]: w for w in before_snapshot.get("wallets", [])}
    after_wallets = {w["agent_id"]: w for w in after_snapshot.get("wallets", [])}
    rollout_start_ts = before_snapshot.get("timestamp", 0)
    agents_data = []
    for agent_id in sorted(set(before_wallets.keys()) | set(after_wallets.keys())):
        before = before_wallets.get(agent_id, {"balance": 0, "transactions": []})
        after = after_wallets.get(agent_id, {"balance": 0, "transactions": []})
        before_balance = float(before.get("balance", 0))
        after_balance = float(after.get("balance", 0))
        actual_change = after_balance - before_balance

        rollout_txs = 0
        rollout_sent = 0.0
        rollout_received = 0.0
        for tx in after.get("transactions", []):
            payload = tx.get("payload", {})
            tx_timestamp = float(payload.get("timestamp", 0))
            if tx_timestamp >= rollout_start_ts:
                rollout_txs += 1
                amount = float(payload.get("amount", 0))
                if payload.get("fromAgent") == agent_id:
                    rollout_sent += amount
                elif payload.get("toAgent") == agent_id:
                    rollout_received += amount

        expected_change = rollout_received - rollout_sent

        if abs(actual_change - expected_change) > 0.01:
            logger.debug(
                f"Balance calculation for {agent_id}: "
                f"before={before_balance:.2f}, after={after_balance:.2f}, "
                f"actual_change={actual_change:.2f}, expected_change={expected_change:.2f}, "
                f"sent={rollout_sent:.2f}, received={rollout_received:.2f}"
            )

        agents_data.append(
            {
                "agent_id": agent_id,
                "before_balance": before_balance,
                "after_balance": after_balance,
                "change": actual_change,
                "rollout_txs": rollout_txs,
                "rollout_sent": rollout_sent,
                "rollout_received": rollout_received,
                "has_activity": abs(actual_change) > 0.01 or rollout_txs > 0,
            }
        )
    agents_data.sort(key=lambda x: (x["has_activity"], abs(x["change"]), x["rollout_txs"]), reverse=True)
    for data in agents_data:
        if not data["has_activity"]:
            continue
        change = data["change"]
        if abs(change) > 0.01:
            if change > 0:
                change_txt = Text(f"+{change:.2f}", style=_STYLES["increase"])
            else:
                change_txt = Text(f"{change:.2f}", style=_STYLES["decrease"])
        else:
            change_txt = Text("0.00", style=_STYLES["value"])
        tx_txt = f"+{data['rollout_txs']}" if data["rollout_txs"] > 0 else "0"
        wallet_table.add_row(data["agent_id"], f"{data['before_balance']:.2f}", f"{data['after_balance']:.2f}", change_txt, tx_txt)
    console.print(wallet_table)


def _config_table(rows: List[Dict[str, Any]]) -> Table:
    keys = _collect_cfg_keys(rows)
    tbl = Table(show_lines=False, header_style=_STYLES["header"])
    tbl.add_column("team")
    tbl.add_column("variant")
    for k in keys:
        tbl.add_column(k, overflow="fold")
    for r in sorted(rows, key=lambda d: (d.get("team_id", ""), d.get("variant_id", ""))):
        flat = _flatten(r.get("overrides", {}))
        cells = [r.get("team_id", "?"), r.get("variant_id", "?")]
        for k in keys:
            v = flat.get(k, "–")
            if len(v) > 25:
                v = v[:22] + "…"
            cells.append(v)
        tbl.add_row(*cells)
    return tbl


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
        t = summary.setdefault(
            team, {"variants": 0, "best_score": 0.0, "tokens": 0, "cost": 0.0, "wall_time": 0.0, "total_paid": 0.0, "total_received": 0.0}
        )
        t["variants"] += 1
        t["best_score"] = max(t["best_score"], float(r.get("score", 0.0)))
        t["tokens"] += int(r.get("tokens", 0))
        t["cost"] += float(r.get("cost", 0.0))
        t["wall_time"] = max(t["wall_time"], float(r.get("wall_time", 0.0)))
        net_flow = float(r.get("net_flow", 0.0))
        if net_flow > 0:
            t["total_received"] += net_flow
        else:
            t["total_paid"] += abs(net_flow)
    tbl = Table(header_style=_STYLES["header"])
    cols = ["team", "variants", "best score", "tokens", "cost $", "wall-time (s)"]
    if any(t.get("total_paid", 0) > 0 or t.get("total_received", 0) > 0 for t in summary.values()):
        cols.extend(["paid out", "received"])
    for col in cols:
        tbl.add_column(col, style=_STYLES["value"], justify="right")
    for team, m in summary.items():
        row = [
            team,
            str(m["variants"]),
            f"{m['best_score']:.3f}",
            f"{m['tokens']:,}",
            f"{m['cost']:.4f}",
            f"{m['wall_time']:.1f}",
        ]
        if "paid out" in cols:
            row.extend([f"{m['total_paid']:.2f}", f"{m['total_received']:.2f}"])
        tbl.add_row(*row)
    return tbl


def _parse_fields(fields: Dict[str, str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in fields.items():
        try:
            out[k] = json.loads(v)
        except Exception:
            out[k] = v
    return out


def _collect_rows(team_id: Optional[str], rollout_id: str, *, refresh: float = 2.0) -> List[Dict[str, Any]]:
    store = RolloutStore(_RDS)
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    last_id = "0-0"
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
            live.update(_rows_to_table(rows))
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
    return rows


@app.command("start")
def start(
    spec_path: Path = typer.Argument(..., exists=True, readable=True),
    parallel: int | None = typer.Option(None, "--parallel", "-p", help="Desired parallelism hint"),
    nowait: bool = typer.Option(False, "--nowait", help="Launch and return immediately"),
    show_config: bool = typer.Option(False, "--show-config", help="Print the expanded rollout spec and exit"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Live-update while running (all teams together)"),
    refresh: float = typer.Option(2.0, "--refresh", "-r", help="Polling interval while following (seconds)"),
    strict_tools: bool = typer.Option(False, "--strict-tools", help="Enforce strict persona/tool validation"),
) -> None:
    multi_spec: MultiRolloutSpec = MultiRolloutSpec.load(spec_path)
    if show_config:
        console.print(multi_spec.model_dump_json(indent=2))
        raise typer.Exit()
    console.print(f"[{_STYLES['header']}]▶ Launching roll-out with {len(multi_spec.teams)} teams…[/{_STYLES['header']}]")
    rollout_id = run_rollout(multi_spec, parallel_hint=parallel, strict_tools=strict_tools)
    if nowait:
        console.print(f"Roll-out launched – rollout_id = [bold]{rollout_id}[/bold]")
        raise typer.Exit()
    store = RolloutStore(_RDS)
    if follow:
        rows = _collect_rows(None, rollout_id, refresh=refresh)
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
        rows = _collect_rows(None, rollout_id, refresh=refresh)
    agent_ids_json = _RDS.get(f"rollout:{rollout_id}:agents")
    agent_ids = []
    if agent_ids_json:
        agent_ids = json.loads(agent_ids_json)
    before_snapshot = None
    after_snapshot = None
    if os.getenv("LEDGER_ENABLED", "true") == "true":
        before_json = _RDS.get(f"rollout:{rollout_id}:snapshot:before")
        if before_json:
            before_snapshot = json.loads(before_json)
        if agent_ids:
            after_snapshot = run_async(capture_ledger_snapshot("after_rollout", agent_ids, wait_for_settle=True))
            _RDS.set(f"rollout:{rollout_id}:snapshot:after", json.dumps(after_snapshot), ex=86400)
    console.rule("[bold]Roll-out Metrics (per variant)")
    console.print(_rows_to_table(rows))
    console.rule("[bold]Variant Configuration")
    console.print(_config_table(rows))
    console.rule("[bold]Team Aggregate")
    console.print(_aggregate_summary(rows))
    if before_snapshot and after_snapshot:
        rollout_start_ts = before_snapshot.get("timestamp")
        _display_ledger_changes(before_snapshot, after_snapshot, rollout_start_ts)
    _print_flow(rows)
