"""Cliente TCP para el Sistema Distribuido PFO 3.

Cumple con RF-03:
- Conexión TCP con host y puerto configurables (servidor directo o balanceador Nginx).
- Envío de tareas y recepción de respuestas formateadas.
- Soporte para múltiples tareas en la misma sesión persistente.
- Manejo robusto de errores de red y ejecución.
- Interfaz interactiva de consola y clase cliente para scripts y tests.
"""

import argparse
import socket
import sys
import uuid
from typing import Any, Dict, List, Optional

from config.settings import settings
from server.protocol import (
    DELIMITER,
    extract_messages,
    serialize_message
)


class DistributedTaskClient:
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, timeout: float = 30.0):
        self.host = host or settings.LB_HOST
        self.port = port or settings.LB_PORT
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._buffer: bytes = b""

    def connect(self) -> None:
        """Establece la conexión TCP con el servidor o balanceador."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        self._sock.connect((self.host, self.port))
        self._buffer = b""

    def close(self) -> None:
        """Cierra la conexión TCP de forma ordenada."""
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def is_connected(self) -> bool:
        return self._sock is not None

    def send_task(
        self,
        operation: str,
        payload: Dict[str, Any],
        task_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Envía una tarea y espera la respuesta correspondiente."""
        if not self.is_connected():
            self.connect()

        req_id = request_id or f"req-{uuid.uuid4().hex[:8]}"
        t_id = task_id or f"task-{uuid.uuid4().hex[:8]}"

        request_envelope = {
            "type": "submit_task",
            "request_id": req_id,
            "task": {
                "task_id": t_id,
                "operation": operation,
                "payload": payload
            }
        }

        # 1. Enviar mensaje serializado con delimitador
        data_bytes = serialize_message(request_envelope)
        self._sock.sendall(data_bytes)

        # 2. Leer del socket hasta obtener la respuesta completa delimitada
        while True:
            # Primero chequear si ya hay un mensaje en el buffer
            messages, self._buffer = extract_messages(self._buffer)
            for msg in messages:
                # Comprobar si coincide el request_id
                if msg.get("request_id") == req_id:
                    return msg

            # Si no hay mensaje completo, leer más datos
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("El servidor cerró la conexión inesperadamente antes de responder.")
            self._buffer += chunk

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def print_banner():
    print("=" * 65)
    print("      SISTEMA DISTRIBUIDO - CLIENTE TCP (PFO 3)")
    print("=" * 65)


def run_interactive_client(host: str, port: int):
    print_banner()
    print(f"[*] Conectando a {host}:{port}...")

    client = DistributedTaskClient(host=host, port=port)
    try:
        client.connect()
        print(f"[+] Conexión establecida exitosamente con {host}:{port}.\n")
    except Exception as e:
        print(f"[-] Error crítico al conectar a {host}:{port}: {e}")
        sys.exit(1)

    try:
        while True:
            print("-" * 50)
            print("Seleccione una operación a ejecutar:")
            print("1. Sumar números (sum)")
            print("2. Multiplicar números (multiply)")
            print("3. Obtener el máximo (max)")
            print("4. Enviar ráfaga de tareas concurrentes (Test de Carga)")
            print("5. Probar operación no permitida (Prueba de Error CA-03)")
            print("6. Salir")
            print("-" * 50)

            opcion = input("Opción [1-6]: ").strip()

            if opcion == "6":
                print("\n[*] Cerrando conexión...")
                break

            elif opcion in ("1", "2", "3"):
                op_names = {"1": "sum", "2": "multiply", "3": "max"}
                op_name = op_names[opcion]
                entrada = input(f"Ingrese números separados por coma para '{op_name}' (ej: 10, 20, 30): ").strip()
                try:
                    numeros = [float(x.strip()) if "." in x else int(x.strip()) for x in entrada.split(",") if x.strip()]
                    if not numeros:
                        print("[-] Debe ingresar al menos un número.")
                        continue
                except ValueError:
                    print("[-] Error de formato: asegúrese de ingresar números válidos.")
                    continue

                print(f"\n[>] Enviando tarea '{op_name}' con datos: {numeros}...")
                try:
                    response = client.send_task(operation=op_name, payload={"numbers": numeros})
                    if response.get("type") == "task_result":
                        print(f"[OK] RESULTADO RECIBIDO:")
                        print(f"    - Task ID:   {response.get('task_id')}")
                        print(f"    - Estado:    {response.get('status')}")
                        print(f"    - Resultado: {response.get('result')}")
                        print(f"    - Worker:    {response.get('worker_id')}")
                    else:
                        err = response.get("error", {})
                        print(f"[!] RESPUESTA DE ERROR DEL SERVIDOR:")
                        print(f"    - Código:    {err.get('code')}")
                        print(f"    - Mensaje:   {err.get('message')}")
                except Exception as ex:
                    print(f"[-] Error durante la comunicación: {ex}")

            elif opcion == "4":
                print("\n[>] Enviando ráfaga de 5 tareas concurrentes...")
                import time
                start_time = time.time()
                for i in range(1, 6):
                    nums = [i * 10, i * 20, i * 30]
                    res = client.send_task(operation="sum", payload={"numbers": nums})
                    print(f"    - Tarea {i}: sum({nums}) = {res.get('result')} (Procesado por: {res.get('worker_id')})")
                elapsed = time.time() - start_time
                print(f"[OK] Ráfaga completada en {elapsed:.3f} segundos.")

            elif opcion == "5":
                print("\n[>] Enviando tarea con operación desconocida 'calcular_derivada'...")
                try:
                    res = client.send_task(operation="calcular_derivada", payload={"numbers": [1, 2, 3]})
                    err = res.get("error", {})
                    print(f"[OK] Error controlado recibido con éxito:")
                    print(f"    - Código:  {err.get('code')}")
                    print(f"    - Mensaje: {err.get('message')}")
                except Exception as ex:
                    print(f"[-] Error: {ex}")

            else:
                print("[-] Opción inválida. Intente nuevamente.")

    finally:
        client.close()
        print("[+] Conexión finalizada correctamente. ¡Hasta luego!")


def main():
    parser = argparse.ArgumentParser(description="Cliente TCP Distribuido PFO 3")
    parser.add_argument("--host", type=str, default=None, help="Host del servidor o balanceador")
    parser.add_argument("--port", type=int, default=None, help="Puerto del servidor o balanceador")
    args = parser.parse_args()

    host = args.host or settings.LB_HOST
    port = args.port or settings.LB_PORT
    run_interactive_client(host=host, port=port)


if __name__ == "__main__":
    main()
