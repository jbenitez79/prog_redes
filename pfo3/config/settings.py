import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


class Settings:
    # Servidor TCP
    TCP_HOST: str = os.getenv("TCP_HOST", "0.0.0.0")
    TCP_PORT: int = int(os.getenv("TCP_PORT", "5001"))
    MAX_CONNECTIONS: int = int(os.getenv("MAX_CONNECTIONS", "50"))
    SOCKET_TIMEOUT: float = float(os.getenv("SOCKET_TIMEOUT", "30.0"))
    SERVER_ID: str = os.getenv("SERVER_ID", "server-node-a")
    BUFFER_SIZE: int = int(os.getenv("BUFFER_SIZE", "4096"))
    MESSAGE_DELIMITER: bytes = b"\n"

    # RabbitMQ
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "127.0.0.1")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_QUEUE_TASKS: str = os.getenv("RABBITMQ_QUEUE_TASKS", "task_queue")
    RABBITMQ_QUEUE_RESULTS: str = os.getenv("RABBITMQ_QUEUE_RESULTS", "results_queue")
    RABBITMQ_EXCHANGE: str = os.getenv("RABBITMQ_EXCHANGE", "tasks_exchange")

    # PostgreSQL
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "127.0.0.1")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "distributed_tasks")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")

    # S3 / MinIO
    S3_ENABLED: bool = os.getenv("S3_ENABLED", "true").lower() in ("true", "1", "yes")
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
    S3_ACCESS_KEY_ID: str = os.getenv("S3_ACCESS_KEY_ID", "minioadmin")
    S3_SECRET_ACCESS_KEY: str = os.getenv("S3_SECRET_ACCESS_KEY", "minioadmin")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "task-artifacts")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")

    # Workers
    WORKER_ID: str = os.getenv("WORKER_ID", "worker-01")
    WORKER_THREADS: int = int(os.getenv("WORKER_THREADS", "4"))
    WORKER_PREFETCH: int = int(os.getenv("WORKER_PREFETCH", "1"))

    # Balanceador (para que el cliente sepa a dónde apuntar si se usa)
    LB_HOST: str = os.getenv("LB_HOST", "localhost")
    LB_PORT: int = int(os.getenv("LB_PORT", "5000"))


settings = Settings()
