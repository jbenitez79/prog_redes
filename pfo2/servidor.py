import os
import sqlite3
from flask import Flask, request, jsonify, session, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================================================================
# Configuración del servidor y base de datos
# ==============================================================================
app = Flask(__name__)
# Clave secreta necesaria para firmar y mantener las sesiones seguras en cookies
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_pfo2_progredes_key_2026")

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tareas.db")


# ==============================================================================
# Inicialización de SQLite
# ==============================================================================
def obtener_conexion():
    """Retorna una conexión a la base de datos SQLite con soporte para acceso por nombres de columnas."""
    conn = sqlite3.connect(DB_NAME, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db():
    """
    Crea las tablas de usuarios y tareas si no existen:
    - usuarios: id, usuario (único), contrasena_hash
    - tareas: id, usuario_id, titulo, descripcion, estado ('pendiente' o 'cerrada')
    """
    conn = obtener_conexion()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            contrasena_hash TEXT NOT NULL
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        );
    ''')

    conn.commit()
    conn.close()


# ==============================================================================
# Decorador o función de verificación de sesión
# ==============================================================================
def obtener_usuario_autenticado():
    """Retorna el usuario_id de la sesión activa si existe, o None si no está autenticado."""
    return session.get("usuario_id")


# ==============================================================================
# Endpoints de la API REST
# ==============================================================================

@app.route("/", methods=["GET"])
def index():
    """Endpoint informativo de bienvenida."""
    return jsonify({
        "mensaje": "API REST - Sistema de Gestión de Tareas (PFO 2)",
        "estado": "activo",
        "endpoints": [
            "POST /registro",
            "POST /login",
            "GET  /tareas",
            "POST /tareas",
            "PUT  /tareas/<id>/cerrar",
            "POST /logout"
        ]
    }), 200


@app.route("/registro", methods=["POST"])
def registro():
    """
    RF-01 — Registro de usuario
    Recibe JSON: {"usuario": "...", "contraseña": "..."} o {"contrasena": "..."}
    Guarda la contraseña protegida con hash criptográfico.
    """
    datos = request.get_json(silent=True)
    if not datos:
        return jsonify({"error": "Formato JSON inválido o faltante."}), 400

    nombre_usuario = datos.get("usuario")
    password = datos.get("contraseña") or datos.get("contrasena")

    if not nombre_usuario or not password:
        return jsonify({"error": "Los campos 'usuario' y 'contraseña' son obligatorios."}), 400

    nombre_usuario = str(nombre_usuario).strip()
    if not nombre_usuario:
        return jsonify({"error": "El nombre de usuario no puede estar vacío."}), 400

    # Hashing seguro de la contraseña usando pbkdf2/scrypt provisto por Werkzeug
    contrasena_hash = generate_password_hash(str(password))

    conn = obtener_conexion()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuarios (usuario, contrasena_hash) VALUES (?, ?)",
            (nombre_usuario, contrasena_hash)
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
        return jsonify({
            "mensaje": "Usuario registrado exitosamente.",
            "id": nuevo_id,
            "usuario": nombre_usuario
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": f"El usuario '{nombre_usuario}' ya se encuentra registrado."}), 400
    except Exception as e:
        return jsonify({"error": f"Error interno al registrar usuario: {str(e)}"}), 500
    finally:
        conn.close()


@app.route("/login", methods=["POST"])
def login():
    """
    RF-02 — Inicio de sesión
    Recibe JSON: {"usuario": "...", "contraseña": "..."}
    Valida credenciales y establece la sesión autenticada.
    """
    datos = request.get_json(silent=True)
    if not datos:
        return jsonify({"error": "Formato JSON inválido o faltante."}), 400

    nombre_usuario = datos.get("usuario")
    password = datos.get("contraseña") or datos.get("contrasena")

    if not nombre_usuario or not password:
        return jsonify({"error": "Los campos 'usuario' y 'contraseña' son obligatorios."}), 400

    nombre_usuario = str(nombre_usuario).strip()

    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id, usuario, contrasena_hash FROM usuarios WHERE usuario = ?", (nombre_usuario,))
    usuario_db = cursor.fetchone()
    conn.close()

    # Usuario inexistente -> 401 Unauthorized
    if not usuario_db:
        return jsonify({"error": "Credenciales inválidas: usuario no encontrado."}), 401

    # Contraseña incorrecta -> 401 Unauthorized
    if not check_password_hash(usuario_db["contrasena_hash"], str(password)):
        return jsonify({"error": "Credenciales inválidas: contraseña incorrecta."}), 401

    # Iniciar sesión en el servidor
    session["usuario_id"] = usuario_db["id"]
    session["usuario"] = usuario_db["usuario"]

    return jsonify({
        "mensaje": "Inicio de sesión exitoso.",
        "usuario": usuario_db["usuario"]
    }), 200


HTML_BIENVENIDA_TAREAS = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bienvenido - Panel de Tareas</title>
    <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --badge-pendiente: #f59e0b;
            --badge-cerrada: #10b981;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
        }
        .container {
            width: 100%;
            max-width: 800px;
        }
        .welcome-card {
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 32px;
            margin-bottom: 24px;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);
            text-align: center;
        }
        .welcome-card h1 {
            font-size: 2rem;
            color: #60a5fa;
            margin-bottom: 8px;
        }
        .welcome-card p {
            color: var(--text-muted);
            font-size: 1.1rem;
        }
        .user-tag {
            display: inline-block;
            background: rgba(37, 99, 235, 0.2);
            color: #93c5fd;
            border: 1px solid #3b82f6;
            padding: 4px 12px;
            border-radius: 9999px;
            margin-top: 12px;
            font-weight: 600;
        }
        .section-title {
            font-size: 1.3rem;
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .task-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .task-card {
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .task-info h3 {
            font-size: 1.1rem;
            margin-bottom: 4px;
        }
        .task-info p {
            font-size: 0.9rem;
            color: var(--text-muted);
        }
        .badge {
            font-size: 0.8rem;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 9999px;
            text-transform: uppercase;
        }
        .badge.pendiente {
            background-color: rgba(245, 158, 11, 0.2);
            color: var(--badge-pendiente);
            border: 1px solid var(--badge-pendiente);
        }
        .badge.cerrada {
            background-color: rgba(16, 185, 129, 0.2);
            color: var(--badge-cerrada);
            border: 1px solid var(--badge-cerrada);
        }
        .empty-tasks {
            text-align: center;
            padding: 30px;
            color: var(--text-muted);
            background: var(--card-bg);
            border-radius: 8px;
            border: 1px dashed var(--border);
        }
        .footer-note {
            margin-top: 30px;
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="welcome-card">
            <h1>¡Bienvenido a tu Sistema de Gestión de Tareas!</h1>
            <p>API REST y Base de Datos SQLite (PFO 2 - Programación de Redes)</p>
            <div class="user-tag">Usuario conectado: {{ usuario }}</div>
        </div>

        <div class="section-title">
            <h2>Tus Tareas Registradas</h2>
            <span style="font-size: 0.9rem; color: var(--text-muted);">Total: {{ tareas|length }}</span>
        </div>

        {% if tareas %}
        <ul class="task-list">
            {% for t in tareas %}
            <li class="task-card">
                <div class="task-info">
                    <h3>#{{ t.id }} - {{ t.titulo }}</h3>
                    {% if t.descripcion %}
                    <p>{{ t.descripcion }}</p>
                    {% endif %}
                </div>
                <span class="badge {{ t.estado }}">{{ t.estado }}</span>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <div class="empty-tasks">
            <p>No tienes tareas registradas actualmente. Puedes crear una desde el cliente de consola o enviando un POST a /tareas.</p>
        </div>
        {% endif %}

        <div class="footer-note">
            Endpoint <code>GET /tareas</code> renderizando HTML de bienvenida según la especificación oficial.
        </div>
    </div>
</body>
</html>
"""


@app.route("/tareas", methods=["GET"])
def listar_tareas():
    """
    3. Gestión de Tareas:
    - GET /tareas: Muestre un html de bienvenida (Requisito explícito del PDF).
    
    Implementa negociación de contenido:
    - Si el cliente solicita HTML (por ejemplo, desde navegador web): renderiza el HTML de bienvenida.
    - Si el cliente solicita JSON (o cliente REST/consola): retorna la lista de tareas en formato JSON.
    """
    usuario_id = obtener_usuario_autenticado()
    nombre_usuario = session.get("usuario", "Usuario")

    # Si no está autenticado
    if not usuario_id:
        if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
            return """
            <!DOCTYPE html>
            <html lang="es">
            <head><meta charset="UTF-8"><title>Acceso Requerido</title>
            <style>body{font-family:sans-serif;background:#0f172a;color:#f8fafc;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}
            .card{background:#1e293b;padding:30px;border-radius:10px;text-align:center;box-shadow:0 4px 6px rgba(0,0,0,0.3);}</style>
            </head>
            <body>
            <div class="card">
                <h2>Inicio de Sesión Requerido</h2>
                <p style="color:#94a3b8;margin-top:10px;">Debes autenticarte previamente a través del cliente de consola o mediante <code>POST /login</code>.</p>
            </div>
            </body></html>
            """, 401
        return jsonify({"error": "No autorizado. Inicie sesión para acceder a las tareas."}), 401

    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, titulo, descripcion, estado FROM tareas WHERE usuario_id = ? ORDER BY id ASC",
        (usuario_id,)
    )
    filas = cursor.fetchall()
    conn.close()

    tareas = [
        {
            "id": f["id"],
            "titulo": f["titulo"],
            "descripcion": f["descripcion"],
            "estado": f["estado"]
        }
        for f in filas
    ]

    # Negociación de contenido:
    # Si la petición prefiere HTML (ej. navegador web), renderizar el HTML de bienvenida
    if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
        return render_template_string(HTML_BIENVENIDA_TAREAS, usuario=nombre_usuario, tareas=tareas), 200

    # Por defecto para APIs y clientes de consola: JSON
    return jsonify(tareas), 200


@app.route("/tareas", methods=["POST"])
def crear_tarea():
    """
    RF-04 — Crear tarea
    Recibe JSON: {"titulo": "...", "descripcion": "..."}
    Crea la tarea asociada al usuario autenticado con estado 'pendiente'.
    """
    usuario_id = obtener_usuario_autenticado()
    if not usuario_id:
        return jsonify({"error": "No autorizado. Inicie sesión para crear tareas."}), 401

    datos = request.get_json(silent=True)
    if not datos:
        return jsonify({"error": "Formato JSON inválido o faltante."}), 400

    titulo = datos.get("titulo")
    descripcion = datos.get("descripcion", "")

    if not titulo or not str(titulo).strip():
        return jsonify({"error": "El título de la tarea es obligatorio."}), 400

    titulo = str(titulo).strip()
    descripcion = str(descripcion).strip()

    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tareas (usuario_id, titulo, descripcion, estado) VALUES (?, ?, ?, 'pendiente')",
        (usuario_id, titulo, descripcion)
    )
    conn.commit()
    nueva_tarea_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "mensaje": "Tarea creada exitosamente.",
        "id": nueva_tarea_id,
        "titulo": titulo,
        "descripcion": descripcion,
        "estado": "pendiente"
    }), 201


@app.route("/tareas/<int:tarea_id>/cerrar", methods=["PUT"])
def cerrar_tarea(tarea_id):
    """
    RF-05 — Cerrar tarea
    Actualiza el estado de la tarea a 'cerrada'.
    Valida pertenencia (403 si pertenece a otro usuario) o existencia (404).
    """
    usuario_id = obtener_usuario_autenticado()
    if not usuario_id:
        return jsonify({"error": "No autorizado. Inicie sesión para cerrar tareas."}), 401

    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id, usuario_id, estado FROM tareas WHERE id = ?", (tarea_id,))
    tarea = cursor.fetchone()

    if not tarea:
        conn.close()
        return jsonify({"error": f"La tarea con ID {tarea_id} no existe."}), 404

    # Verificar que pertenezca al usuario autenticado
    if tarea["usuario_id"] != usuario_id:
        conn.close()
        return jsonify({"error": "Acceso denegado: la tarea pertenece a otro usuario."}), 403

    cursor.execute("UPDATE tareas SET estado = 'cerrada' WHERE id = ?", (tarea_id,))
    conn.commit()
    conn.close()

    return jsonify({
        "mensaje": "Tarea cerrada exitosamente.",
        "id": tarea_id,
        "estado": "cerrada"
    }), 200


@app.route("/logout", methods=["POST"])
def logout():
    """
    RF-06 — Cerrar sesión
    Invalida la sesión autenticada del usuario.
    """
    usuario_id = obtener_usuario_autenticado()
    if not usuario_id:
        return jsonify({"error": "No hay una sesión activa."}), 401

    session.clear()
    return jsonify({"mensaje": "Sesión cerrada correctamente."}), 200


# ==============================================================================
# Ejecución principal
# ==============================================================================
if __name__ == "__main__":
    inicializar_db()
    print("Iniciando API Flask en http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
