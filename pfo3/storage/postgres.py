"""Cliente de persistencia en PostgreSQL con soporte para consultas parametrizadas.

Almacena estados de tareas ('pending', 'processing', 'completed', 'failed'),
resultados, timestamps y auditoría de workers.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from config.settings import settings

logger = logging.getLogger(__name__)


class PostgresStorage:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.host = host or settings.POSTGRES_HOST
        self.port = port or settings.POSTGRES_PORT
        self.db = db or settings.POSTGRES_DB
        self.user = user or settings.POSTGRES_USER
        self.password = password or settings.POSTGRES_PASSWORD

    def get_connection(self):
        """Retorna una nueva conexión a PostgreSQL."""
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.db,
            user=self.user,
            password=self.password,
            connect_timeout=5
        )

    def init_schema(self) -> None:
        """Crea la tabla e índices si no existen."""
        ddl = """
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            task_id VARCHAR(64) UNIQUE NOT NULL,
            request_id VARCHAR(64) NOT NULL,
            operation VARCHAR(32) NOT NULL,
            payload JSONB,
            status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
            result DOUBLE PRECISION,
            error_message TEXT,
            worker_id VARCHAR(64),
            s3_artifact_url TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP WITH TIME ZONE
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_task_id ON tasks(task_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_request_id ON tasks(request_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()
        logger.info("Esquema de PostgreSQL verificado e inicializado.")

    def create_task(
        self,
        task_id: str,
        request_id: str,
        operation: str,
        payload: Dict[str, Any]
    ) -> bool:
        """Registra una nueva tarea en estado 'pending'."""
        sql = """
        INSERT INTO tasks (task_id, request_id, operation, payload, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (task_id) DO NOTHING;
        """
        payload_json = json.dumps(payload)
        now = datetime.now(timezone.utc)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (task_id, request_id, operation, payload_json, "pending", now))
            conn.commit()
        return True

    def set_task_processing(self, task_id: str, worker_id: str) -> bool:
        """Actualiza el estado de la tarea a 'processing'."""
        sql = """
        UPDATE tasks
        SET status = %s, worker_id = %s
        WHERE task_id = %s;
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, ("processing", worker_id, task_id))
            conn.commit()
        return True

    def set_task_completed(
        self,
        task_id: str,
        worker_id: str,
        result: Any,
        s3_artifact_url: Optional[str] = None
    ) -> bool:
        """Actualiza el estado de la tarea a 'completed' con su resultado."""
        sql = """
        UPDATE tasks
        SET status = %s, worker_id = %s, result = %s, s3_artifact_url = %s, completed_at = %s
        WHERE task_id = %s;
        """
        now = datetime.now(timezone.utc)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, ("completed", worker_id, float(result) if result is not None else None, s3_artifact_url, now, task_id))
            conn.commit()
        return True

    def set_task_failed(
        self,
        task_id: str,
        worker_id: str,
        error_message: str
    ) -> bool:
        """Actualiza el estado de la tarea a 'failed' con el mensaje de error."""
        sql = """
        UPDATE tasks
        SET status = %s, worker_id = %s, error_message = %s, completed_at = %s
        WHERE task_id = %s;
        """
        now = datetime.now(timezone.utc)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, ("failed", worker_id, error_message, now, task_id))
            conn.commit()
        return True

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Recupera una tarea por su task_id."""
        sql = """
        SELECT task_id, request_id, operation, payload, status, result, error_message, worker_id, s3_artifact_url, created_at, completed_at
        FROM tasks
        WHERE task_id = %s;
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (task_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def list_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retorna las últimas tareas registradas."""
        sql = """
        SELECT task_id, request_id, operation, status, result, error_message, worker_id, created_at, completed_at
        FROM tasks
        ORDER BY id DESC
        LIMIT %s;
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (limit,))
                rows = cur.fetchall()
                return [dict(r) for r in rows]
