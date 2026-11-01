"""Servidor TCP concurrente multi-hilo para recepción de tareas distribuidas.

Cumple con RF-01, RF-02, RF-04 y RF-06:
- Gestiona múltiples clientes concurrentemente mediante ThreadPoolExecutor.
- Decodifica y valida mensajes según el protocolo TCP delimitado por salto de línea.
- Despacha tareas hacia RabbitMQ sin bloquear el hilo principal.
- Tolera desconexiones abruptas sin interrumpir el funcionamiento global.
"""

import argparse
import logging
import socket
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from config.settings import settings
from server.protocol import (
    ProtocolError,
    extract_messages,
    serialize_message,
    validate_submit_task,
    build_error_response
)
from server.dispatcher import TaskDispatcher

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] [%(threadName)s] %(message)s"
)
logger = logging.getLogger("TCPServer")


class TCPServer:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        server_id: Optional[str] = None,
        max_connections: Optional[int] = None,
        dispatcher: Optional[TaskDispatcher] = None
    ):
        self.host = host or settings.TCP_HOST
        self.port = port or settings.TCP_PORT
        self.server_id = server_id or settings.SERVER_ID
        self.max_connections = max_connections or settings.MAX_CONNECTIONS
        self.dispatcher = dispatcher or TaskDispatcher()
        
        self.thread_pool = ThreadPoolExecutor(
            max_workers=self.max_connections,
            thread_name_prefix=f"{self.server_id}-client"
        )
        self._server_socket = None
        self._running = False

    def _handle_client_connection(self, client_sock: socket.socket, client_addr: tuple) -> None:
        """Atiende la conexión persistente de un cliente TCP."""
        logger.info(f"[{self.server_id}] Nueva conexión aceptada desde {client_addr}")
        buffer = b""

        try:
            client_sock.settimeout(settings.SOCKET_TIMEOUT)
            while self._running:
                try:
                    data = client_sock.recv(settings.BUFFER_SIZE)
                    if not data:
                        logger.info(f"[{self.server_id}] Cliente {client_addr} cerró la conexión ordenadamente.")
                        break
                    
                    buffer += data
                    try:
                        messages, buffer = extract_messages(buffer)
                    except ProtocolError as pe:
                        logger.warning(f"[{self.server_id}] Error de protocolo al parsear desde {client_addr}: {pe.message}")
                        err_resp = build_error_response(
                            request_id=pe.request_id,
                            code=pe.code,
                            message=pe.message
                        )
                        client_sock.sendall(serialize_message(err_resp))
                        buffer = b""
                        continue

                    for msg in messages:
                        logger.debug(f"[{self.server_id}] Mensaje recibido de {client_addr}: {msg}")
                        try:
                            # 1. Validar formato según protocolo
                            validate_submit_task(msg)

                            # 2. Despachar tarea a la arquitectura distribuida
                            response = self.dispatcher.dispatch_task(msg, timeout=settings.SOCKET_TIMEOUT)

                        except ProtocolError as pe:
                            logger.warning(f"[{self.server_id}] Error de protocolo con {client_addr}: {pe.message}")
                            response = build_error_response(
                                request_id=pe.request_id or msg.get("request_id"),
                                code=pe.code,
                                message=pe.message
                            )
                        except Exception as e:
                            logger.error(f"[{self.server_id}] Error procesando solicitud: {e}")
                            response = build_error_response(
                                request_id=msg.get("request_id"),
                                code="SERVER_ERROR",
                                message=f"Error interno del servidor: {e}"
                            )

                        # 3. Enviar respuesta delimitada al socket
                        payload_bytes = serialize_message(response)
                        client_sock.sendall(payload_bytes)
                        logger.debug(f"[{self.server_id}] Respuesta enviada a {client_addr}: {response.get('type')}")

                except socket.timeout:
                    # Timeout para permitir verificar self._running y mantener viva la conexión
                    continue
                except ConnectionResetError:
                    logger.warning(f"[{self.server_id}] Conexión reseteada abruptamente por el cliente {client_addr}.")
                    break
                except Exception as ex:
                    logger.error(f"[{self.server_id}] Excepción en lectura de socket {client_addr}: {ex}")
                    break

        finally:
            try:
                client_sock.close()
            except Exception:
                pass
            logger.info(f"[{self.server_id}] Conexión con {client_addr} finalizada.")

    def start(self) -> None:
        """Inicia el socket servidor y escucha conexiones entrantes."""
        self._running = True
        
        # Iniciar listener de respuestas de RabbitMQ
        self.dispatcher.start_results_listener()

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(128)

        logger.info(f"[{self.server_id}] Servidor TCP iniciado escuchando en {self.host}:{self.port} (Pool hilos: {self.max_connections})")

        try:
            while self._running:
                try:
                    self._server_socket.settimeout(1.0)
                    client_sock, client_addr = self._server_socket.accept()
                    self.thread_pool.submit(self._handle_client_connection, client_sock, client_addr)
                except socket.timeout:
                    continue
                except OSError:
                    break
        except KeyboardInterrupt:
            logger.info(f"[{self.server_id}] Señal de interrupción recibida. Deteniendo servidor...")
        finally:
            self.stop()

    def stop(self) -> None:
        """Detiene el servidor y libera sockets e hilos."""
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
        self.thread_pool.shutdown(wait=False)
        self.dispatcher.stop()
        logger.info(f"[{self.server_id}] Servidor detenido.")


def main():
    parser = argparse.ArgumentParser(description="Servidor TCP Distribuido PFO 3")
    parser.add_argument("--host", type=str, default=None, help="Host de escucha")
    parser.add_argument("--port", type=int, default=None, help="Puerto de escucha")
    parser.add_argument("--server-id", type=str, default=None, help="Identificador de la instancia")
    parser.add_argument("--max-connections", type=int, default=None, help="Límite del pool de hilos de conexiones")
    args = parser.parse_args()

    server = TCPServer(
        host=args.host,
        port=args.port,
        server_id=args.server_id,
        max_connections=args.max_connections
    )
    server.start()


if __name__ == "__main__":
    main()
