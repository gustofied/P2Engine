"""Real-time monitoring for conversation stacks during rollouts."""

import json
import os
import time
import threading
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from queue import Queue
import redis

from cli.handlers.conversation import stack_view
from infra.observability import rerun_rollout as rr_viz
from infra.logging.logging_config import logger


@dataclass
class StackUpdate:
    """Represents a stack update event."""
    conversation_id: str
    team_id: str
    variant_id: str
    stack_length: int
    timestamp: float


class RealtimeStackMonitor:
    """Monitors conversation stacks in real-time and streams to Rerun."""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        container,
        rollout_id: str,
        refresh_rate: float = 0.5,
        step_sec: float = 0.15,
    ):
        self.redis = redis_client
        self.container = container
        self.rollout_id = rollout_id
        self.refresh_rate = refresh_rate
        self.step_sec = step_sec
        
        # Track conversations and their state
        self.conversations: Dict[str, Tuple[str, str]] = {}  # conv_id -> (team, variant)
        self.last_positions: Dict[str, int] = {}  # conv_id -> last_stack_index
        self.last_line_idx: Dict[Tuple[str, str], int] = {}  # (team, variant) -> last_line_idx

        # Track last normalized state kind per conversation for clean transitions
        self.last_kind_by_conv: Dict[str, str] = {}  # conv_id -> last_kind
        
        # Markov graph state
        self.markov = None  # Will be initialized with MarkovAgg
        self.t_anim = 0.0

        # --- world_sessions graph toggle (OFF by default) --------------------
        self.enable_world_sessions = os.getenv("OBS_WORLD_SESSIONS", "0") == "1"
        # World sessions graph state ("variant → session → agent")
        self.world = rr_viz.WorldState() if self.enable_world_sessions else None
        self.frame_idx: int = 0  # one frame per interaction
        # --------------------------------------------------------------------

        # Mini state-flow ring
        self.pulse = rr_viz.StatePulse()
        
        # Team documentation
        self.team_docs: Dict[str, List[str]] = {}
        
        # Threading
        self.monitoring = threading.Event()
        self.update_queue = Queue()
        self.monitor_thread = None
        self.processor_thread = None
        
    def start(self):
        """Start monitoring in background thread."""
        self.monitoring.set()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Also start update processor
        self.processor_thread = threading.Thread(target=self._process_updates, daemon=True)
        self.processor_thread.start()
        
    def stop(self):
        """Stop monitoring."""
        self.monitoring.clear()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        if self.processor_thread:
            self.processor_thread.join(timeout=2)
            
    def register_conversation(self, conv_id: str, team_id: str, variant_id: str):
        """Register a conversation for monitoring."""
        self.conversations[conv_id] = (team_id, variant_id)
        self.team_docs.setdefault(team_id, [f"# {team_id}\n"])
        # Seed world state minimally (only if enabled)
        if self.enable_world_sessions:
            rr_viz.world_apply_update(
                self.world,
                conversation_id=conv_id,
                team_id=team_id,
                variant_id=variant_id,
                agent_id=None,
                event_type=None,
                frame=self.frame_idx,
            )
            rr_viz.log_world_sessions(self.rollout_id, self.world, frame=self.frame_idx)
        
    def _monitor_loop(self):
        """Main monitoring loop - runs in background thread."""
        last_stream_id = "0-0"
        
        while self.monitoring.is_set():
            try:
                # 1. Check for stack update events from workers
                resp = self.redis.xread(
                    {"stream:stack_updates": last_stream_id},
                    block=int(self.refresh_rate * 500),  # 500ms blocking
                    count=100
                )
                
                for stream_name, messages in resp:
                    for msg_id, fields in messages:
                        last_stream_id = msg_id
                        
                        # Parse the update event
                        update = self._parse_update(fields)
                        if update and update.get("rollout_id") == self.rollout_id:
                            conv_id = update["conversation_id"]
                            
                            # Auto-register if needed
                            if conv_id not in self.conversations:
                                team = update.get("team_id", "?")
                                variant = update.get("variant_id", "?")
                                self.register_conversation(conv_id, team, variant)
                            
                            # Queue for processing
                            self.update_queue.put(("event", update))
                
                # 2. Also poll all known conversations directly
                for conv_id, (team, variant) in list(self.conversations.items()):
                    try:
                        lines = stack_view(self.container, conv_id, n=100)
                        if lines:
                            last_pos = self.last_positions.get(conv_id, -1)
                            if lines[-1].idx <= last_pos:
                                continue  # No new content
                                
                            new_lines = [ln for ln in lines if ln.idx > last_pos]
                            if new_lines:
                                self.update_queue.put(("poll", {
                                    "conversation_id": conv_id,
                                    "team_id": team,
                                    "variant_id": variant,
                                    "lines": lines,
                                    "new_lines": new_lines
                                }))
                                self.last_positions[conv_id] = lines[-1].idx
                    except Exception:
                        pass
                        
                time.sleep(0.1)  # Small delay between poll cycles
                        
            except Exception as e:
                if self.monitoring.is_set():
                    logger.debug(f"Monitor loop error: {e}")
                    time.sleep(0.5)
                    
    def _process_updates(self):
        """Process updates and emit to Rerun."""
        while self.monitoring.is_set() or not self.update_queue.empty():
            try:
                source, data = self.update_queue.get(timeout=0.5)
                
                if source == "poll":
                    self._process_poll_update(data)
                elif source == "event":
                    self._process_event_update(data)
                    
            except:
                pass
                
    def _process_poll_update(self, data: Dict[str, Any]):
        """Process a polling update with full stack data."""
        team = data["team_id"]
        variant = data["variant_id"]
        lines = data["lines"]
        new_lines = data["new_lines"]
        conv_id = data.get("conversation_id", "")

        # Determine the kind immediately preceding the first new line (for clean transitions)
        prev_kind: Optional[str] = self.last_kind_by_conv.get(conv_id)
        if lines and new_lines and prev_kind is None:
            try:
                first_new = new_lines[0]
                idx_in_full = lines.index(first_new)
                if idx_in_full > 0:
                    prev_kind = getattr(lines[idx_in_full - 1], "kind", None)
            except Exception:
                prev_kind = None
        
        # Stream new lines to Rerun AND advance one world frame per line
        for ln in new_lines:
            cur_kind = getattr(ln, "kind", "")
            rr_viz.log_stack_line(
                self.rollout_id,
                team,
                variant,
                idx=int(ln.idx),
                kind=cur_kind,
                content=getattr(ln, "content", ""),
                t_step=self.t_anim,
            )
            self.t_anim += self.step_sec * 0.5

            # Mini state-flow ring: feed transition and render one frame per interaction
            try:
                self.pulse.add(prev_kind, cur_kind)
            except Exception:
                pass
            rr_viz.log_state_pulse(self.rollout_id, self.pulse, frame=self.frame_idx)

            # Advance world timeline iff enabled
            if self.enable_world_sessions:
                rr_viz.world_tick(self.world, self.frame_idx)
                rr_viz.log_world_sessions(self.rollout_id, self.world, frame=self.frame_idx)

            self.frame_idx += 1

            # Chain transitions and remember last kind for this conversation
            prev_kind = cur_kind
            if conv_id:
                self.last_kind_by_conv[conv_id] = cur_kind
            
        # Update Markov graph if we have one
        if self.markov and new_lines:
            self.markov.add_lines(new_lines)
            positions, meta, edges = self.markov.to_graph()
            
            if positions:
                rr_viz.log_graph_static(self.rollout_id, positions, meta, edges)
                
                # Animate transitions
                events = []
                for a, b in zip(new_lines[:-1], new_lines[1:]):
                    ka = getattr(a, "kind", "")
                    kb = getattr(b, "kind", "")
                    pos_map = {m["variant"]: positions[i] for i, m in enumerate(meta)}
                    if ka in pos_map and kb in pos_map:
                        events.append({
                            "t": self.t_anim,
                            "variant": variant,
                            "p1": list(pos_map[ka]),
                            "p2": list(pos_map[kb])
                        })
                        self.t_anim += self.step_sec
                        
                if events:
                    rr_viz.log_graph_events(self.rollout_id, events, timeline="step")
                    
        # Update team documentation
        self._update_team_docs(team)
        
    def _process_event_update(self, data: Dict[str, Any]):
        """Process an event update from workers."""
        conv_id = data.get("conversation_id")
        if not conv_id:
            return

        # Determine team/variant now
        team = None
        variant = None
        if conv_id in self.conversations:
            team, variant = self.conversations[conv_id]
        else:
            team = data.get("team_id") or "?"
            variant = data.get("variant_id") or "?"

        # Update world graph state immediately when events arrive (only if enabled)
        if self.enable_world_sessions:
            rr_viz.world_apply_update(
                self.world,
                conversation_id=conv_id,
                team_id=team,
                variant_id=variant,
                agent_id=data.get("agent_id"),
                event_type=data.get("type"),
                frame=self.frame_idx,
            )
            rr_viz.log_world_sessions(self.rollout_id, self.world, frame=self.frame_idx)

        # Map live events to flow kinds and update the state-flow ring too
        ev_type = (data.get("type") or "").lower()
        flow_kind_map = {
            "tool_start": "ToolCall",
            "tool_end": "ToolResult",
            "ledger_transfer": "ToolResult",  # ledger ops show as effect/result in flow ring
            "stack_update": None,             # handled by polling path
        }
        flow_kind = flow_kind_map.get(ev_type)
        if flow_kind:
            prev_kind = self.last_kind_by_conv.get(conv_id)
            try:
                self.pulse.add(prev_kind, flow_kind)
            except Exception:
                pass
            rr_viz.log_state_pulse(self.rollout_id, self.pulse, frame=self.frame_idx)
            self.last_kind_by_conv[conv_id] = flow_kind

        self.frame_idx += 1

        # Event updates also trigger a poll for the conversation
        if conv_id in self.conversations:
            self.last_positions[conv_id] = self.last_positions.get(conv_id, -1) - 1
            
    def _update_team_docs(self, team_id: str):
        """Update team documentation in Rerun."""
        docs = [f"# {team_id}\n"]
        
        # Collect all conversations for this team
        for conv_id, (team, variant) in self.conversations.items():
            if team == team_id:
                try:
                    lines = stack_view(self.container, conv_id, n=15)
                    if lines:
                        docs.append(f"\n## {variant}\n")
                        docs.append(self._flow_markdown(team, variant, lines))
                except Exception:
                    pass
                    
        rr_viz.log_team_stack_doc(self.rollout_id, team_id, "".join(docs))
        
    def _flow_markdown(self, team_id: str, variant_id: str, lines) -> str:
        """Format stack lines as markdown."""
        buf = ["```text"]
        for ln in lines or []:
            content = ln.content if len(ln.content) <= 120 else (ln.content[:117] + "…")
            buf.append(f"{ln.idx:>3}  {ln.kind:<12}  {content}")
        buf.append("```")
        return "\n".join(buf)
        
    def _parse_update(self, fields: Dict[bytes, bytes]) -> Optional[Dict[str, Any]]:
        """Parse update event from Redis stream."""
        try:
            result = {}
            for k, v in fields.items():
                key = k.decode() if isinstance(k, bytes) else k
                if isinstance(v, bytes):
                    try:
                        # Try to parse as JSON first
                        if v.startswith(b'{') or v.startswith(b'['):
                            result[key] = json.loads(v)
                        else:
                            result[key] = v.decode()
                    except:
                        result[key] = v.decode()
                else:
                    result[key] = v
            return result
        except Exception:
            return None
            
    def set_markov(self, markov_agg):
        """Set the Markov aggregator instance."""
        self.markov = markov_agg
