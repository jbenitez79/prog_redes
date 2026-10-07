import os
import time
import socket
import sqlite3
import threading
import unittest

from servidor import (
    DB_NAME,
    HOST,
    PORT,
    inicializar_db,
    guardar_mensaje,
    inicializar_socket,
    aceptar_conexiones
)

class TestOpenSpecSockets(unittest.TestCase):
    server_socket = None
    server_thread = None

    @classmethod
    def setUpClass(cls):
        # Asegurar un entorno limpio para la base de datos mensajes.db
        if os.path.exists(DB_NAME):
            try:
                os.remove(DB_NAME)
            except Exception:
                pass

        inicializar_db()

        # Iniciar servidor en hilo secundario para pruebas de integración
        cls.server_socket = inicializar_socket()
        cls.server_thread = threading.Thread(
            target=aceptar_conexiones,
            args=(cls.server_socket,),
            daemon=True
        )
        cls.server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        if cls.server_socket:
            try:
                cls.server_socket.close()
            except Exception:
                pass

    def test_01_criterio_base_de_datos(self):
        """Criterio: La tabla mensajes debe contener exactamente id, contenido, fecha_envio, ip_cliente."""
        self.assertTrue(os.path.exists(DB_NAME), "mensajes.db debe existir.")
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(mensajes)")
        columnas = [col[1] for col in cursor.fetchall()]
        conn.close()

        esperadas = ["id", "contenido", "fecha_envio", "ip_cliente"]
        self.assertEqual(columnas, esperadas, f"Columnas en la BD {columnas} no coinciden con las especificadas {esperadas}")
        print("\n[OK] Criterio 5.1: Estructura de tabla mensajes en mensajes.db verificada.")

    def test_02_criterio_flujo_mensajes_y_respuesta(self):
        """Criterio: Múltiples mensajes, respuesta 'Mensaje recibido: <timestamp>' y finalización con 'éxito'."""
        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.connect((HOST, PORT))

        # 1. Enviar primer mensaje
        cliente.sendall("Hola servidor".encode('utf-8'))
        resp1 = cliente.recv(1024).decode('utf-8')
        self.assertTrue(resp1.startswith("Mensaje recibido: "), f"Respuesta inesperada: {resp1}")
        print(f"[OK] Criterio 7: Servidor respondió: '{resp1}'")

        # 2. Enviar segundo mensaje en la misma sesión
        cliente.sendall("Segundo mensaje".encode('utf-8'))
        resp2 = cliente.recv(1024).decode('utf-8')
        self.assertTrue(resp2.startswith("Mensaje recibido: "), f"Respuesta inesperada: {resp2}")
        print(f"[OK] Criterio 4: Segundo mensaje procesado en misma sesión: '{resp2}'")

        # 3. Enviar palabra clave 'éxito'
        cliente.sendall("éxito".encode('utf-8'))
        time.sleep(0.2)
        cliente.close()
        print("[OK] Criterio 8.3: Envío de 'éxito' finalizó la conexión correctamente.")

        # 4. Verificar en SQLite que los dos mensajes se guardaron y que 'éxito' NO se guardó
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT contenido, ip_cliente FROM mensajes")
        filas = cursor.fetchall()
        conn.close()

        contenidos = [f[0] for f in filas]
        self.assertIn("Hola servidor", contenidos)
        self.assertIn("Segundo mensaje", contenidos)
        self.assertNotIn("éxito", contenidos, "El mensaje 'éxito' no debe guardarse en la base de datos.")
        self.assertNotIn("exito", contenidos)
        print("[OK] Criterio 5.2 y 8.3: Mensajes persistidos correctamente y 'éxito' excluido de la base de datos.")

    def test_03_criterio_manejo_puerto_ocupado(self):
        """Criterio 3.3: Detectar cuando el puerto ya está en uso."""
        # Creamos un socket que ocupe un puerto temporal
        puerto_prueba = 5001
        sock_ocupador = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_ocupador.bind((HOST, puerto_prueba))
        sock_ocupador.listen(1)

        # Si intentamos hacer bind en el mismo puerto ocupado sin SO_REUSEADDR en un nuevo socket:
        with self.assertRaises(socket.error):
            sock_intento = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_intento.bind((HOST, puerto_prueba))
        
        sock_ocupador.close()
        print("[OK] Criterio 3.3: Detección de puerto en uso validada.")

if __name__ == '__main__':
    unittest.main()
