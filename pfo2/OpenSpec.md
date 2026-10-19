# OpenSpec — PFO 2: Sistema de Gestión de Tareas con API y Base de Datos

## 1. Nombre de la iniciativa

**Sistema de Gestión de Tareas con API y Base de Datos**

## 2. Objetivo

Desarrollar una aplicación cliente-servidor que permita a un usuario registrarse, iniciar sesión y gestionar sus tareas mediante una API REST desarrollada con Flask.

La aplicación deberá utilizar SQLite para la persistencia de usuarios y tareas, proteger las contraseñas mediante hashing y proporcionar un cliente de consola desde el cual el usuario pueda interactuar con el sistema.

El flujo principal será:

```text
Registro
   ↓
Inicio de sesión
   ↓
Menú de tareas
   ├── Listar tareas
   ├── Crear tarea
   ├── Cerrar tarea
   ├── Cerrar sesión
   └── Salir
```

---

# 3. Alcance

La solución deberá contemplar:

* Registro de usuarios.
* Inicio de sesión.
* Protección de contraseñas mediante hashing.
* Persistencia mediante SQLite.
* Creación de tareas.
* Listado de tareas.
* Cierre de tareas.
* Cierre de sesión.
* Salida del cliente de consola.
* API REST desarrollada con Flask.
* Cliente de consola que consuma la API.
* Documentación de instalación, ejecución y pruebas.
* Capturas de pantalla de pruebas exitosas.
* Publicación del proyecto en GitHub.
* Uso de GitHub Pages para alojar el proyecto.

El enunciado original establece como objetivos implementar una API REST, autenticación con protección de contraseñas, persistencia SQLite y un cliente de consola.

---

# 4. Arquitectura

```text
┌──────────────────────────┐
│    Cliente de consola    │
│                          │
│  1. Registrarse          │
│  2. Iniciar sesión       │
│  3. Listar tareas        │
│  4. Crear tarea          │
│  5. Cerrar tarea         │
│  6. Cerrar sesión        │
│  7. Salir                │
└────────────┬─────────────┘
             │ HTTP / JSON
             ▼
┌──────────────────────────┐
│        API Flask         │
├──────────────────────────┤
│ POST /registro           │
│ POST /login              │
│ GET  /tareas             │
│ POST /tareas              │
│ PUT  /tareas/<id>/cerrar │
│ POST /logout              │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│          SQLite          │
├──────────────────────────┤
│ usuarios                 │
│ tareas                   │
└──────────────────────────┘
```

---

# 5. Modelo de datos

## 5.1 Usuario

La aplicación deberá almacenar como mínimo:

```text
Usuario
├── id
├── usuario
└── contraseña_hash
```

La contraseña original nunca deberá almacenarse en texto plano.

## 5.2 Tarea

Cada tarea deberá estar asociada a un usuario.

Estructura propuesta:

```text
Tarea
├── id
├── usuario_id
├── titulo
├── descripcion
└── estado
```

El campo `estado` deberá permitir diferenciar al menos:

```text
pendiente
cerrada
```

La relación entre usuario y tarea permitirá que cada usuario consulte y gestione únicamente sus propias tareas.

---

# 6. Requerimientos funcionales

## RF-01 — Registro de usuario

El sistema deberá permitir crear un usuario mediante:

```http
POST /registro
```

### Request

```json
{
  "usuario": "nombre",
  "contraseña": "1234"
}
```

### Reglas

* `usuario` es obligatorio.
* `contraseña` es obligatoria.
* La contraseña deberá ser hasheada antes de almacenarse.
* El usuario deberá persistirse en SQLite.
* No se deberá almacenar la contraseña original.

El formato de registro y el requisito de utilizar contraseñas hasheadas están definidos en el enunciado original.

---

# 7. RF-02 — Inicio de sesión

El sistema deberá permitir iniciar sesión mediante:

```http
POST /login
```

### Request

```json
{
  "usuario": "nombre",
  "contraseña": "1234"
}
```

### Comportamiento

El servidor deberá:

1. Buscar el usuario.
2. Verificar la contraseña contra el hash almacenado.
3. Crear una sesión autenticada.
4. Permitir al usuario acceder a sus tareas.

El requisito original establece que `/login` debe verificar las credenciales y permitir el acceso a las tareas.

---

# 8. RF-03 — Listar tareas

El usuario autenticado deberá poder consultar sus tareas mediante:

```http
GET /tareas
```

### Comportamiento

El endpoint deberá devolver las tareas pertenecientes al usuario autenticado.

Ejemplo:

```json
[
  {
    "id": 1,
    "titulo": "Estudiar Flask",
    "descripcion": "Repasar endpoints REST",
    "estado": "pendiente"
  },
  {
    "id": 2,
    "titulo": "Preparar README",
    "descripcion": "Documentar instalación",
    "estado": "cerrada"
  }
]
```

### Reglas

* Solo podrán consultarse tareas del usuario autenticado.
* Las tareas deberán recuperarse desde SQLite.
* El usuario no podrá acceder a tareas pertenecientes a otros usuarios.

---

# 9. RF-04 — Crear tarea

El usuario autenticado deberá poder crear una nueva tarea mediante:

```http
POST /tareas
```

### Request

```json
{
  "titulo": "Estudiar Flask",
  "descripcion": "Repasar endpoints REST"
}
```

### Comportamiento

El sistema deberá:

1. Validar que exista una sesión autenticada.
2. Recibir los datos de la tarea.
3. Asociar la tarea al usuario autenticado.
4. Crear la tarea con estado `pendiente`.
5. Persistirla en SQLite.

### Criterio de aceptación

Una tarea creada deberá aparecer posteriormente al ejecutar:

```http
GET /tareas
```

---

# 10. RF-05 — Cerrar tarea

El usuario autenticado deberá poder marcar una tarea como cerrada mediante:

```http
PUT /tareas/<id>/cerrar
```

Ejemplo:

```http
PUT /tareas/1/cerrar
```

### Comportamiento

El sistema deberá:

1. Verificar que exista una sesión autenticada.
2. Buscar la tarea indicada.
3. Verificar que la tarea pertenezca al usuario autenticado.
4. Cambiar su estado a `cerrada`.
5. Persistir el cambio en SQLite.

### Criterio de aceptación

Después de cerrar una tarea, al listar las tareas deberá aparecer:

```json
{
  "id": 1,
  "estado": "cerrada"
}
```

---

# 11. RF-06 — Cerrar sesión

El usuario deberá poder cerrar su sesión mediante:

```http
POST /logout
```

### Comportamiento

El servidor deberá invalidar la sesión autenticada.

Después del logout:

* El usuario no deberá poder listar tareas.
* El usuario no deberá poder crear tareas.
* El usuario no deberá poder cerrar tareas.
* El cliente deberá regresar al menú de usuario no autenticado.

---

# 12. RF-07 — Salir del cliente

El cliente de consola deberá ofrecer una opción para finalizar completamente la aplicación.

Ejemplo:

```text
=========================
 SISTEMA DE TAREAS
=========================

1. Listar tareas
2. Crear tarea
3. Cerrar tarea
4. Cerrar sesión
5. Salir

Seleccione una opción:
```

La opción **Salir** deberá finalizar la ejecución del cliente.

Esta funcionalidad es independiente del cierre de sesión:

* **Cerrar sesión:** termina la sesión del usuario y mantiene funcionando el cliente.
* **Salir:** termina la ejecución del cliente.

---

# 13. Flujo del cliente

## 13.1 Usuario no autenticado

```text
=========================
 SISTEMA DE TAREAS
=========================

1. Registrarse
2. Iniciar sesión
3. Salir
```

## 13.2 Usuario autenticado

```text
=========================
 MIS TAREAS
=========================

1. Listar tareas
2. Crear tarea
3. Cerrar tarea
4. Cerrar sesión
5. Salir
```

---

# 14. Reglas de autenticación

Las operaciones de tareas deberán requerir autenticación:

| Operación         | Autenticación |
| ----------------- | ------------- |
| Registro          | No            |
| Login             | No            |
| Listar tareas     | Sí            |
| Crear tarea       | Sí            |
| Cerrar tarea      | Sí            |
| Logout            | Sí            |
| Salir del cliente | No            |

La aplicación deberá impedir el acceso a las funcionalidades de tareas cuando no exista un usuario autenticado.

---

# 15. API

| Método | Endpoint              | Autenticación | Descripción       |
| ------ | --------------------- | ------------: | ----------------- |
| POST   | `/registro`           |            No | Registrar usuario |
| POST   | `/login`              |            No | Iniciar sesión    |
| GET    | `/tareas`             |            Sí | Listar tareas     |
| POST   | `/tareas`             |            Sí | Crear tarea       |
| PUT    | `/tareas/<id>/cerrar` |            Sí | Cerrar tarea      |
| POST   | `/logout`             |            Sí | Cerrar sesión     |

---

# 16. Requerimientos técnicos

## RT-01 — Flask

El servidor deberá desarrollarse utilizando Flask.

## RT-02 — SQLite

La persistencia deberá realizarse utilizando SQLite.

## RT-03 — Hashing

Deberá utilizarse una librería para hashear contraseñas.

Las contraseñas no podrán almacenarse en texto plano.

## RT-04 — Servidor

El archivo principal deberá ser:

```text
servidor.py
```

El mismo deberá contener la API Flask y la interacción con SQLite.

## RT-05 — Cliente

Se deberá implementar un cliente de consola que consuma la API.

Se propone:

```text
cliente.py
```

---

# 17. Estructura propuesta

```text
pfo2/
│
├── servidor.py
├── cliente.py
├── README.md
├── requirements.txt
├── tareas.db
│
└── screenshots/
    ├── registro.png
    ├── login.png
    ├── listar_tareas.png
    ├── crear_tarea.png
    ├── cerrar_tarea.png
    └── logout.png
```

---

# 18. Manejo de errores

La API deberá devolver respuestas apropiadas ante situaciones como:

### Usuario inexistente

```http
401 Unauthorized
```

### Contraseña incorrecta

```http
401 Unauthorized
```

### Usuario no autenticado

```http
401 Unauthorized
```

### Tarea inexistente

```http
404 Not Found
```

### Intento de modificar una tarea de otro usuario

```http
403 Forbidden
```

### Datos incompletos

```http
400 Bad Request
```

---

# 19. Pruebas

Se deberán demostrar como mínimo los siguientes escenarios.

## Prueba 1 — Registro

```text
Registrar usuario
        ↓
Usuario almacenado
        ↓
Contraseña almacenada como hash
```

## Prueba 2 — Login

```text
Ingresar credenciales
        ↓
Credenciales válidas
        ↓
Sesión iniciada
```

## Prueba 3 — Crear tarea

```text
Crear tarea
        ↓
Tarea persistida
        ↓
Estado = pendiente
```

## Prueba 4 — Listar tareas

```text
Listar tareas
        ↓
Se muestran las tareas del usuario
```

## Prueba 5 — Cerrar tarea

```text
Seleccionar tarea
        ↓
Cerrar tarea
        ↓
Estado = cerrada
```

## Prueba 6 — Cerrar sesión

```text
Cerrar sesión
        ↓
Sesión invalidada
        ↓
No se puede acceder a las tareas
```

## Prueba 7 — Salir

```text
Seleccionar "Salir"
        ↓
Cliente finalizado
```

El entregable original requiere capturas de pantalla de pruebas exitosas.

---

# 20. Documentación

Se deberá incluir:

```text
README.md
```

El README deberá explicar:

* Requisitos previos.
* Instalación.
* Instalación de dependencias.
* Creación/inicialización de la base de datos.
* Ejecución del servidor.
* Ejecución del cliente.
* Flujo de registro.
* Flujo de login.
* Listado de tareas.
* Creación de tareas.
* Cierre de tareas.
* Cierre de sesión.
* Salida del cliente.
* Ejemplos de uso.
* Evidencias de pruebas.

El enunciado original exige documentación con instrucciones para ejecutar y probar el proyecto.

---

# 21. Entregables

### E-01 — Código fuente

```text
servidor.py
cliente.py
```

### E-02 — Base de datos

```text
SQLite
```

### E-03 — Documentación

```text
README.md
```

### E-04 — Capturas

Evidencias de las pruebas exitosas.

### E-05 — GitHub

Repositorio con el código fuente.

### E-06 — GitHub Pages

Alojamiento del proyecto mediante GitHub Pages, según el requisito original.

### E-07 — Respuestas conceptuales

Responder:

1. ¿Por qué hashear contraseñas?
2. ¿Cuáles son las ventajas de usar SQLite en este proyecto?

Estas preguntas forman parte de los entregables conceptuales originales.

---

# 22. Criterios de aceptación

La iniciativa se considerará terminada cuando:

* [ ] Un usuario pueda registrarse.
* [ ] Las contraseñas se almacenen hasheadas.
* [ ] Un usuario pueda iniciar sesión.
* [ ] Un usuario autenticado pueda listar sus tareas.
* [ ] Un usuario autenticado pueda crear tareas.
* [ ] Las nuevas tareas comiencen en estado `pendiente`.
* [ ] Un usuario autenticado pueda cerrar sus tareas.
* [ ] Una tarea cerrada quede en estado `cerrada`.
* [ ] Un usuario no pueda acceder a tareas de otro usuario.
* [ ] Un usuario pueda cerrar sesión.
* [ ] Después del logout no pueda utilizar las operaciones protegidas.
* [ ] El cliente permita salir de la aplicación.
* [ ] Los datos persistan en SQLite.
* [ ] La API esté implementada con Flask.
* [ ] Exista `servidor.py`.
* [ ] Exista un cliente de consola.
* [ ] Exista `README.md`.
* [ ] Existan capturas de las pruebas.
* [ ] El proyecto esté publicado en GitHub.
* [ ] Se haya configurado GitHub Pages.
* [ ] Se hayan respondido las preguntas conceptuales.

---

# 23. Fuera de alcance

No se incorporan, salvo que posteriormente se soliciten:

* Edición de tareas.
* Eliminación de tareas.
* Prioridades.
* Fechas de vencimiento.
* Categorías.
* Asignación de tareas entre usuarios.
* Roles administrativos.
* Recuperación de contraseñas.
* JWT/OAuth.
* Notificaciones.
* Aplicación web completa.

---

# 24. Definición de terminado

El sistema deberá permitir completar el siguiente flujo de punta a punta:

```text
┌─────────────────────┐
│     Registrarse     │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│   Iniciar sesión    │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│    Menú de tareas   │
├─────────────────────┤
│ 1. Listar tareas    │
│ 2. Crear tarea      │
│ 3. Cerrar tarea     │
│ 4. Cerrar sesión    │
│ 5. Salir            │
└─────────────────────┘
           │
           ├──── Listar ────→ GET /tareas
           │
           ├──── Crear ─────→ POST /tareas
           │
           ├──── Cerrar ────→ PUT /tareas/<id>/cerrar
           │
           ├──── Logout ────→ POST /logout
           │
           └──── Salir ─────→ Finalizar cliente
```

La solución deberá demostrar que las operaciones de gestión de tareas funcionan únicamente para usuarios autenticados y que los datos permanecen almacenados en SQLite.
