import socket
import sys

# ==============================================================================
# Configuración del socket TCP/IP del cliente (Sección 8.1 de OpenSpec)
# ==============================================================================
HOST = "localhost"
PORT = 5000
BUFFER_SIZE = 1024


def iniciar_cliente():
    """
    Cliente TCP interactivo que se conecta al servidor en localhost:5000.
    Permite el envío continuo de mensajes hasta que el usuario ingresa 'éxito'.
    """
    # Creación del socket TCP
    cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Intentar conectar con el servidor
        cliente_socket.connect((HOST, PORT))
    except ConnectionRefusedError:
        # Manejo de error controlado si el servidor está apagado o no responde
        print(f"Error: no se pudo conectar con el servidor en {HOST}:{PORT}.")
        return
    except Exception as e:
        print(f"Error al conectar con el servidor: {e}")
        return

    try:
        while True:
            # Solicitar mensaje al usuario por consola (Sección 8.2)
            mensaje = input("Ingrese un mensaje: ")

            # Evitar enviar mensajes vacíos
            if not mensaje.strip():
                continue

            # Condición de finalización: palabra exacta 'éxito' (Sección 8.3)
            if mensaje.strip().lower() in ('éxito', 'exito'):
                # Enviar notificación de finalización al servidor
                try:
                    cliente_socket.sendall(mensaje.encode('utf-8'))
                except Exception:
                    pass
                break

            # Enviar mensaje al servidor usando codificación UTF-8
            cliente_socket.sendall(mensaje.encode('utf-8'))

            # Esperar y recibir la confirmación del servidor
            respuesta = cliente_socket.recv(BUFFER_SIZE).decode('utf-8')

            # Si recv retorna vacío, el servidor cerró la conexión
            if not respuesta:
                print("Error: la conexión con el servidor se interrumpió.")
                break

            # Mostrar la respuesta con el formato esperado:
            # "Respuesta: Mensaje recibido: <timestamp>"
            print(f"Respuesta: {respuesta}\n")

    except KeyboardInterrupt:
        print("\nPrograma interrumpido por el usuario.")
    except Exception as e:
        print(f"Error durante la comunicación: {e}")
    finally:
        # Cerrar el socket para liberar el recurso
        cliente_socket.close()


if __name__ == "__main__":
    try:
        iniciar_cliente()
    except KeyboardInterrupt:
        sys.exit(0)
