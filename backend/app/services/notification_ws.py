"""
Registre de connexions WebSocket pour la diffusion temps réel des
notifications. Un utilisateur peut avoir plusieurs onglets/connexions
ouvertes ; on garde une liste de sockets par `user_id` et on pousse le
message à toutes.

Best-effort : une déconnexion silencieuse ou une erreur d'envoi ne doit
jamais faire planter le flux métier qui a déclenché la notification.
"""
import logging
from collections import defaultdict
from typing import Dict, List
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class NotificationConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[UUID, List[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].append(websocket)

    def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        sockets = self._connections.get(user_id)
        if not sockets:
            return
        if websocket in sockets:
            sockets.remove(websocket)
        if not sockets:
            self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: UUID, payload: dict) -> None:
        """Pousse `payload` à toutes les connexions ouvertes de `user_id`."""
        sockets = list(self._connections.get(user_id, []))
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception as exc:  # pragma: no cover - connexion fermée entre-temps
                logger.debug(f"WS send failed for user {user_id}: {exc}")
                self.disconnect(user_id, ws)

    def is_online(self, user_id: UUID) -> bool:
        return bool(self._connections.get(user_id))


notification_ws_manager = NotificationConnectionManager()
