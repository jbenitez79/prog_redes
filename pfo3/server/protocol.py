"""Protocolo de aplicación sobre TCP para intercambio de mensajes JSON delimitados por salto de línea.

Resuelve explícitamente la fragmentación y agrupación de paquetes TCP (stream de bytes).
"""

import json
from typing import Any, Dict, List, Optional, Tuple

DELIMITER = b"\n"


class ProtocolError(Exception):
    """Excepción para errores de protocolo o formato de mensaje."""
    def __init__(self, code: str, message: str, request_id: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.request_id = request_id


def serialize_message(data: Dict[str, Any]) -> bytes:
    """Serializa un diccionario a JSON UTF-8 terminado en salto de línea (delimitador)."""
    raw_json = json.dumps(data, ensure_ascii=False)
    return raw_json.encode("utf-8") + DELIMITER


def extract_messages(buffer: bytes) -> Tuple[List[Dict[str, Any]], bytes]:
    """Extrae todos los mensajes JSON completos del buffer TCP.
    
    Retorna:
        - Lista de diccionarios de mensajes parseados.
        - Buffer remanente (bytes no delimitados aún).
    
    Eleva ProtocolError si algún mensaje delimitado no es JSON válido.
    """
    messages: List[Dict[str, Any]] = []
    
    while DELIMITER in buffer:
        line, buffer = buffer.split(DELIMITER, 1)
        line = line.strip()
        if not line:
            continue  # ignorar líneas vacías
        
        try:
            decoded_text = line.decode("utf-8")
            parsed = json.loads(decoded_text)
            if not isinstance(parsed, dict):
                raise ProtocolError(
                    code="INVALID_MESSAGE_FORMAT",
                    message="El mensaje debe ser un objeto JSON."
                )
            messages.append(parsed)
        except UnicodeDecodeError as e:
            raise ProtocolError(
                code="INVALID_ENCODING",
                message=f"El mensaje debe estar codificado en UTF-8 válido: {e}"
            )
        except json.JSONDecodeError as e:
            raise ProtocolError(
                code="INVALID_JSON",
                message=f"Sintaxis JSON inválida: {e}"
            )
            
    return messages, buffer


def validate_submit_task(msg: Dict[str, Any]) -> None:
    """Valida la estructura de una solicitud 'submit_task'."""
    if msg.get("type") != "submit_task":
        raise ProtocolError(
            code="UNSUPPORTED_TYPE",
            message=f"Tipo de mensaje no soportado: '{msg.get('type')}'. Se esperaba 'submit_task'.",
            request_id=msg.get("request_id")
        )
    
    request_id = msg.get("request_id")
    if not request_id or not isinstance(request_id, str):
        raise ProtocolError(
            code="MISSING_REQUEST_ID",
            message="El mensaje debe contener un 'request_id' de tipo string no vacío.",
            request_id=request_id
        )
        
    task = msg.get("task")
    if not isinstance(task, dict):
        raise ProtocolError(
            code="MISSING_TASK",
            message="El mensaje debe contener un objeto 'task'.",
            request_id=request_id
        )
        
    task_id = task.get("task_id")
    if not task_id or not isinstance(task_id, str):
        raise ProtocolError(
            code="MISSING_TASK_ID",
            message="El objeto 'task' debe contener un 'task_id' de tipo string.",
            request_id=request_id
        )
        
    operation = task.get("operation")
    if not operation or not isinstance(operation, str):
        raise ProtocolError(
            code="MISSING_OPERATION",
            message="El objeto 'task' debe contener un campo 'operation' válido.",
            request_id=request_id
        )
        
    if "payload" not in task or not isinstance(task.get("payload"), dict):
        raise ProtocolError(
            code="MISSING_PAYLOAD",
            message="El objeto 'task' debe contener un diccionario 'payload'.",
            request_id=request_id
        )


def build_task_result_response(
    request_id: str,
    task_id: str,
    result: Any,
    worker_id: str,
    status: str = "completed"
) -> Dict[str, Any]:
    """Construye un mensaje de respuesta exitosa según el protocolo."""
    return {
        "type": "task_result",
        "request_id": request_id,
        "task_id": task_id,
        "status": status,
        "result": result,
        "worker_id": worker_id
    }


def build_error_response(
    request_id: Optional[str],
    code: str,
    message: str,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """Construye un mensaje de respuesta de error controlado."""
    resp = {
        "type": "error",
        "request_id": request_id or "unknown",
        "error": {
            "code": code,
            "message": message
        }
    }
    if task_id:
        resp["task_id"] = task_id
    return resp
