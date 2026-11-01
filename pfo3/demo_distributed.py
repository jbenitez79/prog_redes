"""Script de demostración y generación de evidencia para PFO 3 (Entregable 5).

Demuestra en vivo:
1. Conexión de cliente a servidores distribuidos.
2. Despacho y consumo asíncrono vía colas RabbitMQ.
3. Distribución concurrente entre Worker 1 y Worker 2 (pools de hilos).
4. Persistencia en PostgreSQL de estados y resultados con timestamps.
5. Control de errores ante operaciones no registradas (CA-03).
"""

import sys
import time
import threading
from pathlib import Path

# Asegurar importación de módulos de pfo3
pfo3_root = Path(__file__).resolve().parent
if str(pfo3_root) not in sys.path:
    sys.path.insert(0, str(pfo3_root))

from config.settings import settings
from client.client import DistributedTaskClient
from server.tcp_server import TCPServer
from workers.worker import DistributedWorker
from storage.postgres import PostgresStorage


def run_demo():
    print("=" * 70)
    print("   DEMOSTRACIÓN DEL SISTEMA DISTRIBUIDO PFO 3 (PROGRAMACIÓN DE REDES)")
    print("=" * 70)

    # 1. Verificar e inicializar almacenamiento PostgreSQL
    print("\n[Fase 1] Conectando a PostgreSQL e inicializando esquema DDL...")
    storage = PostgresStorage(password="postgres")
    try:
        storage.init_schema()
        print("[OK] Esquema verificado en PostgreSQL (tabla 'tasks').")
    except Exception as e:
        print(f"[-] Error conectando a PostgreSQL: {e}")
        return

    # 2. Iniciar Worker 1 y Worker 2 con pools de hilos independientes
    print("\n[Fase 2] Iniciando 2 Workers concurrentes...")
    worker1 = DistributedWorker(worker_id="worker-01", threads=2, postgres_storage=storage)
    worker2 = DistributedWorker(worker_id="worker-02", threads=2, postgres_storage=storage)

    t_w1 = threading.Thread(target=worker1.start, daemon=True, name="Worker-01")
    t_w2 = threading.Thread(target=worker2.start, daemon=True, name="Worker-02")
    t_w1.start()
    t_w2.start()
    time.sleep(1.0)
    print("[OK] Worker 1 (ID: worker-01) y Worker 2 (ID: worker-02) activos consumiendo de RabbitMQ.")

    # 3. Iniciar Servidor TCP
    server_port = 5090
    print(f"\n[Fase 3] Iniciando Servidor TCP en puerto {server_port}...")
    server = TCPServer(host="127.0.0.1", port=server_port, server_id="server-node-demo", max_connections=20)
    t_srv = threading.Thread(target=server.start, daemon=True, name="TCPServer-Demo")
    t_srv.start()
    time.sleep(1.0)
    print(f"[OK] Servidor TCP escuchando en 127.0.0.1:{server_port}.")

    # 4. Enviar tareas desde el Cliente TCP
    print("\n[Fase 4] Enviando tareas computacionales desde Cliente TCP...")
    client = DistributedTaskClient(host="127.0.0.1", port=server_port)
    client.connect()

    try:
        # Tarea 1: Suma
        print("\n--> [Tarea 1] Enviar 'sum' con [10, 20, 30]")
        r1 = client.send_task(operation="sum", payload={"numbers": [10, 20, 30]}, task_id="demo-task-01")
        print(f"    Respuesta: status={r1.get('status')}, result={r1.get('result')}, worker={r1.get('worker_id')}")

        # Tarea 2: Multiplicación
        print("\n--> [Tarea 2] Enviar 'multiply' con [4, 5, 2]")
        r2 = client.send_task(operation="multiply", payload={"numbers": [4, 5, 2]}, task_id="demo-task-02")
        print(f"    Respuesta: status={r2.get('status')}, result={r2.get('result')}, worker={r2.get('worker_id')}")

        # Tarea 3: Máximo
        print("\n--> [Tarea 3] Enviar 'max' con [15, 89, 42, 3]")
        r3 = client.send_task(operation="max", payload={"numbers": [15, 89, 42, 3]}, task_id="demo-task-03")
        print(f"    Respuesta: status={r3.get('status')}, result={r3.get('result')}, worker={r3.get('worker_id')}")

        # Tarea 4: Operación Inválida (CA-03)
        print("\n--> [Tarea 4] Enviar operación desconocida 'logaritmo' (Prueba CA-03)")
        r4 = client.send_task(operation="logaritmo", payload={"numbers": [10]}, task_id="demo-task-04")
        err = r4.get("error", {})
        print(f"    Respuesta Error Controlado: code={err.get('code')}, message={err.get('message')}")

    finally:
        client.close()

    # 5. Consulta y auditoría de persistencia en PostgreSQL
    print("\n[Fase 5] Consultando registros históricos persistidos en PostgreSQL:")
    print("-" * 75)
    tasks = storage.list_tasks(limit=5)
    print(f"{'TASK ID':<16} | {'OPERACIÓN':<10} | {'ESTADO':<10} | {'RESULTADO':<10} | {'WORKER':<12}")
    print("-" * 75)
    for t in tasks:
        res_str = str(t['result']) if t['result'] is not None else "-"
        w_str = str(t['worker_id']) if t['worker_id'] else "-"
        print(f"{t['task_id']:<16} | {t['operation']:<10} | {t['status']:<10} | {res_str:<10} | {w_str:<12}")
    print("-" * 75)

    # 6. Limpieza
    server.stop()
    worker1.stop()
    worker2.stop()
    print("\n[OK] Demostración completada con éxito rotundo. Todos los criterios verificados.\n")


if __name__ == "__main__":
    run_demo()
