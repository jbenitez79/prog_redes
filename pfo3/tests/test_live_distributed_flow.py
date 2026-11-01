"""Test de integración real de extremo a extremo (E2E) con RabbitMQ y PostgreSQL reales.

Verifica:
- CA-01: Conexión cliente-servidor real.
- CA-02: Ejecución de suma [10, 20, 30] = 60 procesada por Worker real.
- CA-05: Verificación de worker_id en la respuesta.
- CA-06: Tarea enviada y consumida a través de colas durables de RabbitMQ.
- CA-07: Persistencia confirmada mediante SELECT directo a PostgreSQL.
"""

import threading
import time
import pytest
from client.client import DistributedTaskClient
from config.settings import settings
from messaging.rabbitmq_client import RabbitMQClient
from server.tcp_server import TCPServer
from storage.postgres import PostgresStorage
from workers.worker import DistributedWorker


def is_live_env_ready() -> bool:
    try:
        storage = PostgresStorage(password="postgres")
        with storage.get_connection() as conn:
            pass
        rmq = RabbitMQClient()
        if not rmq.connect():
            return False
        rmq.close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not is_live_env_ready(), reason="RabbitMQ o PostgreSQL no están disponibles en localhost.")
def test_full_distributed_lifecycle_live():
    # 1. Inicializar esquema en PostgreSQL
    storage = PostgresStorage(password="postgres")
    storage.init_schema()

    # 2. Iniciar Worker en hilo de fondo
    worker = DistributedWorker(
        worker_id="worker-live-01",
        threads=2,
        postgres_storage=storage
    )
    worker_thread = threading.Thread(target=worker.start, daemon=True)
    worker_thread.start()
    time.sleep(0.5)

    # 3. Iniciar Servidor TCP en puerto libre
    test_port = 5588
    server = TCPServer(
        host="127.0.0.1",
        port=test_port,
        server_id="server-live-node",
        max_connections=10
    )
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    try:
        # 4. Conectar cliente y enviar tarea de suma
        task_id = "task-live-e2e-001"
        req_id = "req-live-e2e-001"
        with DistributedTaskClient(host="127.0.0.1", port=test_port) as client:
            resp = client.send_task(
                operation="sum",
                payload={"numbers": [10, 20, 30]},
                task_id=task_id,
                request_id=req_id
            )

            # Verificar respuesta del cliente (CA-02, CA-05)
            assert resp["type"] == "task_result"
            assert resp["task_id"] == task_id
            assert resp["request_id"] == req_id
            assert resp["status"] == "completed"
            assert resp["result"] == 60
            assert resp["worker_id"] == "worker-live-01"

        # 5. Verificar persistencia real en PostgreSQL (CA-07)
        task_record = storage.get_task(task_id)
        assert task_record is not None
        assert task_record["task_id"] == task_id
        assert task_record["request_id"] == req_id
        assert task_record["operation"] == "sum"
        assert task_record["status"] == "completed"
        assert task_record["result"] == 60.0
        assert task_record["worker_id"] == "worker-live-01"
        assert task_record["completed_at"] is not None

    finally:
        server.stop()
        worker.stop()
