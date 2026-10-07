import socket
import sys

# Configuración de conexión
HOST = "localhost"
PORT = 5000

def iniciar_cliente():
    # Configuración del socket del cliente TCP/IP
    cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Intentamos conectar al servidor
        cliente_socket.connect((HOST, PORT))
        print(f"¡Conectado al servidor en {HOST}:{PORT}!")
        print("Escribí tus mensajes. Para salir, escribí 'éxito'.\n")
        
        while True:
            mensaje = input("Vos: ")
            
            # Evitar mandar mensajes vacíos
            if not mensaje.strip():
                continue
                
            # Usamos sendall() para asegurar que se envíe el mensaje completo por la red
            cliente_socket.sendall(mensaje.encode('utf-8'))
            
            # Esperar la confirmación del servidor
            respuesta = cliente_socket.recv(1024).decode('utf-8')
            
            # Si recv devuelve un string vacío, el servidor se cayó o cerró la conexión
            if not respuesta:
                print("\nError: El servidor cerró la conexión inesperadamente.")
                break
                
            print(f"Servidor: {respuesta}")
            
            # Condición de salida (ahora sale DESPUÉS de enviarlo al servidor y recibir acuse)
            if mensaje.strip().lower() == 'éxito':
                print("Desconectando del chat...")
                break
            
    except ConnectionRefusedError:
        print(f"Error: No se pudo conectar. Asegurate de que el servidor esté corriendo en el puerto {PORT}.")
    except KeyboardInterrupt:
        # Atrapamos Ctrl+C para evitar el traceback feo en el cliente también
        print("\nSalida forzada por el usuario.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
    finally:
        # El cierre del socket en el finally garantiza que se libere el recurso
        cliente_socket.close()

if __name__ == "__main__":
    # Protegemos la ejecución global
    try:
        iniciar_cliente()
    except KeyboardInterrupt:
        sys.exit(0)
