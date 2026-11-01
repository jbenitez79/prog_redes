"""Implementación de Worker distribuido concurrente con Pool de Hilos.

Consume tareas desde RabbitMQ, ejecuta operaciones registradas en un pool de hilos,
actualiza el estado en PostgreSQL, persiste artefactos en S3 y publica el resultado.
"""

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

from config.settings import settings
from messaging.rabbitmq_client import RabbitMQClient
from storage.postgres import PostgresStorage
from storage.s3_storage import S3Storage
from server.protocol import build_task_result_response, build_error_response
from workers.operations import execute_operation, OperationError

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] [%(threadName)s] %(message)s"
)
logger = logging.getLogger("Worker")


class DistributedWorker:
    def __init__(
        self,
        worker_id: Optional[str] = None,
        threads: Optional[int] = None,
        rabbitmq_client: Optional[RabbitMQClient] = None,
        postgres_storage: Optional[PostgresStorage] = None,
        s3_storage: Optional[S3Storage] = None
    ):
        self.worker_id = worker_id or settings.WORKER_ID
        self.threads = threads or settings.WORKER_THREADS
        self.rmq = rabbitmq_client or RabbitMQClient()
        self.storage = postgres_storage or PostgresStorage()
        self.s3 = s3_storage or S3Storage()
        self.thread_pool = ThreadPoolExecutor(max_workers=self.threads, thread_name_prefix=f"{self.worker_id}-thread")
        self._publisher = RabbitMQClient(
            host=self.rmq.host,
            port=self.rmq.port,
            user=self.rmq.user,
            password=self.rmq.password,
            queue_tasks=self.rmq.queue_tasks,
            queue_results=self.rmq.queue_results
        )
        self._running = False

    def _process_task_job(
        self,
        msg: Dict[str, Any],
        correlation_id: str,
        reply_to: str,
        ack_func: Callable[[], None]
    ) -> None:
        """Trabajo ejecutado dentro del ThreadPoolExecutor del Worker."""
        request_id = msg.get("request_id", correlation_id)
        task_id = msg.get("task_id", "unknown")
        operation = msg.get("operation", "unknown")
        payload = msg.get("payload", {})

        logger.info(f"[{self.worker_id}] Iniciando tarea {task_id} (operación='{operation}', request_id={request_id})")

        # 1. Actualizar estado a 'processing'
        try:
            self.storage.set_task_processing(task_id, self.worker_id)
        except Exception as e:
            logger.warning(f"No se pudo actualizar estado a 'processing' en PostgreSQL: {e}")

        # 2. Ejecutar la operación
        try:
            result = execute_operation(operation, payload)
            logger.info(f"[{self.worker_id}] Tarea {task_id} completada exitosamente. Resultado={result}")

            # 3. Guardar artefacto en S3 (opcional / configurable)
            s3_url = None
            if self.s3.enabled:
                artifact_data = {
                    "task_id": task_id,
                    "request_id": request_id,
                    "operation": operation,
                    "payload": payload,
                    "result": result,
                    "worker_id": self.worker_id
                }
                s3_url = self.s3.save_artifact(task_id, artifact_data)

            # 4. Actualizar estado a 'completed' en PostgreSQL
            try:
                self.storage.set_task_completed(task_id, self.worker_id, result, s3_url)
            except Exception as e:
                logger.warning(f"No se pudo guardar resultado en PostgreSQL: {e}")

            # 5. Armar respuesta según protocolo
            response_msg = build_task_result_response(
                request_id=request_id,
                task_id=task_id,
                result=result,
                worker_id=self.worker_id
            )

        except OperationError as oe:
            logger.error(f"[{self.worker_id}] Error de validación/operación en tarea {task_id}: {oe}")
            try:
                self.storage.set_task_failed(task_id, self.worker_id, str(oe))
            except Exception:
                pass
            response_msg = build_error_response(
                request_id=request_id,
                code="INVALID_OPERATION_PAYLOAD",
                message=str(oe),
                task_id=task_id
            )
        except Exception as ex:
            logger.exception(f"[{self.worker_id}] Error no controlado en tarea {task_id}: {ex}")
            try:
                self.storage.set_task_failed(task_id, self.worker_id, f"Error de ejecución: {ex}")
            except Exception:
                pass
            response_msg = build_error_response(
                request_id=request_id,
                code="EXECUTION_ERROR",
                message=f"Error interno durante la ejecución: {ex}",
                task_id=task_id
            )

        # 6. Publicar resultado en RabbitMQ
        try:
            self._publisher.publish_result(
                result_data=response_msg,
                correlation_id=correlation_id,
                routing_key=reply_to
            )
        except Exception as e:
            logger.error(f"[{self.worker_id}] Error al publicar resultado a RabbitMQ: {e}")

        # 7. Confirmar mensaje (ack)
        ack_func()
        logger.info(f"[{self.worker_id}] Mensaje de tarea {task_id} confirmado (ack).")

    def _task_consumer_callback(
        self,
        msg: Dict[str, Any],
        correlation_id: str,
        reply_to: str,
        ack_func: Callable[[], None]
    ) -> None:
        """Callback invocado por RabbitMQ al llegar un mensaje a la cola."""
        logger.debug(f"[{self.worker_id}] Despachando tarea recibida al pool de hilos ({self.threads} hilos).")
        
        def safe_ack():
            try:
                if self.rmq._connection and self.rmq._connection.is_open:
                    self.rmq._connection.add_callback_threadsafe(ack_func)
                else:
                    ack_func()
            except Exception as e:
                logger.error(f"Error en safe_ack: {e}")

        self.thread_pool.submit(self._process_task_job, msg, correlation_id, reply_to, safe_ack)

    def start(self) -> None:
        """Inicia el ciclo principal de escucha y consumo de tareas."""
        self._running = True
        logger.info(f"Iniciando Worker ID '{self.worker_id}' con {self.threads} hilos de ejecución...")
        
        # Verificar bucket S3
        if self.s3.enabled:
            self.s3.ensure_bucket_exists()

        while self._running:
            try:
                self.rmq.start_consuming_tasks(
                    callback=self._task_consumer_callback,
                    prefetch_count=self.threads
                )
            except AMQPConnectionError as ce:
                logger.warning(f"Conexión con RabbitMQ perdida. Reintentando en 3s... ({ce})")
                import time
                time.sleep(3.0)
            except KeyboardInterrupt:
                logger.info("Detención solicitada por el usuario (KeyboardInterrupt).")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error inesperado en el ciclo del worker: {e}")
                import time
                time.sleep(3.0)

    def stop(self) -> None:
        """Detiene el worker y libera hilos y conexiones."""
        self._running = False
        logger.info(f"Deteniendo Worker '{self.worker_id}'...")
        self.thread_pool.shutdown(wait=True)
        self.rmq.close()


def main():
    parser = argparse.ArgumentParser(description="Worker Distribuido PFO 3")
    parser.add_argument("--worker-id", type=str, default=None, help="Identificador único del worker")
    parser.add_argument("--threads", type=int, default=None, help="Cantidad de hilos en el pool")
    args = parser.parse_args()

    worker = DistributedWorker(worker_id=args.worker_id, threads=args.threads)
    try:
        worker.start()
    except KeyboardInterrupt:
        worker.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
