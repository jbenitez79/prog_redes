import socket
import sqlite3
import datetime
import threading
import sys
import os

# ==============================================================================
# 3.1 Configuración de red del socket TCP/IP
# ==============================================================================
# Host y Puerto según la especificación OpenSpec:
# localhost permite conexiones en la máquina local.
# Puerto 5000 es el puerto TCP designado para el servicio de chat.
HOST = "localhost"
PORT = 5000
BUFFER_SIZE = 1024

# Base de datos SQLite especificada en OpenSpec
DB_NAME = os.path.join(os.path.dirname(__file__), "mensajes.db")

# Variables globales para control de clientes y concurrencia
contador_clientes = 0
lock_contador = threading.Lock()


# ==============================================================================
# Inicialización de la base de datos
# ==============================================================================
def inicializar_db():
    """
    Crea la base de datos SQLite 'mensajes.db' y la tabla 'mensajes' si no existen.
    Campos según OpenSpec (Sección 5.1):
    - id: Identificador único autoincremental
    - contenido: Texto recibido del cliente
    - fecha_envio: Fecha y hora en que se procesó el mensaje
    - ip_cliente: Dirección IP del cliente emisor
    """
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contenido TEXT NOT NULL,
                fecha_envio TEXT NOT NULL,
                ip_cliente TEXT NOT NULL
            );
        ''')
        conexion.commit()
        conexion.close()
    except sqlite3.Error as e:
        manejar_errores("base_de_datos", f"Error crítico al inicializar la base de datos: {e}")
        sys.exit(1)


# ==============================================================================
# Guardar mensaje en SQLite
# ==============================================================================
def guardar_mensaje(contenido, ip_cliente):
    """
    Inserta un mensaje en la base de datos usando consultas parametrizadas (?)
    para evitar inyecciones SQL y problemas de formato (Sección 5.2 de OpenSpec).
    
    Retorna el timestamp generado si fue exitoso, o None si ocurrió un error en SQLite.
    """
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        
        # Timestamp exacto en formato YYYY-MM-DD HH:MM:SS
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            """
            INSERT INTO mensajes (contenido, fecha_envio, ip_cliente)
            VALUES (?, ?, ?)
            """,
            (contenido, fecha_actual, ip_cliente)
        )
        conexion.commit()
        conexion.close()
        return fecha_actual
    except sqlite3.Error as e:
        manejar_errores("base_de_datos", f"Error al registrar mensaje en SQLite: {e}")
        return None


# ==============================================================================
# Manejo de errores centralizado
# ==============================================================================
def manejar_errores(tipo_error, mensaje):
    """
    Maneja y formatea los errores de red y de base de datos sin mostrar
    tracebacks innecesarios al usuario final (Sección 3.3 y 6 de OpenSpec).
    """
    if tipo_error == "puerto_ocupado":
        print(f"Error: el puerto {PORT} ya está en uso.")
    elif tipo_error == "base_de_datos":
        print(f"[Error de Base de Datos] {mensaje}")
    elif tipo_error == "socket":
        print(f"[Error de Socket] {mensaje}")
    else:
        print(f"[Error] {mensaje}")


# ==============================================================================
# Inicialización del socket
# ==============================================================================
def inicializar_socket():
    """
    Configura y crea el socket TCP/IP según la Sección 3.3 de OpenSpec:
    1. Crea un socket TCP (socket.AF_INET, socket.SOCK_STREAM).
    2. Configura SO_REUSEADDR para permitir reutilizar el puerto rápidamente.
    3. Asocia el socket a localhost:5000 (bind).
    4. Lo deja en estado de escucha (listen).
    5. Contempla específicamente el caso en que el puerto 5000 ya esté en uso.
    """
    # Configuración del socket TCP/IP
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Permitir reutilizar la dirección local inmediatamente al reiniciar
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Asociar socket al host y puerto especificados
        server_socket.bind((HOST, PORT))
        
        # Habilitar escucha para conexiones entrantes
        server_socket.listen(5)
        
        # Timeout para permitir atender señales de apagado limpio (Ctrl+C en Windows)
        server_socket.settimeout(1.0)
        
        print(f"Servidor iniciado en {HOST}:{PORT}")
        print("Esperando conexiones...")
        return server_socket

    except socket.error as e:
        # Detectar si el puerto ya se encuentra ocupado (código 10048 en Windows o 98 en Linux)
        if getattr(e, 'errno', None) in (10048, 98) or "address already in use" in str(e).lower():
            manejar_errores("puerto_ocupado", "")
        else:
            manejar_errores("socket", f"No se pudo iniciar el servidor: {e}")
        sys.exit(1)


# ==============================================================================
# Recibir mensaje del cliente y enviar confirmación
# ==============================================================================
def atender_cliente(conexion, direccion, id_cliente):
    """
    Gestiona la sesión con un cliente conectado, permitiéndole enviar múltiples
    mensajes hasta que se desconecte o envíe 'éxito'.
    """
    ip_cliente, puerto_cliente = direccion
    print(f"[{id_cliente}] Conectado desde {ip_cliente}:{puerto_cliente}")

    try:
        while True:
            # Recibir mensaje del cliente
            datos = conexion.recv(BUFFER_SIZE)
            if not datos:
                print(f"[{id_cliente}] El cliente se desconectó.")
                break

            mensaje = datos.decode('utf-8').strip()

            # El mensaje 'éxito' no debe almacenarse en la base de datos (Sección 8.3)
            if mensaje.lower() == 'éxito' or mensaje.lower() == 'exito':
                print(f"[{id_cliente}] Finalizó sesión con 'éxito'.")
                break

            print(f"[{id_cliente} - {ip_cliente}] dice: {mensaje}")

            # Guardar mensaje en SQLite
            fecha_envio = guardar_mensaje(mensaje, ip_cliente)

            # Enviar confirmación al cliente según formato OpenSpec (Sección 7):
            # "Mensaje recibido: <timestamp>"
            if fecha_envio:
                respuesta = f"Mensaje recibido: {fecha_envio}"
            else:
                respuesta = "Error: no se pudo guardar el mensaje en la base de datos."

            conexion.sendall(respuesta.encode('utf-8'))

    except ConnectionResetError:
        print(f"[{id_cliente}] Conexión restablecida abruptamente por el cliente.")
    except Exception as e:
        manejar_errores("socket", f"Error en la comunicación con {id_cliente}: {e}")
    finally:
        # Cerrar el socket individual del cliente
        conexion.close()


# ==============================================================================
# Esperar conexiones de clientes
# ==============================================================================
def aceptar_conexiones(server_socket):
    """
    Bucle principal del servidor que acepta clientes entrantes y asigna
    un identificador único a cada uno (ej. Cliente-1, Cliente-2).
    """
    global contador_clientes

    try:
        while True:
            try:
                # Esperar conexiones de clientes
                conexion, direccion = server_socket.accept()

                # Asignación de identificador único de cliente
                with lock_contador:
                    contador_clientes += 1
                    id_cliente = f"Cliente-{contador_clientes}"

                # Atender cliente en un hilo independiente para permitir múltiples conexiones concurrentes
                hilo = threading.Thread(
                    target=atender_cliente,
                    args=(conexion, direccion, id_cliente),
                    daemon=True
                )
                hilo.start()

            except socket.timeout:
                # Permite verificar interrupciones periódicamente
                continue
            except OSError:
                # Socket cerrado externamente
                break
            except Exception as e:
                manejar_errores("socket", f"Error al aceptar conexión: {e}")

    except KeyboardInterrupt:
        print("\nApagando el servidor limpiamente...")
    finally:
        server_socket.close()
        print("Servidor detenido.")


# ==============================================================================
# Ejecución Principal
# ==============================================================================
if __name__ == "__main__":
    try:
        inicializar_db()
        sock = inicializar_socket()
        aceptar_conexiones(sock)
    except KeyboardInterrupt:
        sys.exit(0)
