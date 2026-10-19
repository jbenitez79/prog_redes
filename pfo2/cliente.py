import sys
import requests

API_URL = "http://127.0.0.1:5000"

# Creamos una sesión de requests para conservar automáticamente las cookies de sesión (Flask session)
session_http = requests.Session()


def mostrar_separador():
    print("=" * 35)


def registrarse():
    mostrar_separador()
    print("        REGISTRO DE USUARIO")
    mostrar_separador()
    usuario = input("Ingrese nombre de usuario: ").strip()
    if not usuario:
        print("[!] El nombre de usuario no puede estar vacío.\n")
        return

    password = input("Ingrese contraseña: ").strip()
    if not password:
        print("[!] La contraseña no puede estar vacía.\n")
        return

    try:
        resp = session_http.post(
            f"{API_URL}/registro",
            json={"usuario": usuario, "contraseña": password}
        )
        if resp.status_code == 201:
            print("\n[✔] Registro exitoso. Ahora puede iniciar sesión con sus credenciales.\n")
        else:
            datos = resp.json()
            print(f"\n[X] Error ({resp.status_code}): {datos.get('error', 'Error en el registro')}\n")
    except requests.exceptions.ConnectionError:
        print(f"\n[X] Error: no se pudo conectar con el servidor en {API_URL}. ¿Está encendido el servidor?\n")
    except Exception as e:
        print(f"\n[X] Error inesperado: {e}\n")


def iniciar_sesion():
    mostrar_separador()
    print("         INICIO DE SESIÓN")
    mostrar_separador()
    usuario = input("Usuario: ").strip()
    password = input("Contraseña: ").strip()

    if not usuario or not password:
        print("[!] Debe completar ambos campos.\n")
        return None

    try:
        resp = session_http.post(
            f"{API_URL}/login",
            json={"usuario": usuario, "contraseña": password}
        )
        if resp.status_code == 200:
            print(f"\n[✔] Bienvenido, {usuario}! Sesión iniciada correctamente.\n")
            return usuario
        else:
            datos = resp.json()
            print(f"\n[X] Error ({resp.status_code}): {datos.get('error', 'Credenciales inválidas')}\n")
            return None
    except requests.exceptions.ConnectionError:
        print(f"\n[X] Error: no se pudo conectar con el servidor en {API_URL}.\n")
        return None
    except Exception as e:
        print(f"\n[X] Error inesperado: {e}\n")
        return None


def listar_tareas():
    mostrar_separador()
    print("          LISTA DE TAREAS")
    mostrar_separador()
    try:
        resp = session_http.get(f"{API_URL}/tareas")
        if resp.status_code == 200:
            tareas = resp.json()
            if not tareas:
                print("No tienes tareas registradas actualmente.\n")
                return

            for t in tareas:
                estado_icono = "[✔ CERRADA]" if t["estado"] == "cerrada" else "[⏳ PENDIENTE]"
                print(f"ID #{t['id']} | {estado_icono} {t['titulo']}")
                if t.get("descripcion"):
                    print(f"       Descripción: {t['descripcion']}")
            print()
        else:
            datos = resp.json()
            print(f"[X] Error ({resp.status_code}): {datos.get('error', 'No se pudieron obtener las tareas')}\n")
    except requests.exceptions.ConnectionError:
        print(f"[X] Error: sin conexión con el servidor en {API_URL}.\n")


def crear_tarea():
    mostrar_separador()
    print("         CREAR NUEVA TAREA")
    mostrar_separador()
    titulo = input("Título de la tarea: ").strip()
    if not titulo:
        print("[!] El título no puede estar vacío.\n")
        return

    descripcion = input("Descripción (opcional): ").strip()

    try:
        resp = session_http.post(
            f"{API_URL}/tareas",
            json={"titulo": titulo, "descripcion": descripcion}
        )
        if resp.status_code == 201:
            datos = resp.json()
            print(f"\n[✔] Tarea #{datos['id']} creada exitosamente en estado 'pendiente'.\n")
        else:
            datos = resp.json()
            print(f"\n[X] Error ({resp.status_code}): {datos.get('error', 'No se pudo crear la tarea')}\n")
    except requests.exceptions.ConnectionError:
        print(f"\n[X] Error: sin conexión con el servidor en {API_URL}.\n")


def cerrar_tarea():
    mostrar_separador()
    print("            CERRAR TAREA")
    mostrar_separador()
    id_str = input("Ingrese el ID de la tarea a cerrar: ").strip()
    if not id_str.isdigit():
        print("[!] El ID debe ser un número entero.\n")
        return

    tarea_id = int(id_str)
    try:
        resp = session_http.put(f"{API_URL}/tareas/{tarea_id}/cerrar")
        if resp.status_code == 200:
            print(f"\n[✔] Tarea #{tarea_id} cerrada exitosamente.\n")
        elif resp.status_code == 404:
            print(f"\n[X] Error (404): La tarea #{tarea_id} no existe.\n")
        elif resp.status_code == 403:
            print(f"\n[X] Error (403): Acceso denegado. Esa tarea pertenece a otro usuario.\n")
        else:
            datos = resp.json()
            print(f"\n[X] Error ({resp.status_code}): {datos.get('error', 'No se pudo cerrar la tarea')}\n")
    except requests.exceptions.ConnectionError:
        print(f"\n[X] Error: sin conexión con el servidor en {API_URL}.\n")


def cerrar_sesion():
    try:
        resp = session_http.post(f"{API_URL}/logout")
        if resp.status_code == 200:
            print("\n[✔] Sesión cerrada exitosamente.\n")
        else:
            print("\n[!] Sesión finalizada localmente.\n")
    except Exception:
        print("\n[!] Sesión finalizada localmente.\n")


def menu_autenticado(usuario_actual):
    while True:
        mostrar_separador()
        print(f"        MIS TAREAS ({usuario_actual})")
        mostrar_separador()
        print("1. Listar tareas")
        print("2. Crear tarea")
        print("3. Cerrar tarea")
        print("4. Cerrar sesión")
        print("5. Salir")
        opcion = input("\nSeleccione una opción: ").strip()

        if opcion == "1":
            listar_tareas()
        elif opcion == "2":
            crear_tarea()
        elif opcion == "3":
            cerrar_tarea()
        elif opcion == "4":
            cerrar_sesion()
            break
        elif opcion == "5":
            print("\nSaliendo del cliente. ¡Hasta luego!")
            sys.exit(0)
        else:
            print("[!] Opción inválida. Intente nuevamente.\n")


def menu_principal():
    while True:
        mostrar_separador()
        print("       SISTEMA DE TAREAS")
        mostrar_separador()
        print("1. Registrarse")
        print("2. Iniciar sesión")
        print("3. Salir")
        opcion = input("\nSeleccione una opción: ").strip()

        if opcion == "1":
            registrarse()
        elif opcion == "2":
            usuario = iniciar_sesion()
            if usuario:
                menu_autenticado(usuario)
        elif opcion == "3":
            print("\nSaliendo de la aplicación. ¡Hasta luego!")
            sys.exit(0)
        else:
            print("[!] Opción inválida. Intente nuevamente.\n")


if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\nOperación cancelada por el usuario. Saliendo...")
        sys.exit(0)
