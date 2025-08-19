from __future__ import annotations
import json
import time
import asyncio
import os
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import requests
from datetime import datetime
import jwt
import contextlib

from infra.logging.logging_config import logger
from infra.artifacts.bus import get_bus
from infra.artifacts.schema import ArtifactHeader, current_timestamp, generate_ref
from infra.config_loader import settings
from infra.logging.metrics import metrics


@dataclass
class LedgerConfig:
    json_api_url: str = "http://localhost:7575"
    party_id: str = "p2engine::default"
    application_id: str = "p2engine"
    initial_balance: float = 100.0
    cache_ttl: int = 60
    ledger_id: str = "p2engine"
    connection_timeout: int = 60
    retry_delay: int = 5
    max_retries: int = 10
    package_id: Optional[str] = None


@dataclass
class WalletInfo:
    contract_id: str
    agent_id: str
    balance: float
    last_updated: float


class CantonLedgerService:
    _instance: Optional["CantonLedgerService"] = None
    _lock = asyncio.Lock()

    def __init__(self, config: Optional[LedgerConfig] = None):
        self.config = config or LedgerConfig()
        self.headers = {"Content-Type": "application/json"}
        self.package_id = self.config.package_id or os.getenv("DAML_PACKAGE_ID")
        if not self.package_id:
            logger.warning("DAML_PACKAGE_ID not set - ledger operations may fail")
        if os.getenv("LEDGER_DEV_MODE", "true") == "true":
            dummy_payload = {
                "https://daml.com/ledger-api": {
                    "ledgerId": self.config.ledger_id,
                    "participantId": "participant",
                    "applicationId": self.config.application_id,
                    "actAs": [self.config.party_id],
                    "readAs": [self.config.party_id],
                },
                "sub": "participant",
                "exp": int(time.time()) + 86400,
                "aud": "participant",
            }
            dummy_token = jwt.encode(dummy_payload, "test", algorithm="HS256")
            if isinstance(dummy_token, bytes):
                dummy_token = dummy_token.decode()
            self.headers["Authorization"] = f"Bearer {dummy_token}"
            logger.info("Running in dev mode - using test JWT token")
        else:
            logger.info("Running in production mode - proper auth required")
        self._wallet_cache: Dict[str, WalletInfo] = {}
        self._initialized_agents: set[str] = set()
        self._actual_party_id: Optional[str] = None
        self._connection_verified = False
        logger.info(
            "CantonLedgerService initialized",
            extra={
                "json_api_url": self.config.json_api_url,
                "party_id": self.config.party_id,
                "ledger_id": self.config.ledger_id,
                "package_id": self.package_id,
                "dev_mode": os.getenv("LEDGER_DEV_MODE", "true"),
            },
        )

    def _get_template_id(self, module: str, entity: str) -> str:
        if not self.package_id:
            raise ValueError("DAML_PACKAGE_ID not set - cannot construct template ID")
        return f"{self.package_id}:{module}:{entity}"

    @classmethod
    async def get_instance(cls, config: Optional[LedgerConfig] = None) -> "CantonLedgerService":
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config)
                    await cls._instance._verify_connection()
        return cls._instance

    def _update_token_with_party(self, party_id: str):
        if os.getenv("LEDGER_DEV_MODE", "true") == "true":
            dummy_payload = {
                "https://daml.com/ledger-api": {
                    "ledgerId": self.config.ledger_id,
                    "participantId": "participant",
                    "applicationId": self.config.application_id,
                    "actAs": [party_id],
                    "readAs": [party_id],
                },
                "sub": "participant",
                "exp": int(time.time()) + 86400,
                "aud": "participant",
            }
            dummy_token = jwt.encode(dummy_payload, "test", algorithm="HS256")
            if isinstance(dummy_token, bytes):
                dummy_token = dummy_token.decode()
            self.headers["Authorization"] = f"Bearer {dummy_token}"

    async def _verify_connection(self) -> None:
        max_attempts = self.config.max_retries
        attempt = 0
        while attempt < max_attempts:
            try:
                health_url = f"{self.config.json_api_url}/livez"
                with contextlib.suppress(Exception):
                    if requests.get(health_url, timeout=2).status_code == 200:
                        logger.info("JSON API health check passed")
                        self._connection_verified = True
                        break
            except Exception as exc:
                logger.warning(f"Connection attempt {attempt + 1}/{max_attempts} failed: {exc}")
            attempt += 1
            if attempt < max_attempts:
                await asyncio.sleep(self.config.retry_delay)
        if self._connection_verified:
            logger.info("Waiting for Canton domain connection to stabilize...")
            await asyncio.sleep(10)
            await self._ensure_party()
            logger.info("Canton connection verified and party established")
        else:
            logger.error("Failed to connect to Canton after all attempts")

    async def _ensure_party(self) -> str:
        if self._actual_party_id:
            return self._actual_party_id
        party_hint = self.config.party_id.replace("::", "_")
        for attempt in range(self.config.max_retries):
            try:
                parties_url = f"{self.config.json_api_url}/v1/parties"
                parties_response = await self._make_request("GET", parties_url)
                parties = []
                if isinstance(parties_response, dict):
                    if "result" in parties_response:
                        parties = parties_response["result"]
                    elif "errors" not in parties_response:
                        parties = [parties_response]
                elif isinstance(parties_response, list):
                    parties = parties_response
                for party in parties:
                    if isinstance(party, dict):
                        party_id = party.get("identifier", "")
                        if party_hint in party_id or party.get("displayName") == "P2Engine Default Party":
                            self._actual_party_id = party_id
                            self._update_token_with_party(party_id)
                            logger.info(f"Using existing party: {party_id}")
                            return party_id
                party_payload = {"identifierHint": party_hint, "displayName": "P2Engine Default Party"}
                response = await self._make_request("POST", f"{self.config.json_api_url}/v1/parties/allocate", party_payload)
                allocated_party = None
                if isinstance(response, dict):
                    if "result" in response:
                        allocated_party = response["result"].get("identifier")
                    else:
                        allocated_party = response.get("identifier")
                if allocated_party:
                    self._actual_party_id = allocated_party
                    self._update_token_with_party(allocated_party)
                    logger.info(f"Party allocated: {allocated_party}")
                    return allocated_party
            except Exception as exc:
                error_str = str(exc)
                if "PARTY_ALLOCATION_WITHOUT_CONNECTED_DOMAIN" in error_str:
                    if attempt < self.config.max_retries - 1:
                        logger.warning(
                            f"Domain not yet connected, waiting {self.config.retry_delay}s "
                            f"before retry {attempt + 2}/{self.config.max_retries}..."
                        )
                        await asyncio.sleep(self.config.retry_delay)
                        continue
                    else:
                        logger.error(
                            "Domain connection not established after all retries. " "Canton may need more time to connect to domain."
                        )
                        break
                elif "INTERNAL" in error_str or "unavailable" in error_str.lower():
                    if attempt < self.config.max_retries - 1:
                        logger.warning(
                            f"Canton appears to be initializing, waiting {self.config.retry_delay}s "
                            f"before retry {attempt + 2}/{self.config.max_retries}..."
                        )
                        await asyncio.sleep(self.config.retry_delay)
                        continue
                    else:
                        logger.error("Canton not ready after all retries")
                else:
                    logger.error(f"Party allocation failed: {exc}")
                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(self.config.retry_delay)
                        continue
                    break
        default_party = f"party-{party_hint}"
        self._actual_party_id = default_party
        self._update_token_with_party(default_party)
        logger.warning(f"Using fallback party ID: {default_party}")
        return default_party

    async def _make_request(self, method: str, url: str, json_data: Optional[Dict] = None, skip_auth: bool = False) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()

        def _sync_request():
            headers = {} if skip_auth else self.headers.copy()
            if method == "GET":
                headers.setdefault("Accept", "application/json")
            try:
                if method == "GET":
                    return requests.get(url, headers=headers, timeout=self.config.connection_timeout)
                elif method == "POST":
                    return requests.post(url, json=json_data, headers=headers, timeout=self.config.connection_timeout)
                else:
                    raise ValueError(f"Unsupported method: {method}")
            except requests.exceptions.ConnectionError as e:
                raise Exception(f"Cannot connect to Canton JSON API at {url}: {e}")

        response = await loop.run_in_executor(None, _sync_request)
        content_type = response.headers.get("content-type", "")
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                if "/packages/" in url and content_type == "application/octet-stream":
                    logger.debug(f"Binary response from {url} - this is expected for package data")
                    return {}
                raise Exception(f"Failed to parse JSON from {url} (content-type was {content_type or 'unknown'})")
        elif response.status_code == 401:
            error_msg = response.json().get("errors", ["Authentication failed"])[0]
            raise Exception(f"Canton API authentication error: {error_msg}")
        elif response.status_code == 404:
            raise Exception(f"Canton API endpoint not found: {url}")
        elif response.status_code >= 400:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            raise Exception(f"Canton API error: {response.status_code} - {error_data}")
        else:
            return response.json()

    def _get_party_id(self) -> str:
        return self._actual_party_id or self.config.party_id

    async def ensure_agent_wallet(self, agent_id: str) -> str:
        await self._ensure_party()
        try:
            wallet = await self._find_wallet(agent_id)
            self._initialized_agents.add(agent_id)
            return wallet.contract_id
        except Exception as e:
            logger.info(f"Wallet not found for {agent_id} ({e}), creating new one")
            return await self.create_agent_wallet(agent_id)

    async def create_agent_wallet(self, agent_id: str, initial_balance: Optional[float] = None) -> str:
        if initial_balance is None:
            initial_balance = self.config.initial_balance
        party_id = await self._ensure_party()
        payload = {
            "templateId": self._get_template_id("P2Engine.Ledger", "AgentWallet"),
            "payload": {"party": party_id, "agent": agent_id, "balance": str(initial_balance), "created": str(int(time.time()))},
        }
        try:
            result = await self._make_request("POST", f"{self.config.json_api_url}/v1/create", payload)
            contract_id = result.get("contractId")
            if not contract_id and "result" in result:
                contract_id = result["result"].get("contractId")
            if not contract_id:
                if isinstance(result, dict):
                    for key in ["result", "exerciseResult", "created", "events"]:
                        if key in result and isinstance(result[key], dict):
                            contract_id = result[key].get("contractId")
                            if contract_id:
                                break
            if not contract_id:
                raise Exception(f"No contract ID in response: {result}")
            self._initialized_agents.add(agent_id)
            await self._publish_ledger_event(
                "wallet_created",
                {"agent_id": agent_id, "contract_id": contract_id, "initial_balance": initial_balance, "timestamp": current_timestamp()},
            )
            logger.info(f"Created wallet for agent {agent_id}: {contract_id}")
            return contract_id
        except Exception as exc:
            if "DUPLICATE_CONTRACT_KEY" in str(exc):
                logger.warning(f"Wallet already exists for {agent_id}, fetching existing wallet")
                wallet = await self._find_wallet(agent_id)
                return wallet.contract_id
            logger.error(f"Failed to create wallet for {agent_id}: {exc}")
            raise

    async def transfer_funds(
        self, from_agent: str, to_agent: str, amount: float, reason: str = "", conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        # Log the transfer attempt
        logger.info(
            f"Transfer initiated: {from_agent} -> {to_agent}, amount: {amount}, " f"reason: {reason}, conversation: {conversation_id}"
        )
        # Ensure wallets exist
        await self.ensure_agent_wallet(from_agent)
        await self.ensure_agent_wallet(to_agent)
        # Get fresh wallet states
        from_wallet = await self._find_wallet(from_agent, use_cache=False)
        to_wallet = await self._find_wallet(to_agent, use_cache=False)
        logger.debug(f"Pre-transfer balances: {from_agent}={from_wallet.balance}, " f"{to_agent}={to_wallet.balance}")
        if from_wallet.balance < amount:
            raise ValueError(f"Insufficient balance: {from_wallet.balance} < {amount}")
        # Exercise the Transfer choice on the from wallet
        exercise_payload = {
            "templateId": self._get_template_id("P2Engine.Ledger", "AgentWallet"),
            "contractId": from_wallet.contract_id,
            "choice": "Transfer",
            "argument": {
                "toWalletId": to_wallet.contract_id,
                "amount": str(amount),
                "reason": reason or f"Transfer from {from_agent} to {to_agent}",
                "timestamp": str(int(time.time())),
            },
        }
        try:
            result = await self._make_request("POST", f"{self.config.json_api_url}/v1/exercise", exercise_payload)
            # Clear cache after transfer since contract IDs change
            self._wallet_cache.pop(from_agent, None)
            self._wallet_cache.pop(to_agent, None)
            # Extract transaction ID from the result
            transaction_id = ""
            exercise_result = result.get("exerciseResult", [])
            if isinstance(exercise_result, list):
                for item in exercise_result:
                    if isinstance(item, dict) and "contractId" in item:
                        template_id = item.get("templateId", "")
                        if "TransferRecord" in template_id:
                            transaction_id = item.get("contractId", "")
                            break
            # Get fresh balances after transfer
            from_wallet_new = await self._find_wallet(from_agent, use_cache=False)
            to_wallet_new = await self._find_wallet(to_agent, use_cache=False)
            # Publish ledger event
            await self._publish_ledger_event(
                "transfer_executed",
                {
                    "from_agent": from_agent,
                    "to_agent": to_agent,
                    "amount": amount,
                    "reason": reason,
                    "transaction_id": transaction_id,
                    "conversation_id": conversation_id,
                    "from_balance": from_wallet_new.balance,
                    "to_balance": to_wallet_new.balance,
                    "timestamp": current_timestamp(),
                },
            )
            # Optional: nudge realtime stream tied to a rollout conversation
            try:
                if conversation_id:
                    r = get_bus().redis
                    rollout_id = r.get(f"{conversation_id}:rollout_id")
                    if rollout_id:
                        team_b = r.get(f"{conversation_id}:team")
                        var_b = r.get(f"{conversation_id}:variant")
                        r.xadd(
                            "stream:stack_updates",
                            {
                                "type": "ledger_transfer",
                                "conversation_id": conversation_id,
                                "team_id": (team_b.decode() if isinstance(team_b, bytes) else team_b) or "",
                                "variant_id": (var_b.decode() if isinstance(var_b, bytes) else var_b) or "",
                                "rollout_id": rollout_id.decode() if isinstance(rollout_id, bytes) else rollout_id,
                                "from_agent": from_agent,
                                "to_agent": to_agent,
                                "amount": amount,
                                "from_balance": from_wallet_new.balance,
                                "to_balance": to_wallet_new.balance,
                                "timestamp": time.time(),
                            },
                            maxlen=10000,
                            approximate=True,
                        )
            except Exception:
                pass

            metrics.emit("ledger_transfer", amount, tags={"from_agent": from_agent, "to_agent": to_agent})
            logger.info(f"Transfer successful: {from_agent} -> {to_agent}: {amount}")
            return {
                "success": True,
                "transaction_id": transaction_id,
                "from_balance": from_wallet_new.balance,
                "to_balance": to_wallet_new.balance,
            }
        except Exception as exc:
            logger.error(f"Transfer failed: {exc}")
            raise Exception(f"Canton API issue. Ensure Canton and JSON API are running. Error: {exc}")

    async def get_agent_balance(self, agent_id: str, use_cache: bool = True) -> float:
        wallet = await self._find_wallet(agent_id, use_cache=use_cache)
        return wallet.balance

    async def get_transaction_history(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        # Ensure agent has a wallet
        try:
            await self.ensure_agent_wallet(agent_id)
        except Exception:
            return []
        query = {"templateIds": [self._get_template_id("P2Engine.Ledger", "TransferRecord")]}
        try:
            result = await self._make_request("POST", f"{self.config.json_api_url}/v1/query", query)
            all_transactions = result.get("result", [])
            # Filter transactions for this agent
            transactions = []
            for tx in all_transactions:
                payload = tx.get("payload", {})
                if payload.get("fromAgent") == agent_id or payload.get("toAgent") == agent_id:
                    transactions.append(tx)

            # Sort by timestamp (newest first)
            def get_timestamp(tx):
                try:
                    return int(tx.get("payload", {}).get("timestamp", 0))
                except (ValueError, TypeError):
                    return 0

            transactions.sort(key=get_timestamp, reverse=True)
            return transactions[:limit]
        except Exception as exc:
            logger.error(f"Failed to get transaction history: {exc}")
            return []

    async def get_system_metrics(self) -> Dict[str, Any]:
        try:
            # Ensure party exists first
            await self._ensure_party()
            # Query all wallets
            wallet_query = {"templateIds": [self._get_template_id("P2Engine.Ledger", "AgentWallet")]}
            wallets_result = await self._make_request("POST", f"{self.config.json_api_url}/v1/query", wallet_query)
            wallets = wallets_result.get("result", [])
            # Query all transfers
            transfer_query = {"templateIds": [self._get_template_id("P2Engine.Ledger", "TransferRecord")]}
            transfers_result = await self._make_request("POST", f"{self.config.json_api_url}/v1/query", transfer_query)
            transfers = transfers_result.get("result", [])
            # Calculate metrics
            total_balance = sum(float(w.get("payload", {}).get("balance", 0)) for w in wallets)
            total_volume = sum(float(t.get("payload", {}).get("amount", 0)) for t in transfers)
            metrics = {
                "wallet_count": len(wallets),
                "total_balance": total_balance,
                "transaction_count": len(transfers),
                "total_volume": total_volume,
                "average_balance": total_balance / len(wallets) if wallets else 0,
            }
            logger.info(f"System metrics: {metrics}")
            return metrics
        except Exception as exc:
            logger.error(f"Failed to get system metrics: {exc}")
            return {
                "wallet_count": 0,
                "total_balance": 0,
                "transaction_count": 0,
                "total_volume": 0,
                "average_balance": 0,
            }

    async def _find_wallet(self, agent_id: str, use_cache: bool = True) -> WalletInfo:
        # Check cache first if allowed
        if use_cache and agent_id in self._wallet_cache:
            cached = self._wallet_cache[agent_id]
            if time.time() - cached.last_updated < self.config.cache_ttl:
                return cached
        # Query for the wallet
        query = {"templateIds": [self._get_template_id("P2Engine.Ledger", "AgentWallet")], "query": {"agent": agent_id}}
        try:
            result = await self._make_request("POST", f"{self.config.json_api_url}/v1/query", query)
            contracts = result.get("result", [])
            # Find the wallet for this specific agent
            wallet_contract = None
            for contract in contracts:
                payload = contract.get("payload", {})
                if payload.get("agent") == agent_id:
                    wallet_contract = contract
                    break
            if not wallet_contract:
                raise ValueError(f"No wallet found for agent {agent_id}")
            payload = wallet_contract["payload"]
            wallet_info = WalletInfo(
                contract_id=wallet_contract["contractId"], agent_id=agent_id, balance=float(payload["balance"]), last_updated=time.time()
            )
            # Only cache if requested
            if use_cache:
                self._wallet_cache[agent_id] = wallet_info
            return wallet_info
        except Exception as exc:
            logger.error(f"Failed to find wallet for {agent_id}: {exc}")
            raise

    async def _publish_ledger_event(self, event_type: str, data: Dict[str, Any]):
        try:
            bus = get_bus()
            party_id = self._get_party_id()
            # Use a consistent session ID format
            session_id = f"ledger:{party_id.replace('::', '_')}"
            header: ArtifactHeader = {
                "ref": generate_ref(),
                "session_id": session_id,
                "agent_id": "ledger_service",
                "branch_id": "main",
                "episode_id": "",
                "type": "ledger_event",
                "role": "ledger_event",
                "mime": "application/json",
                "ts": current_timestamp(),
                "meta": {"event_type": event_type, "party_id": party_id, "tags": ["ledger", event_type]},
            }
            bus.publish(header, data)
            logger.info(f"Published ledger event {event_type} to session {session_id}")
        except Exception as exc:
            logger.error(f"Failed to publish ledger artifact: {exc}")


async def get_ledger_service() -> CantonLedgerService:
    config = LedgerConfig()
    ledger_settings = settings().ledger
    if ledger_settings:
        config.json_api_url = ledger_settings.json_api_url
        config.party_id = ledger_settings.party_id
        config.initial_balance = ledger_settings.initial_balance
        config.cache_ttl = ledger_settings.cache_ttl
    config.package_id = os.getenv("DAML_PACKAGE_ID")
    return await CantonLedgerService.get_instance(config)
