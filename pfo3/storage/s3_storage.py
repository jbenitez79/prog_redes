"""Integración con almacenamiento de objetos compatible con Amazon S3 / MinIO.

Utilizado para persistir artefactos o resultados de tareas de gran volumen,
mientras PostgreSQL conserva los metadatos y el estado de ejecución.
"""

import json
import logging
from typing import Any, Dict, Optional
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, EndpointConnectionError
from config.settings import settings

logger = logging.getLogger(__name__)


class S3Storage:
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        bucket_name: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None,
        enabled: Optional[bool] = None
    ):
        self.enabled = settings.S3_ENABLED if enabled is None else enabled
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.access_key = access_key or settings.S3_ACCESS_KEY_ID
        self.secret_key = secret_key or settings.S3_SECRET_ACCESS_KEY
        self.region = region or settings.S3_REGION
        self._client = None

    def _get_client(self):
        if not self.enabled:
            return None
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                config=Config(connect_timeout=1, read_timeout=1, retries={"max_attempts": 1})
            )
        return self._client

    def ensure_bucket_exists(self) -> bool:
        """Crea el bucket si no existe en MinIO / S3."""
        if not self.enabled:
            return False
        try:
            client = self._get_client()
            if client is None:
                return False
            client.head_bucket(Bucket=self.bucket_name)
            return True
        except (ClientError, EndpointConnectionError, Exception) as e:
            try:
                client = self._get_client()
                client.create_bucket(Bucket=self.bucket_name)
                logger.info(f"Bucket S3 '{self.bucket_name}' creado con éxito.")
                return True
            except Exception:
                logger.warning(f"S3/MinIO no está disponible en {self.endpoint_url}. Modo S3 desactivado.")
                self.enabled = False
                return False

    def save_artifact(self, task_id: str, data: Dict[str, Any]) -> Optional[str]:
        """Almacena el JSON de la tarea/resultado como objeto en S3."""
        if not self.enabled:
            return None
        client = self._get_client()
        if client is None:
            return None
        
        object_key = f"tasks/{task_id}/artifact.json"
        raw_bytes = json.dumps(data, indent=2).encode("utf-8")
        try:
            client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=raw_bytes,
                ContentType="application/json"
            )
            url = f"{self.endpoint_url}/{self.bucket_name}/{object_key}"
            logger.info(f"Artefacto S3 guardado para tarea {task_id}: {url}")
            return url
        except Exception as e:
            logger.warning(f"Error al subir artefacto a S3 para {task_id}: {e}")
            return None

    def get_artifact(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Recupera el artefacto de la tarea desde S3."""
        if not self.enabled:
            return None
        client = self._get_client()
        if client is None:
            return None
        object_key = f"tasks/{task_id}/artifact.json"
        try:
            resp = client.get_object(Bucket=self.bucket_name, Key=object_key)
            raw = resp["Body"].read().decode("utf-8")
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Error al recuperar artefacto S3 para {task_id}: {e}")
            return None
