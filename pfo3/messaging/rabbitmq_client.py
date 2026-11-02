"""Cliente de mensajería asíncrona sobre RabbitMQ usando Pika.

Implementa:
- Declaración de colas durables ('task_queue', 'results_queue')
- Publicación de mensajes persistentes (delivery_mode=2)
- Confirmaciones de procesamiento (basic_ack)
- Desacoplamiento total entre servidor TCP y workers
- Soporte para patrón RPC / Correlation ID
"""

import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError
from config.settings import settings

logger = logging.getLogger(__name__)


class RabbitMQClient:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        queue_tasks: Optional[str] = None,
        queue_results: Optional[str] = None
    ):
        self.host = host or settings.RABBITMQ_HOST
        self.port = port or settings.RABBITMQ_PORT
        self.user = user or settings.RABBITMQ_USER
        self.password = password or settings.RABBITMQ_PASSWORD
        self.queue_tasks = queue_tasks or settings.RABBITMQ_QUEUE_TASKS
        self.queue_results = queue_results or settings.RABBITMQ_QUEUE_RESULTS
        self._connection = None
        self._channel = None
        self._lock = threading.Lock()

    def connect(self, retries: int = 5, retry_delay: float = 2.0) -> bool:
        """Establece conexión y canal con RabbitMQ con reintentos."""
        credentials = pika.PlainCredentials(self.user, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=credentials,
            heartbeat=60,
            blocked_connection_timeout=300
        )
        
        for attempt in range(1, retries + 1):
            try:
                self._connection = pika.BlockingConnection(parameters)
                self._channel = self._connection.channel()
                
                # Declarar colas durables
                self._channel.queue_declare(queue=self.queue_tasks, durable=True)
                self._channel.queue_declare(queue=self.queue_results, durable=True)
                
                logger.info(f"Conexión exitosa a RabbitMQ ({self.host}:{self.port}) en intento {attempt}.")
                return True
            except AMQPConnectionError as e:
                logger.warning(f"Intento {attempt}/{retries} falló al conectar a RabbitMQ: {e}")
                if attempt < retries:
                    time.sleep(retry_delay)
                else:
                    logger.error("No se pudo conectar a RabbitMQ tras todos los intentos.")
                    return False

    def is_connected(self) -> bool:
        return self._connection is not None and self._connection.is_open

    def publish_task(
        self,
        task_data: Dict[str, Any],
        correlation_id: str,
        reply_to: Optional[str] = None
    ) -> bool:
        """Publica una tarea en la cola durable de tareas."""
        if not self.is_connected():
            if not self.connect():
                raise ConnectionError("No hay conexión activa con RabbitMQ para publicar la tarea.")
                
        body = json.dumps(task_data, ensure_ascii=False).encode("utf-8")
        properties = pika.BasicProperties(
            delivery_mode=2,  # Mensaje persistente en disco
            correlation_id=correlation_id,
            reply_to=reply_to or self.queue_results,
            content_type="application/json"
        )
        
        self._channel.basic_publish(
            exchange="",
            routing_key=self.queue_tasks,
            body=body,
            properties=properties
        )
        logger.debug(f"Tarea publicada en RabbitMQ: correlation_id={correlation_id}")
        return True

    def publish_result(
        self,
        result_data: Dict[str, Any],
        correlation_id: str,
        routing_key: Optional[str] = None
    ) -> bool:
        """Publica el resultado de una tarea en la cola de resultados."""
        if not self.is_connected():
            if not self.connect():
                raise ConnectionError("No hay conexión activa con RabbitMQ para publicar el resultado.")
                
        body = json.dumps(result_data, ensure_ascii=False).encode("utf-8")
        properties = pika.BasicProperties(
            delivery_mode=2,
            correlation_id=correlation_id,
            content_type="application/json"
        )
        
        target_queue = routing_key or self.queue_results
        self._channel.basic_publish(
            exchange="",
            routing_key=target_queue,
            body=body,
            properties=properties
        )
        logger.debug(f"Resultado publicado en RabbitMQ: correlation_id={correlation_id} en {target_queue}")
        return True

    def start_consuming_tasks(
        self,
        callback: Callable[[Dict[str, Any], str, str, Callable[[], None]], None],
        prefetch_count: int = 1
    ) -> None:
        """Inicia consumo bloqueante de tareas desde 'task_queue'.
        
        El callback recibe: (mensaje_dict, correlation_id, reply_to, ack_func).
        """
        if not self.is_connected():
            if not self.connect():
                raise ConnectionError("No se pudo conectar a RabbitMQ para iniciar el consumo de tareas.")

        self._channel.basic_qos(prefetch_count=prefetch_count)

        def on_message(ch, method, props, body):
            try:
                msg = json.loads(body.decode("utf-8"))
                corr_id = props.correlation_id or ""
                reply_to = props.reply_to or self.queue_results
                
                def ack():
                    try:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as err:
                        logger.error(f"Error al enviar basic_ack: {err}")

                def nack(requeue: bool = True):
                    try:
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=requeue)
                    except Exception as err:
                        logger.error(f"Error al enviar basic_nack: {err}")

                def publish_result_threadsafe(res_body: bytes, routing_k: str, correlation: str):
                    try:
                        res_props = pika.BasicProperties(
                            delivery_mode=2,
                            correlation_id=correlation,
                            content_type="application/json"
                        )
                        ch.basic_publish(
                            exchange="",
                            routing_key=routing_k,
                            body=res_body,
                            properties=res_props
                        )
                        logger.debug(f"Resultado publicado thread-safe en {routing_k} (corr_id={correlation})")
                    except Exception as err:
                        logger.error(f"Error al publicar resultado thread-safe: {err}")
                        raise

                callback(msg, corr_id, reply_to, ack, nack, publish_result_threadsafe)
            except Exception as e:
                logger.error(f"Error al procesar mensaje de RabbitMQ: {e}")
                # En caso de error irrecuperable en deserialización, se rechaza sin reencolar
                try:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                except Exception:
                    pass

        self._channel.basic_consume(
            queue=self.queue_tasks,
            on_message_callback=on_message,
            auto_ack=False
        )
        logger.info(f"Iniciando consumo de tareas en cola '{self.queue_tasks}'...")
        self._channel.start_consuming()

    def start_consuming_results(
        self,
        callback: Callable[[Dict[str, Any], str], None]
    ) -> None:
        """Inicia consumo de resultados en un hilo de escucha para correlación."""
        if not self.is_connected():
            if not self.connect():
                raise ConnectionError("No se pudo conectar a RabbitMQ para consumir resultados.")

        def on_result(ch, method, props, body):
            try:
                result_dict = json.loads(body.decode("utf-8"))
                corr_id = props.correlation_id or result_dict.get("request_id", "")
                callback(result_dict, corr_id)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error al procesar resultado de RabbitMQ: {e}")
                ch.basic_ack(delivery_tag=method.delivery_tag)

        self._channel.basic_consume(
            queue=self.queue_results,
            on_message_callback=on_result,
            auto_ack=False
        )
        logger.info(f"Iniciando consumo de resultados en cola '{self.queue_results}'...")
        self._channel.start_consuming()

    def close(self) -> None:
        """Cierra el canal y la conexión de forma segura."""
        try:
            if self._channel and self._channel.is_open:
                self._channel.close()
            if self._connection and self._connection.is_open:
                self._connection.close()
        except Exception as e:
            logger.debug(f"Excepción controlada al cerrar RabbitMQ: {e}")
