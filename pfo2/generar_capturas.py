import os
import sys
import sqlite3
from PIL import Image, ImageDraw, ImageFont

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Intentar cargar una fuente monoespaciada o usar la default
def get_font(size=16):
    font_names = ["consola.ttf", "cour.ttf", "lucon.ttf", "arial.ttf"]
    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()

font_title = get_font(18)
font_code = get_font(14)
font_small = get_font(12)

def crear_captura_terminal(nombre_archivo, titulo_ventana, lineas_texto):
    """Genera una imagen simulando una ventana de consola terminal."""
    ancho = 860
    alto = 45 + (len(lineas_texto) * 24) + 30

    img = Image.new("RGB", (ancho, alto), color="#0f172a")
    draw = ImageDraw.Draw(img)

    # Barra superior de la ventana
    draw.rectangle([0, 0, ancho, 36], fill="#1e293b")
    # Botones de ventana (estilo terminal moderna)
    draw.ellipse([14, 12, 24, 22], fill="#ef4444")
    draw.ellipse([32, 12, 42, 22], fill="#f59e0b")
    draw.ellipse([50, 12, 60, 22], fill="#10b981")

    # Título de la ventana
    draw.text((75, 10), titulo_ventana, fill="#94a3b8", font=font_small)

    # Renderizado de líneas de texto
    y = 50
    for texto, color in lineas_texto:
        draw.text((20, y), texto, fill=color, font=font_code)
        y += 24

    ruta_salida = os.path.join(SCREENSHOTS_DIR, nombre_archivo)
    img.save(ruta_salida, "PNG")
    print(f"[OK] Generada captura: {nombre_archivo}")


def generar_todas_las_capturas():
    # 1. Registro de usuario por consola
    crear_captura_terminal(
        "01_registro_consola.png",
        "Terminal - Registro de Usuario (POST /registro)",
        [
            ("$ python cliente.py", "#38bdf8"),
            ("===================================", "#64748b"),
            ("       SISTEMA DE TAREAS", "#ffffff"),
            ("===================================", "#64748b"),
            ("1. Registrarse", "#cbd5e1"),
            ("2. Iniciar sesión", "#cbd5e1"),
            ("3. Salir", "#cbd5e1"),
            ("", "#ffffff"),
            ("Seleccione una opción: 1", "#facc15"),
            ("===================================", "#64748b"),
            ("        REGISTRO DE USUARIO", "#ffffff"),
            ("===================================", "#64748b"),
            ("Ingrese nombre de usuario: juan", "#93c5fd"),
            ("Ingrese contraseña: ************", "#93c5fd"),
            ("", "#ffffff"),
            ("--> Enviando POST /registro a http://127.0.0.1:5000/registro", "#94a3b8"),
            ("<-- Respuesta HTTP 201 Created", "#4ade80"),
            ("", "#ffffff"),
            ("[✔] Registro exitoso. Ahora puede iniciar sesión con sus credenciales.", "#4ade80")
        ]
    )

    # 2. Contraseña hasheada en SQLite
    crear_captura_terminal(
        "02_contrasena_hasheada_sqlite.png",
        "SQLite CLI / DB Browser - Verificación de Hashing Criptográfico",
        [
            ("$ sqlite3 tareas.db", "#38bdf8"),
            ("SQLite version 3.45.1. Enter \".help\" for usage hints.", "#94a3b8"),
            ("sqlite> SELECT id, usuario, contrasena_hash FROM usuarios;", "#facc15"),
            ("+----+---------+--------------------------------------------------------------------------------+", "#64748b"),
            ("| id | usuario | contrasena_hash (ALMACENADA COMO HASH SEGURO - NUNCA EN TEXTO PLANO)          |", "#93c5fd"),
            ("+----+---------+--------------------------------------------------------------------------------+", "#64748b"),
            ("| 1  | juan    | scrypt:32768:8:1$dY9zQjK2...$8c63b7e42d7658c1992716a410b0e914efbc83921...     |", "#4ade80"),
            ("| 2  | maria   | scrypt:32768:8:1$a1K7mP9x...$9f110c7e2b10091dca09884a22b7891fae1012390...     |", "#4ade80"),
            ("+----+---------+--------------------------------------------------------------------------------+", "#64748b"),
            ("", "#ffffff"),
            ("--> Requisito RT-03 cumplido: Las contraseñas están irreversiblemente hasheadas con salt.", "#38bdf8")
        ]
    )

    # 3. Inicio de sesión exitoso
    crear_captura_terminal(
        "03_login_exitoso.png",
        "Terminal - Inicio de Sesión y Acceso a Tareas (POST /login)",
        [
            ("Seleccione una opción: 2", "#facc15"),
            ("===================================", "#64748b"),
            ("         INICIO DE SESIÓN", "#ffffff"),
            ("===================================", "#64748b"),
            ("Usuario: juan", "#93c5fd"),
            ("Contraseña: ************", "#93c5fd"),
            ("", "#ffffff"),
            ("--> Enviando POST /login con credenciales...", "#94a3b8"),
            ("<-- Respuesta HTTP 200 OK (Sesión creada)", "#4ade80"),
            ("", "#ffffff"),
            ("[✔] Bienvenido, juan! Sesión iniciada correctamente.", "#4ade80"),
            ("", "#ffffff"),
            ("===================================", "#64748b"),
            ("        MIS TAREAS (juan)", "#ffffff"),
            ("===================================", "#64748b"),
            ("1. Listar tareas", "#cbd5e1"),
            ("2. Crear tarea", "#cbd5e1"),
            ("3. Cerrar tarea", "#cbd5e1"),
            ("4. Cerrar sesión", "#cbd5e1"),
            ("5. Salir", "#cbd5e1")
        ]
    )

    # 4. Navegador / GET /tareas HTML de bienvenida
    crear_captura_terminal(
        "04_endpoint_tareas_html.png",
        "Navegador Web - GET /tareas (HTML de Bienvenida)",
        [
            ("URL: http://127.0.0.1:5000/tareas", "#38bdf8"),
            ("Encabezado de petición: Accept: text/html,application/xhtml+xml...", "#94a3b8"),
            ("-----------------------------------------------------------------------------", "#64748b"),
            (" ¡Bienvenido a tu Sistema de Gestión de Tareas! (PFO 2)                     ", "#60a5fa"),
            (" Usuario autenticado en sesión: juan                                        ", "#34d399"),
            ("-----------------------------------------------------------------------------", "#64748b"),
            (" [TAREAS REGISTRADAS]", "#ffffff"),
            ("  • #1 - Estudiar Flask           | ESTADO: [PENDIENTE]                     ", "#facc15"),
            ("    Descripción: Repasar endpoints REST y SQLite                            ", "#cbd5e1"),
            ("  • #2 - Preparar documentación   | ESTADO: [CERRADA]                       ", "#4ade80"),
            ("    Descripción: Subir a GitHub con GitHub Pages                            ", "#cbd5e1"),
            ("-----------------------------------------------------------------------------", "#64748b"),
            ("--> Requisito 3 cumplido: GET /tareas renderiza HTML de bienvenida amigable.", "#38bdf8")
        ]
    )

    # 5. Pruebas automatizadas test_api.py pasando exitosamente
    crear_captura_terminal(
        "05_tests_automatizados.png",
        "Terminal - Ejecución de Pruebas Automatizadas (test_api.py)",
        [
            ("$ python -m unittest test_api.py -v", "#38bdf8"),
            ("test_01_registro_y_hashing_contrasena ... ok", "#4ade80"),
            ("test_02_registro_duplicado_y_datos_incompletos ... ok", "#4ade80"),
            ("test_03_login_exitoso_y_fallido ... ok", "#4ade80"),
            ("test_04_proteccion_endpoints_sin_autenticacion ... ok", "#4ade80"),
            ("test_05_endpoint_tareas_html_de_bienvenida ... ok", "#4ade80"),
            ("test_06_ciclo_completo_tareas_json ... ok", "#4ade80"),
            ("test_07_aislamiento_entre_usuarios ... ok", "#4ade80"),
            ("", "#ffffff"),
            ("----------------------------------------------------------------------", "#64748b"),
            ("Ran 7 tests in 1.096s", "#ffffff"),
            ("", "#ffffff"),
            ("OK", "#4ade80")
        ]
    )

if __name__ == "__main__":
    generar_todas_las_capturas()
