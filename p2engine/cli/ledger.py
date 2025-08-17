# cli/ledger.py
import json
from datetime import datetime
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from infra.async_utils import run_async
from services.ledger_service import get_ledger_service
from ._ui import STYLES, console
import os
import requests
from infra.logging.logging_config import logger

app = typer.Typer(help="Canton ledger operations and audit trail")


@app.command("balance")
def balance_cmd(
    ctx: typer.Context,
    agent_id: str = typer.Argument(..., help="Agent ID to check balance"),
) -> None:
    """Check the balance of an agent's wallet"""

    async def _check():
        ledger = await get_ledger_service()
        await ledger.ensure_agent_wallet(agent_id)
        return await ledger.get_agent_balance(agent_id)

    try:
        balance = run_async(_check())
        table = Table(show_header=False, box=None)
        table.add_column("Field", style=STYLES["name"])
        table.add_column("Value", style=STYLES["value"])

        table.add_row("Agent", agent_id)
        table.add_row("Balance", f"{balance:.2f}")

        panel = Panel(table, title=f"[bold]Wallet Balance[/bold]", border_style="cyan")
        console.print(panel)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")


@app.command("transfer")
def transfer_cmd(
    ctx: typer.Context,
    from_agent: str = typer.Argument(..., help="Source agent ID"),
    to_agent: str = typer.Argument(..., help="Target agent ID"),
    amount: float = typer.Argument(..., help="Amount to transfer"),
    reason: str = typer.Option("Manual transfer", "--reason", "-r", help="Transfer reason"),
) -> None:
    """Transfer funds between agent wallets"""
    if amount <= 0:
        console.print("[red]Error: Amount must be positive[/red]")
        raise typer.Exit(1)

    async def _transfer():
        ledger = await get_ledger_service()
        return await ledger.transfer_funds(from_agent=from_agent, to_agent=to_agent, amount=amount, reason=reason)

    try:
        result = run_async(_transfer())
        console.print(f"[green]✓ Transfer successful![/green]")
        console.print(f"  Transaction ID: {result['transaction_id']}")
        console.print(f"  {from_agent} new balance: {result['from_balance']:.2f}")
        console.print(f"  {to_agent} new balance: {result['to_balance']:.2f}")
    except Exception as exc:
        console.print(f"[red]Transfer failed: {exc}[/red]")


@app.command("history")
def history_cmd(
    ctx: typer.Context,
    agent_id: str = typer.Argument(..., help="Agent ID to show history for"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of transactions to show"),
) -> None:
    """Show transaction history for an agent"""

    async def _get_history():
        ledger = await get_ledger_service()
        return await ledger.get_transaction_history(agent_id, int(limit))

    try:
        transactions = run_async(_get_history())
        if not transactions:
            console.print(f"[yellow]No transactions found for {agent_id}[/yellow]")
            return

        table = Table(title=f"Transaction History for {agent_id}", header_style=STYLES["header"])
        table.add_column("Time", style=STYLES["timestamp"])
        table.add_column("Type", style=STYLES["kind"])
        table.add_column("Amount", justify="right", style=STYLES["value"])
        table.add_column("Other Party", style=STYLES["name"])
        table.add_column("Reason", style=STYLES["content"])

        for tx in transactions:
            payload = tx.get("payload", {})
            is_sent = payload.get("fromAgent") == agent_id
            tx_type = Text("↑ SENT", style="red") if is_sent else Text("↓ RECV", style="green")

            timestamp_raw = payload.get("timestamp", 0)
            try:
                timestamp = float(timestamp_raw) if timestamp_raw else 0
            except (ValueError, TypeError):
                timestamp = 0

            time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") if timestamp > 0 else "Unknown"
            other_party = payload.get("toAgent") if is_sent else payload.get("fromAgent")
            amount = float(payload.get("amount", 0))
            amount_str = f"-{amount:.2f}" if is_sent else f"+{amount:.2f}"
            amount_text = Text(amount_str, style="red" if is_sent else "green")

            table.add_row(time_str, tx_type, amount_text, other_party or "Unknown", payload.get("reason", "-")[:50])

        console.print(table)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")


@app.command("audit")
def audit_cmd(
    ctx: typer.Context,
    since: Optional[str] = typer.Option(None, "--since", help="ISO timestamp to filter from"),
    event_type: Optional[str] = typer.Option(None, "--type", help="Filter by event type"),
    limit: int = typer.Option(50, "--limit", help="Maximum events to show"),
) -> None:
    """Show ledger audit trail"""
    from infra.artifacts.bus import get_bus
    from infra.logging.logging_config import logger

    bus = get_bus()
    redis_client = bus.redis

    ledger_sessions = []
    patterns = [
        "artifacts:ledger:*:index",
        "artifacts:ledger_*:index",
    ]

    for pattern in patterns:
        for key in redis_client.keys(pattern):
            key_str = key.decode() if isinstance(key, bytes) else key
            parts = key_str.split(":")
            if len(parts) >= 3:
                session_id = ":".join(parts[1:-1])
                if session_id not in ledger_sessions:
                    ledger_sessions.append(session_id)

    party_id = os.getenv("LEDGER_PARTY_ID", "p2engine::default")
    additional_patterns = [f"ledger:{party_id}", f"ledger:{party_id.replace('::', '_')}", "ledger:p2engine_default"]

    for pattern in additional_patterns:
        test_key = f"artifacts:{pattern}:index"
        if redis_client.exists(test_key):
            if pattern not in ledger_sessions:
                ledger_sessions.append(pattern)

    if not ledger_sessions:
        console.print("[yellow]No ledger sessions found. Ledger events may not have been recorded yet.[/yellow]")
        return

    events = []
    for session_id in ledger_sessions:
        try:
            session_events = bus.search(session_id=session_id, tag=event_type, since=since, limit=limit)
            events.extend(session_events)
        except Exception as exc:
            logger.debug(f"Failed to search session {session_id}: {exc}")
            continue

    if not events:
        console.print("[yellow]No ledger events found[/yellow]")
        console.print(f"[dim]Searched sessions: {', '.join(ledger_sessions)}[/dim]")
        return

    # Sort by timestamp
    events.sort(key=lambda x: x[0]["ts"], reverse=True)
    events = events[:limit]

    table = Table(title="Ledger Audit Trail", header_style=STYLES["header"])
    table.add_column("Timestamp", style=STYLES["timestamp"])
    table.add_column("Event Type", style=STYLES["kind"])
    table.add_column("Details", style=STYLES["content"])

    for header, payload in events:
        event_type = header.get("meta", {}).get("event_type", "unknown")

        if event_type == "wallet_created":
            details = f"Agent: {payload.get('agent_id')}, Initial: {payload.get('initial_balance')}"
        elif event_type == "transfer_executed":
            details = (
                f"{payload.get('from_agent')} → {payload.get('to_agent')}: "
                f"{payload.get('amount')} ({payload.get('reason', 'No reason')})"
            )
        else:
            details = json.dumps(payload, indent=2)[:100] + "..."

        table.add_row(header["ts"], event_type, details)

    console.print(table)


@app.command("metrics")
def metrics_cmd(ctx: typer.Context) -> None:
    """Show ledger system metrics"""

    async def _get_metrics():
        ledger = await get_ledger_service()
        return await ledger.get_system_metrics()

    try:
        metrics = run_async(_get_metrics())

        table = Table(show_header=False, box=None)
        table.add_column("Metric", style=STYLES["name"])
        table.add_column("Value", justify="right", style=STYLES["value"])

        table.add_row("Active Wallets", str(metrics.get("wallet_count", 0)))
        table.add_row("Total Balance", f"{metrics.get('total_balance', 0):.2f}")
        table.add_row("Total Transactions", str(metrics.get("transaction_count", 0)))
        table.add_row("Total Volume", f"{metrics.get('total_volume', 0):.2f}")
        table.add_row("Average Balance", f"{metrics.get('average_balance', 0):.2f}")

        panel = Panel(table, title="[bold]Ledger System Metrics[/bold]", border_style="cyan")
        console.print(panel)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")


@app.command("init")
def init_wallets_cmd(
    ctx: typer.Context,
    initial_balance: float = typer.Option(100.0, "--balance", help="Initial balance for new wallets"),
) -> None:
    """Initialize wallets for all configured agents"""

    async def _init_all():
        from infra import config_loader as cfg

        ledger = await get_ledger_service()

    
        agent_configs = cfg.agents()
        agent_ids = [cfg.id for cfg in agent_configs]

        additional_agents = ["treasurer", "agent_helper", "child"]
        all_agents = list(set(agent_ids + additional_agents))

        results = []
        for agent_id in all_agents:
            try:
                contract_id = await ledger.create_agent_wallet(agent_id, initial_balance)
                balance = await ledger.get_agent_balance(agent_id)
                results.append((agent_id, "success", balance))
                logger.info(f"Created wallet for {agent_id} with balance {balance}")
            except Exception as exc:
                if "already exists" in str(exc) or "DUPLICATE_CONTRACT_KEY" in str(exc):
                    try:
                        balance = await ledger.get_agent_balance(agent_id)
                        results.append((agent_id, "exists", balance))
                    except:
                        results.append((agent_id, "error", str(exc)))
                else:
                    results.append((agent_id, "failed", str(exc)))

        return results

    results = run_async(_init_all())

    table = Table(title="Wallet Initialization Results", header_style=STYLES["header"])
    table.add_column("Agent", style=STYLES["name"])
    table.add_column("Status", style=STYLES["kind"])
    table.add_column("Balance", style=STYLES["value"])

    for agent_id, status, value in results:
        if status == "success":
            table.add_row(agent_id, "[green]✓ Created[/green]", f"{value:.2f}")
        elif status == "exists":
            table.add_row(agent_id, "[yellow]✓ Exists[/yellow]", f"{value:.2f}")
        else:
            table.add_row(agent_id, "[red]✗ Failed[/red]", str(value)[:50])

    console.print(table)


@app.command("debug")
def debug_canton_cmd(ctx: typer.Context) -> None:
    """Debug Canton connection and configuration"""

    async def _debug():
        from services.ledger_service import get_ledger_service

        results = []

   
        try:
            response = requests.get("http://localhost:7575/livez", timeout=5)
            results.append(("JSON API Health", "✓", f"Status: {response.status_code}"))
        except Exception as e:
            results.append(("JSON API Health", "✗", str(e)))

     
        package_id = os.getenv("DAML_PACKAGE_ID")
        if package_id:
            results.append(("Package ID", "✓", package_id[:20] + "..."))
        else:
            results.append(("Package ID", "✗", "Not set"))

       
        try:
            ledger = await get_ledger_service()
            results.append(("Ledger Service", "✓", "Initialized"))

     
            party_id = await ledger._ensure_party()
            results.append(("Party ID", "✓", party_id))

      
            metrics = await ledger.get_system_metrics()
            results.append(("Wallet Query", "✓", f"{metrics.get('wallet_count', 0)} wallets"))
        except Exception as e:
            results.append(("Ledger Service", "✗", str(e)[:50]))

        return results

    results = run_async(_debug())

    table = Table(title="Canton Debug Information", header_style=STYLES["header"])
    table.add_column("Check", style=STYLES["name"])
    table.add_column("Status", style=STYLES["kind"])
    table.add_column("Details", style=STYLES["value"])

    for check, status, details in results:
        table.add_row(check, status, details)

    console.print(table)


@app.command("overview")
def overview_cmd(ctx: typer.Context) -> None:
    """Show comprehensive ledger overview with all wallets and metrics"""

    async def _get_overview():
        ledger = await get_ledger_service()
        
        from infra import config_loader as cfg

        agent_configs = cfg.agents()
        known_agents = [cfg.id for cfg in agent_configs]
        known_agents.extend(["treasurer", "agent_helper", "child"])
        known_agents = list(set(known_agents))

        wallets = []
        for agent_id in known_agents:
            try:
                balance = await ledger.get_agent_balance(agent_id)
                history = await ledger.get_transaction_history(agent_id, limit=5)
                wallets.append(
                    {"agent_id": agent_id, "balance": balance, "tx_count": len(history), "last_tx": history[0] if history else None}
                )
            except Exception as exc:
                logger.debug(f"No wallet for {agent_id}: {exc}")
                continue

        metrics = await ledger.get_system_metrics()
        return wallets, metrics

    try:
        wallets, metrics = run_async(_get_overview())

       
        metrics_table = Table(show_header=False, box=None)
        metrics_table.add_column("Metric", style=STYLES["name"])
        metrics_table.add_column("Value", justify="right", style=STYLES["value"])

        metrics_table.add_row("Total Wallets", str(metrics.get("wallet_count", 0)))
        metrics_table.add_row("Total Balance", f"{metrics.get('total_balance', 0):.2f}")
        metrics_table.add_row("Total Transactions", str(metrics.get("transaction_count", 0)))
        metrics_table.add_row("Total Volume", f"{metrics.get('total_volume', 0):.2f}")

        console.print(Panel(metrics_table, title="[bold]System Overview[/bold]", border_style="cyan"))

     
        if wallets:
            wallet_table = Table(title="Agent Wallets", header_style=STYLES["header"])
            wallet_table.add_column("Agent", style=STYLES["name"])
            wallet_table.add_column("Balance", justify="right", style=STYLES["value"])
            wallet_table.add_column("Transactions", justify="center", style=STYLES["kind"])
            wallet_table.add_column("Last Activity", style=STYLES["timestamp"])
            wallet_table.add_column("Status", style=STYLES["kind"])

            for wallet in sorted(wallets, key=lambda w: w["agent_id"]):
                last_activity = "Never"
                if wallet["last_tx"]:
                    try:
                        ts = float(wallet["last_tx"]["payload"].get("timestamp", 0))
                        if ts > 0:
                            last_activity = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                    except:
                        pass

                balance_text = f"{wallet['balance']:.2f}"
                status_text = Text("Active", style="green") if wallet["tx_count"] > 0 else Text("Initialized", style="yellow")

                wallet_table.add_row(wallet["agent_id"], balance_text, str(wallet["tx_count"]), last_activity, status_text)

            console.print(wallet_table)
        else:
            console.print("[yellow]No wallets found. Run 'ledger init' first.[/yellow]")

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
