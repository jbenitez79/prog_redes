import json
import pytest
from server.protocol import (
    DELIMITER,
    ProtocolError,
    serialize_message,
    extract_messages,
    validate_submit_task,
    build_task_result_response,
    build_error_response
)


def test_serialize_and_extract_single_message():
    data = {"type": "submit_task", "request_id": "req-001"}
    raw = serialize_message(data)
    assert raw.endswith(DELIMITER)
    
    messages, remaining = extract_messages(raw)
    assert len(messages) == 1
    assert messages[0] == data
    assert remaining == b""


def test_extract_messages_fragmented():
    """Simula llegada de datos en dos paquetes TCP distintos (fragmentación)."""
    full_raw = serialize_message({"type": "submit_task", "request_id": "req-002"})
    part1 = full_raw[:10]
    part2 = full_raw[10:]
    
    # Paquete 1 llega incompleto
    msgs, buf = extract_messages(part1)
    assert msgs == []
    assert buf == part1
    
    # Llega paquete 2 completando el mensaje
    msgs, buf = extract_messages(buf + part2)
    assert len(msgs) == 1
    assert msgs[0]["request_id"] == "req-002"
    assert buf == b""


def test_extract_messages_grouped():
    """Simula llegada de múltiples mensajes agrupados en una sola llamada recv() TCP."""
    m1 = {"type": "submit_task", "request_id": "req-1"}
    m2 = {"type": "submit_task", "request_id": "req-2"}
    raw = serialize_message(m1) + serialize_message(m2)
    
    msgs, buf = extract_messages(raw)
    assert len(msgs) == 2
    assert msgs[0]["request_id"] == "req-1"
    assert msgs[1]["request_id"] == "req-2"
    assert buf == b""


def test_extract_messages_invalid_json():
    raw = b"this is not a valid json\n"
    with pytest.raises(ProtocolError) as exc_info:
        extract_messages(raw)
    assert exc_info.value.code == "INVALID_JSON"


def test_validate_submit_task_success():
    valid_task = {
        "type": "submit_task",
        "request_id": "req-001",
        "task": {
            "task_id": "task-001",
            "operation": "sum",
            "payload": {"numbers": [1, 2, 3]}
        }
    }
    # No debe levantar excepción
    validate_submit_task(valid_task)


def test_validate_submit_task_missing_fields():
    with pytest.raises(ProtocolError) as exc_info:
        validate_submit_task({"type": "wrong_type"})
    assert exc_info.value.code == "UNSUPPORTED_TYPE"
    
    with pytest.raises(ProtocolError) as exc_info:
        validate_submit_task({"type": "submit_task", "request_id": ""})
    assert exc_info.value.code == "MISSING_REQUEST_ID"

    with pytest.raises(ProtocolError) as exc_info:
        validate_submit_task({"type": "submit_task", "request_id": "req-1", "task": {}})
    assert exc_info.value.code == "MISSING_TASK_ID"


def test_build_responses():
    res = build_task_result_response("req-1", "task-1", 60, "worker-01")
    assert res["status"] == "completed"
    assert res["result"] == 60
    assert res["worker_id"] == "worker-01"

    err = build_error_response("req-1", "INVALID_TASK", "Error test", task_id="task-1")
    assert err["type"] == "error"
    assert err["error"]["code"] == "INVALID_TASK"
    assert err["task_id"] == "task-1"
