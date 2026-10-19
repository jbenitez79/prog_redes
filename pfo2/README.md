# Sistema de Gestión de Tareas con API REST y Base de Datos (PFO 2)

**Materia:** Programación de Redes  
**Proyecto:** PFO 2 — Sistema de Gestión de Tareas con API REST, Autenticación, Hashing y SQLite  

---

## 📌 Objetivo

Al finalizar este trabajo práctico, se demuestra la capacidad de:
1. **Implementar una API REST** con endpoints funcionales mediante **Flask**.
2. **Utilizar autenticación** con protección criptográfica de contraseñas mediante hashing.
3. **Gestionar datos persistentes** utilizando **SQLite** (`tareas.db`).
4. **Construir un cliente de consola** interactivo que consuma la API REST vía HTTP.
5. **Proporcionar un HTML de bienvenida** en el endpoint `GET /tareas`.

---

## 📁 Estructura del Proyecto

```text
pfo2/
├── servidor.py            # API REST desarrollada en Flask con SQLite y Werkzeug Security
├── cliente.py             # Cliente interactivo de consola (consume la API REST vía HTTP)
├── test_api.py            # Suite de pruebas automatizadas con unittest (7 tests)
├── generar_capturas.py    # Script para generar automáticamente las capturas PNG
├── tareas.db              # Base de datos SQLite (se genera automáticamente)
├── requirements.txt       # Dependencias del proyecto
├── README.md              # Documentación principal e instrucciones
├── OpenSpec.md            # Especificación funcional y técnica
├── docs/
│   └── index.html         # Sitio web para publicación en GitHub Pages
└── screenshots/           # Capturas de pantalla de pruebas exitosas (E-04)
    ├── 01_registro_consola.png
    ├── 02_contrasena_hasheada_sqlite.png
    ├── 03_login_exitoso.png
    ├── 04_endpoint_tareas_html.png
    ├── 05_tests_automatizados.png
    └── README.md
```

---

## 🛠️ Requisitos Previos e Instalación

1. **Python 3.8 o superior** (probado en Python 3.13).
2. Clonar o descargar el repositorio.
3. Instalar las dependencias del proyecto:
   ```bash
   pip install -r requirements.txt
   ```

*Contenido de `requirements.txt`:*
- `Flask>=3.0.0`
- `Werkzeug>=3.0.0`
- `requests>=2.31.0`
- `pillow>=10.0.0` (opcional, para regenerar imágenes de capturas)

---

## 🌐 Endpoints de la API REST (`servidor.py`)

| Método | Endpoint | Autenticación | Código Éxito | Descripción |
| :--- | :--- | :---: | :---: | :--- |
| `POST` | `/registro` | No | `201 Created` | Recibe `{"usuario": "...", "contraseña": "..."}` y almacena el hash. |
| `POST` | `/login` | No | `200 OK` | Verifica credenciales y crea la sesión autenticada. |
| `GET` | `/tareas` | Sí | `200 OK` | **Navegador web:** Muestra el **HTML de bienvenida** con panel de tareas.<br>**Cliente API:** Retorna array JSON de tareas del usuario. |
| `POST` | `/tareas` | Sí | `201 Created` | Crea tarea con estado inicial `pendiente`. |
| `PUT` | `/tareas/<id>/cerrar` | Sí | `200 OK` | Actualiza la tarea a estado `cerrada`. Valida propiedad (`403` si es ajena). |
| `POST` | `/logout` | Sí | `200 OK` | Invalida la sesión autenticada. |

---

## 🚀 Instrucciones de Ejecución

### 1. Iniciar el Servidor API Flask (Terminal 1)
```bash
python servidor.py
```
Salida en consola:
```text
Iniciando API Flask en http://127.0.0.1:5000
 * Running on http://127.0.0.1:5000
```

### 2. Iniciar el Cliente de Consola (Terminal 2)
```bash
python cliente.py
```

Flujo interactivo:
1. Seleccionar opción **1. Registrarse** e ingresar usuario y contraseña.
2. Seleccionar opción **2. Iniciar sesión** con las credenciales registradas.
3. Acceder al menú autenticado:
   - **1. Listar tareas**
   - **2. Crear tarea** (inicia en `pendiente`)
   - **3. Cerrar tarea** (pasa a `cerrada`)
   - **4. Cerrar sesión**
   - **5. Salir**

### 3. Visualizar el HTML de Bienvenida en el Navegador
Con el servidor encendido y tras haber iniciado sesión en el navegador (o probando con la cookie de sesión), ingresa a:
```text
http://127.0.0.1:5000/tareas
```
Se desplegará una pantalla de bienvenida moderna y estilizada indicando el usuario conectado y sus tareas.

---

## 🧪 Pruebas Automatizadas

Ejecuta la suite oficial de pruebas de integración:
```bash
python -m unittest test_api.py -v
```

Salida esperada:
```text
test_01_registro_y_hashing_contrasena ... ok
test_02_registro_duplicado_y_datos_incompletos ... ok
test_03_login_exitoso_y_fallido ... ok
test_04_proteccion_endpoints_sin_autenticacion ... ok
test_05_endpoint_tareas_html_de_bienvenida ... ok
test_06_ciclo_completo_tareas_json ... ok
test_07_aislamiento_entre_usuarios ... ok

Ran 7 tests in 1.096s

OK
```

---

## 📷 Evidencias de Pruebas (Capturas de Pantalla)

En la carpeta [`screenshots/`](screenshots/) se incluyen las capturas requeridas por el enunciado:
- `01_registro_consola.png`: Registro de usuario en cliente interactivo.
- `02_contrasena_hasheada_sqlite.png`: Verificación del hash criptográfico en `tareas.db`.
- `03_login_exitoso.png`: Inicio de sesión exitoso.
- `04_endpoint_tareas_html.png`: Pantalla de bienvenida HTML al acceder a `GET /tareas`.
- `05_tests_automatizados.png`: Ejecución limpia y exitosa de `test_api.py`.

---

## 🌐 Publicación en GitHub y GitHub Pages

El proyecto incluye la carpeta [`docs/index.html`](docs/index.html) lista para ser publicada en **GitHub Pages**:
1. Hacer push del repositorio a GitHub:
   ```bash
   git add .
   git commit -m "Entrega PFO 2: Sistema de Gestión de Tareas con API y SQLite"
   git push origin main
   ```
2. En GitHub: ir a **Settings** -> **Pages**.
3. En **Build and deployment**: seleccionar **Deploy from a branch**, rama `main`, carpeta `/docs`.

---

## 💡 Respuestas Conceptuales

### 1. ¿Por qué hashear contraseñas?
- **Protección contra filtraciones y accesos no autorizados:** Almacenar contraseñas en texto plano es una de las vulnerabilidades más severas en el desarrollo de software. Si un atacante accede a la base de datos (por inyección SQL, acceso indebido o backup filtrado), no obtiene las credenciales reales.
- **Principio de irreversibilidad:** Las funciones de hashing criptográfico son unidireccionales: es matemáticamente inviable calcular la contraseña original a partir del hash generado.
- **Salting (Sal aleatoria):** Algoritmos modernos como `scrypt` o `pbkdf2` (usados mediante `werkzeug.security`) agregan una sal aleatoria a cada contraseña. Esto previene ataques basados en tablas precalculadas (*rainbow tables*) y garantiza que dos usuarios con la misma contraseña posean hashes completamente distintos.
- **Ralentización intencional (Factor de costo):** A diferencia de algoritmos rápidos como MD5 o SHA-1, las funciones de derivación de claves para contraseñas consumen tiempo y memoria controlados, mitigando los ataques por fuerza bruta masiva con hardware acelerado (GPU/ASIC).

### 2. ¿Cuáles son las ventajas de usar SQLite en este proyecto?
- **Serverless (Sin demonio externo):** SQLite no es un servidor separado que necesite procesos en background, administración de servicios o sockets de red adicionales; el motor de base de datos se ejecuta directamente dentro del intérprete de Python mediante la biblioteca estándar (`sqlite3`).
- **Autocontenido y máxima portabilidad:** Toda la información (esquema, tablas de usuarios y tareas) se guarda en un único archivo físico (`tareas.db`). Esto permite mover, clonar o calificar el proyecto en cualquier máquina sin necesidad de configurar conexiones complejas.
- **Cero configuración:** No requiere crear usuarios de base de datos, contraseñas de conexión, definir puertos ni conceder privilegios a nivel de sistema gestor.
- **Conformidad con transacciones ACID:** Garantiza integridad transaccional (Atomicidad, Consistencia, Aislamiento y Durabilidad) en operaciones de registro, creación y cambio de estado de tareas.
- **Estabilidad e integración nativa:** No requiere dependencias de terceros para interactuar con la base de datos, lo que minimiza la superficie de fallas del proyecto.
