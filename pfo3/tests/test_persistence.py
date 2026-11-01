from unittest.mock import MagicMock, patch
import pytest
from storage.postgres import PostgresStorage
from storage.s3_storage import S3Storage


def test_postgres_create_task_query():
    storage = PostgresStorage(
        host="localhost",
        port=5432,
        db="test_db",
        user="test_user",
        password="test_password"
    )

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_conn.__enter__.return_value = mock_conn

    with patch.object(storage, "get_connection", return_value=mock_conn):
        success = storage.create_task(
            task_id="t-1",
            request_id="r-1",
            operation="sum",
            payload={"numbers": [1, 2]}
        )
        assert success is True
        mock_cur.execute.assert_called_once()
        args = mock_cur.execute.call_args[0]
        # Verificar que la sentencia SQL sea parametrizada (RNF-04)
        assert "INSERT INTO tasks" in args[0]
        assert "%s" in args[0]
        assert args[1][0] == "t-1"
        assert args[1][1] == "r-1"
        assert args[1][2] == "sum"


def test_postgres_set_completed():
    storage = PostgresStorage()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_conn.__enter__.return_value = mock_conn

    with patch.object(storage, "get_connection", return_value=mock_conn):
        storage.set_task_completed("t-1", "worker-01", 60.0, s3_artifact_url="http://s3/test")
        args = mock_cur.execute.call_args[0]
        assert "UPDATE tasks" in args[0]
        assert "completed" in args[1]
        assert "worker-01" in args[1]
        assert 60.0 in args[1]


def test_s3_storage_disabled():
    s3 = S3Storage(enabled=False)
    assert s3.save_artifact("t-1", {"data": 123}) is None
    assert s3.get_artifact("t-1") is None
