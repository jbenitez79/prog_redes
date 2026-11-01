"""Gestor de correlación de tareas en memoria para el servidor TCP.

Sincroniza la recepción asíncrona de resultados desde RabbitMQ con los hilos
que atienden a los sockets TCP de los clientes.
"""

import threading
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._pending_events: Dict[str, threading.Event] = {}
        self._results: Dict[str, Dict[str, Any]] = {}

    def register_request(self, request_id: str) -> None:
        """Registra una solicitud y crea un evento de sincronización."""
        with self._lock:
            self._pending_events[request_id] = threading.Event()
            self._results.pop(request_id, None)

    def set_result(self, request_id: str, result_data: Dict[str, Any]) -> bool:
        """Almacena el resultado recibido y despierta al hilo en espera."""
        with self._lock:
            event = self._pending_events.get(request_id)
            if event:
                self._results[request_id] = result_data
                event.set()
                logger.debug(f"Resultado correlacionado y entregado para request_id={request_id}")
                return True
            else:
                logger.warning(f"Se recibió resultado para request_id desconocido o expirado: {request_id}")
                return False

    def wait_for_result(self, request_id: str, timeout: float = 30.0) -> Dict[str, Any]:
        """Bloquea el hilo del cliente hasta recibir el resultado o agotar el tiempo."""
        with self._lock:
            event = self._pending_events.get(request_id)
            if not event:
                raise ValueError(f"La solicitud {request_id} no está registrada.")

        signaled = event.wait(timeout=timeout)
        with self._lock:
            self._pending_events.pop(request_id, None)
            if not signaled:
                self._results.pop(request_id, None)
                raise TimeoutError(f"Tiempo de espera agotado ({timeout}s) para la tarea.")
            return self._results.pop(request_id, {})

    def cancel_request(self, request_id: str) -> None:
        """Limpia los recursos de una solicitud cancelada."""
        with self._lock:
            self._pending_events.pop(request_id, None)
            self._results.pop(request_id, None)
