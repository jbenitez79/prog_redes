import threading
import time
import pytest
from server.task_manager import TaskManager


def test_task_manager_success_flow():
    mgr = TaskManager()
    req_id = "req-123"
    mgr.register_request(req_id)

    # Simular worker que responde tras 50ms en otro hilo
    def worker_simulation():
        time.sleep(0.05)
        mgr.set_result(req_id, {"status": "completed", "result": 42})

    t = threading.Thread(target=worker_simulation)
    t.start()

    res = mgr.wait_for_result(req_id, timeout=2.0)
    t.join()

    assert res["status"] == "completed"
    assert res["result"] == 42


def test_task_manager_timeout():
    mgr = TaskManager()
    req_id = "req-timeout"
    mgr.register_request(req_id)

    with pytest.raises(TimeoutError):
        mgr.wait_for_result(req_id, timeout=0.1)


def test_task_manager_unknown_request():
    mgr = TaskManager()
    with pytest.raises(ValueError):
        mgr.wait_for_result("non-existent-req", timeout=0.1)
