import asyncio
from threading import Event, Thread

from infra import config_loader as cfg
from infra.async_utils import set_event_loop
from infra.bootstrap import run_once_global_init
from infra.logging.logging_config import logger
from infra.session_driver import session_driver
from services.services import ServiceContainer


class Engine:
    """Process-level orchestrator: boots the async loop, spawns the SessionDriver,
    and wires agents, Redis, Celery, etc.
    """

    def __init__(self, config_path: str = "config/config.json") -> None:
        logger.info("Initializing Engine…")

        self.config = cfg.settings()
        self.container = ServiceContainer()
        self.mode = self.config.mode

        self.loop_ready = Event()
        self.loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self.event_loop_thread = Thread(
            target=self._start_event_loop,
            daemon=True,
            name="AsyncLoop",
        )
        self.event_loop_thread.start()
        if not self.loop_ready.wait(timeout=5):
            raise RuntimeError("Event loop failed to start in time")
        set_event_loop(self.loop)

    
        self._stop_event = Event()  
        self._driver_thread = Thread(
            target=session_driver,
            kwargs={
                "poll_interval": 1,
                "container": self.container,
                "stop_event": self._stop_event, 
            },
            daemon=True,
            name="SessionDriver",
        )

        self._initialize_agents()
        logger.info("Engine initialized successfully")


    def _start_event_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop_ready.set()
        self.loop.run_forever()

    def _initialize_agents(self) -> None:
        for agent_cfg in cfg.agents():
            agent = self.container.get_agent_factory().create(agent_cfg)
            self.container.get_agent_registry().register(agent, agent_cfg)


    def start(self, *, block: bool = True) -> None:
        logger.info("Starting runtime…")
        self._driver_thread.start()
        logger.info("SessionDriver thread started")
        if block:
            self._driver_thread.join()

    def stop(self) -> None:
        logger.info("Stopping runtime…")

        self._stop_event.set()
        if self._driver_thread.is_alive():
            self._driver_thread.join(timeout=5)


        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.event_loop_thread.join(timeout=5)

if __name__ == "__main__":
    run_once_global_init()
    engine = Engine()
    try:
        engine.start(block=True)
    finally:
        engine.stop()
