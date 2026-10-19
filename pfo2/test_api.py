import os
import unittest
import sqlite3
from servidor import app, inicializar_db, DB_NAME


class TestGestionTareasAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Asegurar una base de datos limpia para tests
        if os.path.exists(DB_NAME):
            try:
                os.remove(DB_NAME)
            except Exception:
                pass
        inicializar_db()

    def setUp(self):
        # Crear cliente de pruebas de Flask
        self.app = app.test_client()
        self.app.testing = True

    def test_01_registro_y_hashing_contrasena(self):
        """1. Registro de Usuarios y Requisitos técnicos: hashing en SQLite."""
        resp = self.app.post("/registro", json={"usuario": "juan", "contraseña": "password123"})
        self.assertEqual(resp.status_code, 201)
        datos = resp.get_json()
        self.assertEqual(datos["usuario"], "juan")

        # Verificar en SQLite que la contraseña NO está en texto plano
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT contrasena_hash FROM usuarios WHERE usuario = 'juan'")
        fila = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(fila)
        hash_almacenado = fila[0]
        self.assertNotEqual(hash_almacenado, "password123")
        self.assertTrue(hash_almacenado.startswith("scrypt:") or hash_almacenado.startswith("pbkdf2:"))

    def test_02_registro_duplicado_y_datos_incompletos(self):
        """Manejo de errores: 400 Bad Request ante duplicados o campos vacíos."""
        resp_dup = self.app.post("/registro", json={"usuario": "juan", "contraseña": "otra"})
        self.assertEqual(resp_dup.status_code, 400)

        resp_inc = self.app.post("/registro", json={"usuario": "incompleto"})
        self.assertEqual(resp_inc.status_code, 400)

    def test_03_login_exitoso_y_fallido(self):
        """2. Inicio de Sesión: POST /login verifica credenciales y permite acceso a las tareas."""
        # Login correcto
        resp = self.app.post("/login", json={"usuario": "juan", "contraseña": "password123"})
        self.assertEqual(resp.status_code, 200)

        # Contraseña incorrecta -> 401
        resp_bad = self.app.post("/login", json={"usuario": "juan", "contraseña": "erronea"})
        self.assertEqual(resp_bad.status_code, 401)

        # Usuario inexistente -> 401
        resp_no_user = self.app.post("/login", json={"usuario": "fantasma", "contraseña": "123"})
        self.assertEqual(resp_no_user.status_code, 401)

    def test_04_proteccion_endpoints_sin_autenticacion(self):
        """Verifica que sin sesión no se permita acceso a las tareas (401)."""
        cliente_anonimo = app.test_client()
        self.assertEqual(cliente_anonimo.get("/tareas").status_code, 401)
        self.assertEqual(cliente_anonimo.post("/tareas", json={"titulo": "Test"}).status_code, 401)
        self.assertEqual(cliente_anonimo.put("/tareas/1/cerrar").status_code, 401)

    def test_05_endpoint_tareas_html_de_bienvenida(self):
        """3. Gestión de Tareas: GET /tareas debe mostrar un HTML de bienvenida cuando se solicita HTML."""
        c = app.test_client()
        c.post("/login", json={"usuario": "juan", "contraseña": "password123"})

        # Petición simulando navegador web (Accept: text/html)
        resp_html = c.get("/tareas", headers={"Accept": "text/html"})
        self.assertEqual(resp_html.status_code, 200)
        cuerpo = resp_html.data.decode("utf-8")
        self.assertIn("<!DOCTYPE html>", cuerpo)
        self.assertIn("¡Bienvenido a tu Sistema de Gestión de Tareas!", cuerpo)
        self.assertIn("juan", cuerpo)

    def test_06_ciclo_completo_tareas_json(self):
        """Gestión de tareas REST en JSON para cliente de consola: crear, listar, cerrar y logout."""
        c = app.test_client()
        c.post("/login", json={"usuario": "juan", "contraseña": "password123"})

        # Crear tarea
        resp_crear = c.post("/tareas", json={"titulo": "Estudiar Flask", "descripcion": "Repasar REST"})
        self.assertEqual(resp_crear.status_code, 201)
        tarea_id = resp_crear.get_json()["id"]
        self.assertEqual(resp_crear.get_json()["estado"], "pendiente")

        # Listar tareas en JSON
        resp_listar = c.get("/tareas", headers={"Accept": "application/json"})
        self.assertEqual(resp_listar.status_code, 200)
        tareas = resp_listar.get_json()
        self.assertTrue(any(t["id"] == tarea_id and t["estado"] == "pendiente" for t in tareas))

        # Cerrar tarea
        resp_cerrar = c.put(f"/tareas/{tarea_id}/cerrar")
        self.assertEqual(resp_cerrar.status_code, 200)
        self.assertEqual(resp_cerrar.get_json()["estado"], "cerrada")

        # Cerrar sesión (logout)
        resp_logout = c.post("/logout")
        self.assertEqual(resp_logout.status_code, 200)

        # Tras logout, no puede listar tareas
        self.assertEqual(c.get("/tareas").status_code, 401)

    def test_07_aislamiento_entre_usuarios(self):
        """Aislamiento: Un usuario no puede ver ni modificar tareas de otro (403 Forbidden)."""
        self.app.post("/registro", json={"usuario": "maria", "contraseña": "clavemaria"})

        # Juan crea tarea
        c_juan = app.test_client()
        c_juan.post("/login", json={"usuario": "juan", "contraseña": "password123"})
        resp_tarea_juan = c_juan.post("/tareas", json={"titulo": "Tarea privada de Juan"})
        id_tarea_juan = resp_tarea_juan.get_json()["id"]

        # María intenta acceder
        c_maria = app.test_client()
        c_maria.post("/login", json={"usuario": "maria", "contraseña": "clavemaria"})
        tareas_maria = c_maria.get("/tareas", headers={"Accept": "application/json"}).get_json()
        self.assertNotIn(id_tarea_juan, [t["id"] for t in tareas_maria])

        # María intenta cerrar la tarea de Juan -> 403 Forbidden
        resp_intento = c_maria.put(f"/tareas/{id_tarea_juan}/cerrar")
        self.assertEqual(resp_intento.status_code, 403)


if __name__ == "__main__":
    unittest.main()
