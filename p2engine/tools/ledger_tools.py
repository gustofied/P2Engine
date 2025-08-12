from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator
from agents.decorators import function_tool
from infra.async_utils import run_async
from infra.logging.logging_config import logger
from services.ledger_service import get_ledger_service


class TransferInput(BaseModel):
    """Input schema for fund transfers"""

    to_agent: str = Field(..., description="Target agent ID to receive funds")
    amount: float = Field(..., gt=0, description="Amount to transfer (must be positive)")
    reason: str = Field(default="", description="Reason for the transfer")

    @validator("amount")
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        if v > 10000:
            raise ValueError("Single transfer cannot exceed 10000")
        return round(v, 2) 


@function_tool(
    name="transfer_funds",
    description="Transfer funds from your wallet to another agent's wallet",
    input_schema=TransferInput,
    requires_context=True,
    side_effect_free=False,
    dedup_ttl=10,  
)
def transfer_funds(
    to_agent: str, amount: float, reason: str = "", creator_id: str = "", conversation_id: str = "", **kwargs: Any
) -> Dict[str, Any]:
    """
    Execute a fund transfer to another agent.

    This will debit your wallet and credit the target agent's wallet.
    The transfer is recorded on the immutable ledger.
    """
    logger.info(f"Transfer request: {creator_id} -> {to_agent}: {amount}")

    async def _execute():
        ledger = await get_ledger_service()

        await ledger.ensure_agent_wallet(creator_id)
        await ledger.ensure_agent_wallet(to_agent)

        result = await ledger.transfer_funds(
            from_agent=creator_id,
            to_agent=to_agent,
            amount=amount,
            reason=reason or f"Transfer via tool call",
            conversation_id=conversation_id,
        )
        return result

    try:
        result = run_async(_execute())

        return {
            "status": "success",
            "data": {
                "transferred": amount,
                "from": creator_id,
                "to": to_agent,
                "transaction_id": result["transaction_id"],
                "new_balance": result["from_balance"],
                "reason": reason,
            },
            "message": f"Successfully transferred {amount} to {to_agent}",
        }
    except ValueError as ve:
        return {"status": "error", "message": str(ve), "error_type": "validation_error"}
    except Exception as exc:
        logger.error(f"Transfer failed: {exc}")
        return {"status": "error", "message": f"Transfer failed: {str(exc)}", "error_type": "transfer_error"}


class BalanceInput(BaseModel):
    """Input schema for balance checks"""

    agent_id: Optional[str] = Field(None, description="Agent ID to check balance for (defaults to self)")


@function_tool(
    name="check_balance",
    description="Check the current balance of an agent's wallet",
    input_schema=BalanceInput,
    requires_context=True,
    side_effect_free=True,
    cache_ttl=30,
)
def check_balance(agent_id: Optional[str] = None, creator_id: str = "", **kwargs: Any) -> Dict[str, Any]:
    """
    Check wallet balance for yourself or another agent.

    If no agent_id is provided, returns your own balance.
    """
    target_agent = agent_id or creator_id

    async def _execute():
        ledger = await get_ledger_service()
        await ledger.ensure_agent_wallet(target_agent)
        balance = await ledger.get_agent_balance(target_agent)
        return balance

    try:
        balance = run_async(_execute())

        return {
            "status": "success",
            "data": {"agent": target_agent, "balance": balance, "formatted": f"{balance:.2f}"},
            "message": f"Balance for {target_agent}: {balance:.2f}",
        }
    except Exception as exc:
        logger.error(f"Balance check failed: {exc}")
        return {"status": "error", "message": f"Failed to check balance: {str(exc)}"}


class HistoryInput(BaseModel):
    """Input schema for transaction history"""

    limit: int = Field(default=10, ge=1, le=100, description="Number of transactions to retrieve")


@function_tool(
    name="transaction_history",
    description="Get your recent transaction history",
    input_schema=HistoryInput,
    requires_context=True,
    side_effect_free=True,
    cache_ttl=60,
)
def transaction_history(limit: int = 10, creator_id: str = "", **kwargs: Any) -> Dict[str, Any]:
    """
    Retrieve your transaction history from the ledger.

    Returns the most recent transactions (both sent and received).
    """

    async def _execute():
        ledger = await get_ledger_service()
        history = await ledger.get_transaction_history(creator_id, limit)
        return history

    try:
        transactions = run_async(_execute())

        formatted_txs = []
        for tx in transactions:
            payload = tx.get("payload", {})
            formatted_txs.append(
                {
                    "type": "sent" if payload.get("fromAgent") == creator_id else "received",
                    "amount": float(payload.get("amount", 0)),
                    "other_party": (payload.get("toAgent") if payload.get("fromAgent") == creator_id else payload.get("fromAgent")),
                    "reason": payload.get("reason", ""),
                    "timestamp": payload.get("timestamp", 0),
                    "id": tx.get("contractId", ""),
                }
            )

        return {
            "status": "success",
            "data": {"transactions": formatted_txs, "count": len(formatted_txs), "agent": creator_id},
            "message": f"Found {len(formatted_txs)} transactions",
        }
    except Exception as exc:
        logger.error(f"History retrieval failed: {exc}")
        return {"status": "error", "message": f"Failed to retrieve history: {str(exc)}"}


class RewardInput(BaseModel):
    """Input schema for rewarding agents"""

    agent_id: str = Field(..., description="Agent to reward")
    amount: float = Field(default=10.0, gt=0, le=100, description="Reward amount")
    reason: str = Field(default="Good work!", description="Reason for reward")


@function_tool(
    name="reward_agent",
    description="Reward another agent for good performance or assistance",
    input_schema=RewardInput,
    requires_context=True,
    side_effect_free=False,
)
def reward_agent(
    agent_id: str, amount: float = 10.0, reason: str = "Good work!", creator_id: str = "", conversation_id: str = "", **kwargs: Any
) -> Dict[str, Any]:
    """
    Send a reward to another agent.

    This is a convenience function that wraps transfer_funds
    with reward-specific semantics.
    """
    return transfer_funds(
        to_agent=agent_id, amount=amount, reason=f"Reward: {reason}", creator_id=creator_id, conversation_id=conversation_id, **kwargs
    )
