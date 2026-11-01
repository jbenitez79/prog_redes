"""Distribuidor de tareas: desacopla al cliente TCP del procesamiento.

Valida operaciones registradas, persiste el estado 'pending' en PostgreSQL,
publica la tarea en RabbitMQ y coordina la respuesta mediante correlation_id.
"""

import logging
import threading
from typing import Any, Dict, Optional
from config.settings import settings
from messaging.rabbitmq_client import RabbitMQClient
from storage.postgres import PostgresStorage
from workers.operations import get_available_operations
from server.protocol import ProtocolError, build_error_response
from server.task_manager import TaskManager

logger = logging.getLogger(__name__)


class TaskDispatcher:
    def __init__(
        self,
        rabbitmq_client: Optional[RabbitMQClient] = None,
        postgres_storage: Optional[PostgresStorage] = None,
        task_manager: Optional[TaskManager] = None
    ):
        self.rmq = rabbitmq_client or RabbitMQClient()
        self.storage = postgres_storage or PostgresStorage()
        self.manager = task_manager or TaskManager()
        self._results_listener_thread = None
        self._running = False

    def start_results_listener(self) -> None:
        """Inicia el hilo de fondo para escuchar respuestas en results_queue de RabbitMQ."""
        if self._running:
            return
        self._running = True

        def _listen():
            # Crear un cliente dedicado para el consumidor de respuestas
            listener_rmq = RabbitMQClient(
                host=self.rmq.host,
                port=self.rmq.port,
                user=self.rmq.user,
                password=self.rmq.password,
                queue_results=self.rmq.queue_results
            )
            while self._running:
                try:
                    logger.info("Iniciando escucha de resultados en RabbitMQ...")
                    listener_rmq.start_consuming_results(
                        callback=lambda result_data, corr_id: self.manager.set_result(corr_id, result_data)
                    )
                except Exception as e:
                    if not self._running:
                        break
                    logger.warning(f"Reintentando conexión del listener de resultados en 3s: {e}")
                    import time
                    time.sleep(3.0)

        self._results_listener_thread = threading.Thread(target=_listen, daemon=True, name="RMQ-Results-Listener")
        self._results_listener_thread.start()

    def dispatch_task(self, request_msg: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """Procesa una solicitud 'submit_task' completa."""
        request_id = request_msg["request_id"]
        task = request_msg["task"]
        task_id = task["task_id"]
        operation = task["operation"]
        payload = task["payload"]

        # Validar si la operación está en el registro permitido
        available_ops = get_available_operations()
        if operation not in available_ops:
            logger.warning(f"Operación rechazada: '{operation}' no está registrada.")
            raise ProtocolError(
                code="INVALID_TASK",
                message=f"La operación solicitada '{operation}' no es válida. Permitidas: {', '.join(available_ops)}",
                request_id=request_id
            )

        # 1. Registrar estado inicial en PostgreSQL
        try:
            self.storage.create_task(
                task_id=task_id,
                request_id=request_id,
                operation=operation,
                payload=payload
            )
            logger.info(f"Tarea {task_id} registrada en PostgreSQL con estado 'pending'.")
        except Exception as e:
            logger.warning(f"Aviso de persistencia al crear tarea {task_id} en PostgreSQL: {e}")

        # 2. Registrar en el gestor de correlación
        self.manager.register_request(request_id)

        # 3. Publicar en RabbitMQ
        task_envelope = {
            "request_id": request_id,
            "task_id": task_id,
            "operation": operation,
            "payload": payload
        }
        try:
            self.rmq.publish_task(
                task_data=task_envelope,
                correlation_id=request_id,
                reply_to=self.rmq.queue_results
            )
            logger.info(f"Tarea {task_id} despachada a RabbitMQ con correlation_id={request_id}")
        except Exception as e:
            self.manager.cancel_request(request_id)
            logger.error(f"Error al publicar tarea en RabbitMQ: {e}")
            raise ProtocolError(
                code="MESSAGING_ERROR",
                message=f"No se pudo encolar la tarea en el broker de mensajería: {e}",
                request_id=request_id
            )

        # 4. Esperar el resultado desde la cola de resultados
        try:
            result_data = self.manager.wait_for_result(request_id=request_id, timeout=timeout)
            return result_data
        except TimeoutError:
            logger.error(f"Timeout esperando respuesta de tarea {task_id} (request_id={request_id})")
            try:
                self.storage.set_task_failed(task_id, "unknown", "Tiempo de espera agotado.")
            except Exception:
                pass
            return build_error_response(
                request_id=request_id,
                code="TIMEOUT",
                message=f"Se agotó el tiempo máximo de espera ({timeout}s) para la tarea.",
                task_id=task_id
            )

    def stop(self) -> None:
        self._running = False
        self.rmq.close()
