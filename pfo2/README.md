# Sistema de Chat Cliente-Servidor con Sockets y Persistencia SQLite

**Materia:** Programación de Redes  
**Proyecto:** Chat Básico Cliente-Servidor con Asignación de Identificador y Persistencia en SQLite  

---

## 🎯 Objetivo del Programa

Aprender a configurar un servidor de sockets en Python que:
1. **Reciba mensajes** de múltiples clientes a través de sockets TCP/IP.
2. **Asigne un identificador único** a cada cliente en el momento en que se conecta (ej. `Cliente-1`, `Cliente-2`).
3. **Almacene cada mensaje** de forma persistente en una base de datos **SQLite**.
4. **Envíe confirmaciones (acuses de recibo)** al cliente con el ID del mensaje guardado y la fecha/hora.
5. **Aplique buenas prácticas** de modularización, concurrencia multihilo y manejo exhaustivo de errores (desconexiones abruptas, liberación de sockets, apagado limpio con Ctrl+C).
6. **Explique mediante comentarios en el código** cada una de las configuraciones del socket y del servidor.

---

## 📁 Estructura del Directorio

```text
pfo2/
├── servidor.py          # Servidor de sockets TCP multihilo + Persistencia SQLite
├── cliente.py           # Cliente interactivo de consola por sockets
├── test_chat.py         # Suite de pruebas que verifica la especificación OpenSpec
├── README.md            # Documentación completa del proyecto
├── OpenSpec.md          # Especificación formal del trabajo práctico
├── mensajes.db          # Base de datos SQLite (generada automáticamente)
├── docs/
│   └── index.html       # Presentación web del proyecto (apta para GitHub Pages)
└── screenshots/
    └── README.md        # Guía para capturas de pantalla de pruebas
```

---

## ⚙️ Explicación de las Configuraciones del Servidor

En [`servidor.py`](servidor.py) se incluyen comentarios detallados explicando cada paso de la configuración:

### 1. Creación del Socket TCP:
```python
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
```
- `socket.AF_INET`: Define la familia de direcciones **IPv4**.
- `socket.SOCK_STREAM`: Establece el protocolo **TCP**, garantizando entrega ordenada, libre de errores y orientada a la conexión.

### 2. Reutilización Inmediata del Puerto:
```python
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
```
- Evita el error habitual `[Errno 98/10048] Address already in use` cuando el servidor se reinicia rápidamente y el puerto queda temporalmente en estado `TIME_WAIT`.

### 3. Vinculación (`bind`):
```python
server_socket.bind((HOST, PORT))
```
- Asocia el socket a la interfaz de red local (`127.0.0.1`) y al puerto elegido (`5000`).

### 4. Modo de Escucha (`listen`):
```python
server_socket.listen(10)
```
- Pone el socket en estado pasivo para aceptar conexiones. El número `10` es el *backlog*, indicando la cantidad máxima de conexiones en cola antes de ser aceptadas.

### 5. Manejo Concurrente con Hilos (`threading.Thread`):
- Cuando un cliente se conecta mediante `accept()`, se le asigna un identificador secuencial protegido con un `threading.Lock()` (`Cliente-1`, `Cliente-2`).
- La atención de cada cliente se delega a un hilo independiente (`threading.Thread`), permitiendo que **múltiples clientes se comuniquen simultáneamente sin bloquear la cola de conexiones**.

### 6. Persistencia en SQLite Multihilo:
- Cada hilo abre y cierra su propia conexión a `mensajes.db` mediante `sqlite3.connect()`. Esto respeta las reglas de SQLite evitando conflictos entre hilos concurrentes.

---

## 🗄️ Esquema de la Base de Datos SQLite (`mensajes.db`)

Tabla **`mensajes`**:

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Identificador único del mensaje |
| `id_cliente` | `TEXT NOT NULL` | Identificador asignado (ej. `Cliente-1`) |
| `contenido` | `TEXT NOT NULL` | Texto del mensaje enviado |
| `fecha_envio` | `TEXT NOT NULL` | Timestamp exacto (`YYYY-MM-DD HH:MM:SS`) |
| `ip_cliente` | `TEXT NOT NULL` | Dirección IP de origen |
| `puerto_cliente` | `INTEGER NOT NULL` | Puerto efímero desde el que se conectó |

---

## 🚀 Instrucciones de Ejecución y Pruebas

### 1. Iniciar el Servidor
Abre una terminal y ejecuta:
```bash
python servidor.py
```
El servidor mostrará:
```text
=================================================================
 SERVIDOR DE CHAT CON PERSISTENCIA EN SQLITE INICIADO
 Escuchando en: 127.0.0.1:5000
 Base de datos: mensajes.db
 Presione Ctrl+C en cualquier momento para detener el servidor.
=================================================================
```

### 2. Conectar Clientes (puedes abrir múltiples terminales simultáneas)
En una segunda terminal:
```bash
python cliente.py
```
El cliente recibirá su identificador automáticamente:
```text
[✔] ¡Conexión exitosa!
    -> Identificador asignado: Cliente-1
    -> Mensaje del servidor: Bienvenido al servidor de chat.

[Cliente-1] Vos: Hola servidor
  [✔ Servidor]: Mensaje guardado con éxito [ID #1] en base de datos a las 2026-10-07 19:08:03.
```

Si abres una tercera terminal y ejecutas `python cliente.py`:
```text
[✔] ¡Conexión exitosa!
    -> Identificador asignado: Cliente-2
...
```

Para salir de un cliente de forma ordenada, escribe:
`salir` o `éxito`.

### 3. Ejecutar Pruebas Automatizadas
Para verificar de forma automática la creación de tablas, la concurrencia multihilo, la asignación de IDs y la persistencia en base de datos:
```bash
python test_chat.py
```

---

## 💡 Respuestas Conceptuales

### 1. ¿Por qué hashear contraseñas?
Aunque este módulo de chat se enfoca en comunicación directa por sockets sin autenticación previa, en cualquier sistema que involucre usuarios:
- **Almacenar contraseñas en texto plano es una vulnerabilidad crítica**. Si la base de datos es expuesta (brechas de seguridad, respaldos desprotegidos), los atacantes comprometen todas las cuentas inmediatamente.
- **Irreversibilidad:** El hash criptográfico es una función matemática de un solo sentido (no se puede recuperar la contraseña a partir del hash).
- **Salting:** Añadir un valor aleatorio único (*salt*) a cada contraseña antes de hashearla evita ataques de tablas arcoíris (*Rainbow Tables*) e impide que dos usuarios con la misma contraseña generen el mismo hash.
- **Factor de costo:** Algoritmos como `scrypt`, `bcrypt` o `PBKDF2` consumen tiempo y memoria intencionalmente para frustrar ataques de fuerza bruta masivos.

### 2. Ventajas de usar SQLite en este proyecto
- **Serverless (Sin Servidor):** No requiere instalar ni administrar ningún software o daemon de base de datos externo (como PostgreSQL o MySQL). La base de datos es manejada directamente por la biblioteca estándar de Python.
- **Autocontenido y Portable:** Toda la base de datos se guarda en un único archivo físico (`mensajes.db`), lo que permite respaldar, transportar y revisar las entregas sin depender de configuraciones de red o servicios adicionales.
- **Cero Configuración:** No requiere creación de usuarios de base de datos, contraseñas ni permisos del sistema.
- **Transacciones ACID:** Garantiza atomicidad, consistencia, aislamiento y durabilidad en cada mensaje registrado.
- **Nativo en Python:** Incluido en la biblioteca estándar a través de `import sqlite3`.

---

## 🌐 Publicación en GitHub y GitHub Pages

```bash
git add pfo2/
git commit -m "Entrega PFO 2: Servidor y cliente de chat con sockets y SQLite"
git push origin main
```
Para activar GitHub Pages con la presentación del proyecto en `docs/index.html`:
1. Ir al repositorio en GitHub -> **Settings** -> **Pages**.
2. En **Branch**, seleccionar `main` y la carpeta `/docs` (o `/root`).
3. Guardar cambios.
