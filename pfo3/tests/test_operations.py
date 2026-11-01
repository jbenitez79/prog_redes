import pytest
from workers.operations import (
    execute_operation,
    execute_sum,
    execute_multiply,
    execute_max,
    get_available_operations,
    OperationError
)


def test_available_operations():
    ops = get_available_operations()
    assert "sum" in ops
    assert "multiply" in ops
    assert "max" in ops


def test_execute_sum():
    assert execute_sum({"numbers": [10, 20, 30]}) == 60
    assert execute_sum({"numbers": [-5, 5, 0]}) == 0
    assert execute_sum({"numbers": [1.5, 2.5]}) == 4.0


def test_execute_multiply():
    assert execute_multiply({"numbers": [2, 3, 4]}) == 24
    assert execute_multiply({"numbers": [10, 0, 5]}) == 0
    assert execute_multiply({"numbers": [-2, 3]}) == -6


def test_execute_max():
    assert execute_max({"numbers": [10, 50, 20]}) == 50
    assert execute_max({"numbers": [-10, -5, -20]}) == -5
    assert execute_max({"numbers": [42]}) == 42


def test_execute_operation_dispatcher():
    assert execute_operation("sum", {"numbers": [10, 20]}) == 30
    assert execute_operation("multiply", {"numbers": [3, 4]}) == 12
    assert execute_operation("max", {"numbers": [1, 9, 3]}) == 9


def test_execute_unknown_operation():
    with pytest.raises(OperationError) as exc_info:
        execute_operation("power", {"numbers": [2, 3]})
    assert "Operación desconocida" in str(exc_info.value)


def test_operation_invalid_payload():
    with pytest.raises(OperationError):
        execute_operation("sum", {})

    with pytest.raises(OperationError):
        execute_operation("sum", {"numbers": []})

    with pytest.raises(OperationError):
        execute_operation("sum", {"numbers": ["not", "numbers"]})

    with pytest.raises(OperationError):
        execute_operation("sum", {"numbers": [True, False]})
