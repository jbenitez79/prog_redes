import socket
import sqlite3
import datetime
import sys

# Configuraciones globales
DB_NAME = "chat.db"
HOST = "localhost"
PORT = 5000

def inicializar_db():
    # Configuración de la base de datos con SQLite3
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        # Creamos la tabla si no existe, con los campos pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contenido TEXT NOT NULL,
                fecha_envio TEXT NOT NULL,
                ip_cliente TEXT NOT NULL
            )
        ''')
        conexion.commit()
        conexion.close()
    except sqlite3.Error as e:
        print(f"Error crítico al acceder a la base de datos: {e}")
        sys.exit(1)

def guardar_mensaje(contenido, ip_cliente):
    # Función para guardar el mensaje en la DB
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        # Generamos el timestamp para la fecha de envío
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            "INSERT INTO mensajes (contenido, fecha_envio, ip_cliente) VALUES (?, ?, ?)",
            (contenido, fecha_actual, ip_cliente)
        )
        conexion.commit()
        conexion.close()
        return fecha_actual
    except sqlite3.Error as e:
        print(f"Error al guardar en la base de datos: {e}")
        return None

def inicializar_socket():
    # Configuración del socket TCP/IP
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Esto permite reutilizar el puerto rápido si se reinicia el server, evitando errores
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"Servidor escuchando en {HOST}:{PORT}...")
        return server_socket
    except socket.error as e:
        print(f"Error al iniciar el servidor. ¿El puerto {PORT} está ocupado?: {e}")
        sys.exit(1)

def recibir_mensajes(conexion, ip_cliente):
    # Usamos try/finally para asegurar que el socket del cliente se cierre sí o sí
    try:
        while True:
            try:
                datos = conexion.recv(1024)
                if not datos:
                    print(f"El cliente {ip_cliente} se desconectó.")
                    break
                
                mensaje = datos.decode('utf-8')
                print(f"[{ip_cliente}] dice: {mensaje}")
                
                # Guardamos en la base de datos
                fecha_envio = guardar_mensaje(mensaje, ip_cliente)
                
                # Armamos la respuesta para el cliente
                if fecha_envio:
                    respuesta = f"Mensaje recibido: {fecha_envio}"
                else:
                    respuesta = "Error del servidor: no se pudo guardar el mensaje."
                    
                conexion.send(respuesta.encode('utf-8'))
                
            except socket.timeout:
                # Timeout para dar lugar al KeyboardInterrupt
                continue
            except ConnectionResetError:
                print(f"Conexión perdida con el cliente {ip_cliente}")
                break
            except Exception as e:
                print(f"Error al procesar el mensaje: {e}")
                break
    finally:
        # Se ejecuta siempre, incluso si hay un KeyboardInterrupt o error no manejado
        conexion.close()

def aceptar_conexiones(server_socket):
    # Truco vital en Windows: agregar un timeout permite que Python procese el Ctrl+C
    server_socket.settimeout(1.0)
    print("Esperando conexiones (Presioná Ctrl+C para salir)...")
    
    # Bloque try/except/finally global de conexiones para apagado totalmente limpio
    try:
        while True:
            try:
                conexion, direccion = server_socket.accept()
                
                # También le ponemos timeout a la conexión individual del cliente
                conexion.settimeout(1.0)
                
                ip_cliente = direccion[0]
                print(f"¡Nueva conexión desde: {ip_cliente}!")
                
                recibir_mensajes(conexion, ip_cliente)
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error al aceptar la conexión: {e}")
                
    except KeyboardInterrupt:
        print("\nApagando el servidor manualmente...")
    finally:
        # Garantiza que el socket principal se libere sin importar qué pase
        server_socket.close()

if __name__ == "__main__":
    # Prevenimos cualquier traceback global extra
    try:
        inicializar_db()
        sock = inicializar_socket()
        aceptar_conexiones(sock)
    except KeyboardInterrupt:
        sys.exit(0)
