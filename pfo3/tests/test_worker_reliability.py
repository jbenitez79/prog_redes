from unittest.mock import MagicMock
import pytest
from workers.worker import DistributedWorker


def test_worker_threadsafe_coordination_and_ack_on_success():
    """Verifica que safe_publish_and_ack coordina la publicación y ack en el hilo de RabbitMQ."""
    mock_storage = MagicMock()
    mock_s3 = MagicMock()
    mock_s3.enabled = False

    mock_conn = MagicMock()
    mock_conn.is_open = True

    mock_rmq = MagicMock()
    mock_rmq._connection = mock_conn

    worker = DistributedWorker(
        worker_id="test-worker-threads",
        threads=2,
        rabbitmq_client=mock_rmq,
        postgres_storage=mock_storage,
        s3_storage=mock_s3
    )

    mock_ack = MagicMock()
    mock_nack = MagicMock()
    mock_publish = MagicMock()

    msg = {
        "request_id": "req-thread-1",
        "task_id": "task-thread-1",
        "operation": "sum",
        "payload": {"numbers": [10, 20]}
    }

    # Invocamos el callback del consumidor
    worker._task_consumer_callback(
        msg=msg,
        correlation_id="req-thread-1",
        reply_to="results_queue",
        ack_func=mock_ack,
        nack_func=mock_nack,
        publish_func=mock_publish
    )

    # Esperar a que el ThreadPoolExecutor procese el trabajo
    worker.thread_pool.shutdown(wait=True)

    # Debe haber llamado a add_callback_threadsafe para coordinar con el hilo del canal
    assert mock_conn.add_callback_threadsafe.called
    scheduled_callbacks = [call_arg[0][0] for call_arg in mock_conn.add_callback_threadsafe.call_args_list]

    # Ejecutamos las acciones programadas (simulando el event loop de Pika)
    for cb in scheduled_callbacks:
        cb()

    # Verificar que se publicó y se hizo ack
    assert mock_publish.called
    assert mock_ack.called
    assert not mock_nack.called


def test_worker_requeues_on_publish_error():
    """Verifica confiabilidad: si falla la publicación del resultado, se reencola (nack) y no se hace ack."""
    mock_storage = MagicMock()
    mock_s3 = MagicMock()
    mock_s3.enabled = False

    mock_conn = MagicMock()
    mock_conn.is_open = True

    mock_rmq = MagicMock()
    mock_rmq._connection = mock_conn

    worker = DistributedWorker(
        worker_id="test-worker-threads",
        threads=2,
        rabbitmq_client=mock_rmq,
        postgres_storage=mock_storage,
        s3_storage=mock_s3
    )

    mock_ack = MagicMock()
    mock_nack = MagicMock()

    # Simulamos que la coordinación/publicación lanza una excepción
    def failing_publish(body_bytes, target_queue, corr_id):
        raise ConnectionResetError("Broker desconectado")

    msg = {
        "request_id": "req-err-1",
        "task_id": "task-err-1",
        "operation": "sum",
        "payload": {"numbers": [10, 20]}
    }

    worker._process_task_job(
        msg=msg,
        correlation_id="req-err-1",
        reply_to="results_queue",
        safe_ack=mock_ack,
        safe_nack=lambda requeue: mock_nack(requeue),
        safe_publish_and_ack=failing_publish
    )

    worker.thread_pool.shutdown(wait=True)

    # NO debe haberse confirmado el mensaje
    assert not mock_ack.called
    # DEBE haberse reencolado con requeue=True
    assert mock_nack.called
    assert mock_nack.call_args[0][0] is True
