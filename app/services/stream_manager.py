"""
Stream manager — handles broadcasting processed frames to viewer clients.

WHY in-memory and not Redis/Kafka:
- For a single-server deployment, in-memory asyncio.Queue has ZERO latency
  and ZERO operational overhead.
- If you later need multi-server, swap this for Redis Pub/Sub. The interface
  (add_viewer, remove_viewer, broadcast) stays exactly the same.

PATTERN: Observer/Pub-Sub. The detection loop is the publisher.
Each connected viewer WebSocket is a subscriber with its own queue.
"""

import asyncio
import logging
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class StreamManager:
    """
    Manages a set of viewer queues. Each viewer gets its own asyncio.Queue
    so slow viewers don't block fast ones.
    """

    def __init__(self):
        # dict of viewer_id → asyncio.Queue
        self._viewers: dict[str, asyncio.Queue[bytes]] = {}
        # Latest processed frame (for new viewers joining mid-stream)
        self._latest_frame: Optional[bytes] = None

    @property
    def viewer_count(self) -> int:
        return len(self._viewers)

    def add_viewer(self, viewer_id: str) -> asyncio.Queue[bytes]:
        """
        Register a new viewer and return their personal frame queue.

        WHY per-viewer queue: If one viewer has a slow connection,
        it only fills ITS queue. Other viewers are unaffected.
        """
        if len(self._viewers) >= settings.MAX_VIEWERS:
            raise ConnectionError(
                f"Max viewers ({settings.MAX_VIEWERS}) reached. Try again later."
            )

        queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=5)
        self._viewers[viewer_id] = queue
        logger.info("Viewer %s connected (%d total)", viewer_id, len(self._viewers))

        return queue

    def remove_viewer(self, viewer_id: str) -> None:
        """Unregister a viewer when they disconnect."""
        self._viewers.pop(viewer_id, None)
        logger.info("Viewer %s disconnected (%d remaining)", viewer_id, len(self._viewers))

    async def broadcast(self, frame: bytes) -> None:
        """
        Push a processed frame to all connected viewers.

        WHY put_nowait + queue full handling: We never want to block the
        detection loop waiting for a slow viewer. If a viewer's queue is full,
        we drop the oldest frame (backpressure).
        """
        self._latest_frame = frame

        for viewer_id, queue in list(self._viewers.items()):
            try:
                if queue.full():
                    # Drop oldest frame to make room (backpressure)
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                queue.put_nowait(frame)
            except Exception as e:
                logger.warning("Failed to send frame to viewer %s: %s", viewer_id, e)

    def get_latest_frame(self) -> Optional[bytes]:
        """Return the most recent processed frame (for snapshot endpoint)."""
        return self._latest_frame
