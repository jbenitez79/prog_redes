-- Inicialización de base de datos PostgreSQL para PFO 3
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
