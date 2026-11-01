"""Operaciones matemáticas registradas de demostración para los workers.

Garantiza seguridad estricta: únicamente las operaciones explícitamente registradas
pueden ser invocadas. Se rechaza cualquier intento de ejecución de código arbitrario.
"""

from typing import Any, Callable, Dict, List, Union

Number = Union[int, float]


class OperationError(Exception):
    """Excepción específica para errores de validación o ejecución de operaciones."""
    pass


def _validate_numbers(payload: Any) -> List[Number]:
    if not isinstance(payload, dict):
        raise OperationError("El payload debe ser un objeto JSON.")
    
    if "numbers" not in payload:
        raise OperationError("El payload debe contener el campo 'numbers'.")
    
    numbers = payload["numbers"]
    if not isinstance(numbers, list):
        raise OperationError("El campo 'numbers' debe ser una lista.")
    
    if len(numbers) == 0:
        raise OperationError("La lista 'numbers' no puede estar vacía.")
    
    for item in numbers:
        if not isinstance(item, (int, float)) or isinstance(item, bool):
            raise OperationError(f"Todos los elementos deben ser números. Se encontró: {repr(item)}")
    
    return numbers


def execute_sum(payload: Dict[str, Any]) -> Number:
    numbers = _validate_numbers(payload)
    return sum(numbers)


def execute_multiply(payload: Dict[str, Any]) -> Number:
    numbers = _validate_numbers(payload)
    result = 1
    for n in numbers:
        result *= n
    return result


def execute_max(payload: Dict[str, Any]) -> Number:
    numbers = _validate_numbers(payload)
    return max(numbers)


# Registro de operaciones explícitamente permitidas
_OPERATIONS_REGISTRY: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    "sum": execute_sum,
    "multiply": execute_multiply,
    "max": execute_max,
}


def get_available_operations() -> List[str]:
    """Retorna la lista de nombres de operaciones permitidas."""
    return list(_OPERATIONS_REGISTRY.keys())


def execute_operation(operation_name: str, payload: Dict[str, Any]) -> Any:
    """Ejecuta una operación registrada o eleva OperationError si no está registrada."""
    if not isinstance(operation_name, str):
        raise OperationError("El nombre de la operación debe ser un string.")
    
    operation_fn = _OPERATIONS_REGISTRY.get(operation_name.strip().lower())
    if operation_fn is None:
        raise OperationError(
            f"Operación desconocida '{operation_name}'. "
            f"Operaciones permitidas: {', '.join(_OPERATIONS_REGISTRY.keys())}"
        )
    
    return operation_fn(payload)
