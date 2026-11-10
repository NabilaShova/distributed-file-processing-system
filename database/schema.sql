-- Application database for the distributed file processor.
-- Run this once on Node 01. Galera replicates it to Node 02 and Node 03.
-- Do not change Galera membership, and do not modify other databases.
-- CSV file contents are not stored here. chunk_path is a filesystem path.

CREATE DATABASE IF NOT EXISTS distributed_processing
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE distributed_processing;

CREATE TABLE IF NOT EXISTS workers (
  worker_id VARCHAR(64) NOT NULL,
  hostname VARCHAR(255) NOT NULL,
  base_url VARCHAR(255) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'OFFLINE',
  last_heartbeat DATETIME(6) NULL,
  registered_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (worker_id),
  UNIQUE KEY uq_workers_base_url (base_url)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS jobs (
  job_id CHAR(36) NOT NULL,
  filename VARCHAR(255) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
  total_rows INT UNSIGNED NOT NULL DEFAULT 0,
  chunk_size INT UNSIGNED NOT NULL,
  chunk_count INT UNSIGNED NOT NULL DEFAULT 0,
  processing_config JSON NOT NULL,
  error_message VARCHAR(2000) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  started_at DATETIME(6) NULL,
  finished_at DATETIME(6) NULL,
  PRIMARY KEY (job_id),
  KEY idx_jobs_status_created (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tasks (
  task_id CHAR(36) NOT NULL,
  job_id CHAR(36) NOT NULL,
  chunk_index INT UNSIGNED NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
  assigned_worker_id VARCHAR(64) NULL,
  attempt_count INT UNSIGNED NOT NULL DEFAULT 0,
  max_attempts INT UNSIGNED NOT NULL DEFAULT 3,
  row_start INT UNSIGNED NOT NULL,
  row_end INT UNSIGNED NOT NULL,
  chunk_path VARCHAR(512) NOT NULL,
  error_message VARCHAR(2000) NULL,
  lease_expires_at DATETIME(6) NULL,
  started_at DATETIME(6) NULL,
  finished_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (task_id),
  UNIQUE KEY uq_tasks_job_chunk (job_id, chunk_index),
  KEY idx_tasks_status_lease (status, lease_expires_at),
  KEY idx_tasks_worker (assigned_worker_id),
  CONSTRAINT fk_tasks_job FOREIGN KEY (job_id) REFERENCES jobs (job_id),
  CONSTRAINT fk_tasks_worker FOREIGN KEY (assigned_worker_id) REFERENCES workers (worker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS task_results (
  result_id CHAR(36) NOT NULL,
  task_id CHAR(36) NOT NULL,
  worker_id VARCHAR(64) NOT NULL,
  attempt_number INT UNSIGNED NOT NULL,
  metrics JSON NOT NULL,
  duration_ms INT UNSIGNED NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (result_id),
  UNIQUE KEY uq_task_results_task (task_id),
  CONSTRAINT fk_task_results_task FOREIGN KEY (task_id) REFERENCES tasks (task_id),
  CONSTRAINT fk_task_results_worker FOREIGN KEY (worker_id) REFERENCES workers (worker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS job_results (
  job_id CHAR(36) NOT NULL,
  metrics JSON NOT NULL,
  duration_ms INT UNSIGNED NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (job_id),
  CONSTRAINT fk_job_results_job FOREIGN KEY (job_id) REFERENCES jobs (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
