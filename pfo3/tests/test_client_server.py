import socket
import threading
import time
from unittest.mock import MagicMock
import pytest
from client.client import DistributedTaskClient
from server.tcp_server import TCPServer
from server.dispatcher import TaskDispatcher
from server.protocol import build_task_result_response, build_error_response
from workers.operations import execute_operation


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def mock_dispatcher():
    dispatcher = MagicMock(spec=TaskDispatcher)
    
    def fake_dispatch(msg, timeout=30.0):
        task = msg.get("task", {})
        op = task.get("operation")
        payload = task.get("payload", {})
        req_id = msg.get("request_id")
        task_id = task.get("task_id")
        
        if op not in ("sum", "multiply", "max"):
            return build_error_response(
                request_id=req_id,
                code="INVALID_TASK",
                message=f"La operación solicitada '{op}' no es válida.",
                task_id=task_id
            )
            
        res = execute_operation(op, payload)
        return build_task_result_response(
            request_id=req_id,
            task_id=task_id,
            result=res,
            worker_id="test-worker-01"
        )
        
    dispatcher.dispatch_task.side_effect = fake_dispatch
    return dispatcher


@pytest.fixture
def running_server(mock_dispatcher):
    port = get_free_port()
    server = TCPServer(
        host="127.0.0.1",
        port=port,
        server_id="test-server",
        max_connections=10,
        dispatcher=mock_dispatcher
    )
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(0.15)  # tiempo para bind y listen
    yield ("127.0.0.1", port)
    server.stop()
    server_thread.join(timeout=1.0)


def test_client_server_ca01_ca02_sum(running_server):
    host, port = running_server
    with DistributedTaskClient(host=host, port=port) as client:
        # CA-02: Tarea de suma con [10, 20, 30] debe devolver 60
        resp = client.send_task(
            operation="sum",
            payload={"numbers": [10, 20, 30]},
            task_id="task-001",
            request_id="req-001"
        )
        assert resp["type"] == "task_result"
        assert resp["status"] == "completed"
        assert resp["result"] == 60
        assert resp["worker_id"] == "test-worker-01"
        assert resp["task_id"] == "task-001"


def test_client_server_multiple_tasks_same_session(running_server):
    host, port = running_server
    with DistributedTaskClient(host=host, port=port) as client:
        r1 = client.send_task("sum", {"numbers": [1, 2, 3]})
        assert r1["result"] == 6

        r2 = client.send_task("multiply", {"numbers": [3, 4, 5]})
        assert r2["result"] == 60

        r3 = client.send_task("max", {"numbers": [99, 105, 42]})
        assert r3["result"] == 105


def test_client_server_ca03_unsupported_operation(running_server):
    host, port = running_server
    with DistributedTaskClient(host=host, port=port) as client:
        resp = client.send_task("integral", {"numbers": [1, 2]})
        assert resp["type"] == "error"
        assert resp["error"]["code"] == "INVALID_TASK"


def test_client_server_concurrency(running_server):
    host, port = running_server
    results = []

    def client_worker(n):
        with DistributedTaskClient(host=host, port=port) as c:
            resp = c.send_task("sum", {"numbers": [n, n]})
            results.append(resp["result"])

    threads = [threading.Thread(target=client_worker, args=(i,)) for i in range(1, 6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 5
    assert sorted(results) == [2, 4, 6, 8, 10]


def test_client_server_broken_client_resilience(running_server):
    host, port = running_server
    # Conectar y enviar datos inválidos sin respetar JSON
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall(b"INVALID DATA\n")
    data = s.recv(1024)
    s.close()
    
    assert b"error" in data.lower()
    
    # El servidor debe seguir vivo y aceptar conexiones válidas después del error
    with DistributedTaskClient(host=host, port=port) as c:
        resp = c.send_task("sum", {"numbers": [5, 5]})
        assert resp["result"] == 10
