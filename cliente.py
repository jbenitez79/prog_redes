import socket

# Configuración de conexión
HOST = "127.0.0.1"
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
            
            # Condición de salida que pide el TP
            if mensaje.strip().lower() == 'éxito':
                print("Desconectando del chat...")
                break
                
            # Evitar mandar mensajes vacíos
            if not mensaje.strip():
                continue
                
            # Enviar el mensaje codificado
            cliente_socket.send(mensaje.encode('utf-8'))
            
            # Esperar la confirmación del servidor
            respuesta = cliente_socket.recv(1024).decode('utf-8')
            print(f"Servidor: {respuesta}")
            
    except ConnectionRefusedError:
        print(f"Error: No se pudo conectar. Asegurate de que el servidor esté corriendo en el puerto {PORT}.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
    finally:
        cliente_socket.close()

if __name__ == "__main__":
    iniciar_cliente()
