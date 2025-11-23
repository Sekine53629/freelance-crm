-- Migration: 002_schedule_estimate_tasks
-- Purpose: 工期管理、見積もり、作業工程機能

-- 見積明細テーブル
CREATE TABLE IF NOT EXISTS estimate_items (
    item_id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(project_id) ON DELETE CASCADE,
    item_name VARCHAR(255) NOT NULL,
    description TEXT,
    quantity DECIMAL(10,2) DEFAULT 1,
    unit VARCHAR(50) DEFAULT '式',
    unit_price DECIMAL(12,2) NOT NULL,
    amount DECIMAL(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- マイルストーンテーブル（工期管理）
CREATE TABLE IF NOT EXISTS milestones (
    milestone_id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(project_id) ON DELETE CASCADE,
    milestone_name VARCHAR(255) NOT NULL,
    description TEXT,
    due_date DATE NOT NULL,
    completed_date DATE,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, in_progress, completed, delayed
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 作業工程テーブル
CREATE TABLE IF NOT EXISTS tasks (
    task_id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(project_id) ON DELETE CASCADE,
    milestone_id INTEGER REFERENCES milestones(milestone_id) ON DELETE SET NULL,
    task_name VARCHAR(255) NOT NULL,
    description TEXT,
    assigned_to VARCHAR(100),
    estimated_hours DECIMAL(10,2),
    actual_hours DECIMAL(10,2),
    start_date DATE,
    due_date DATE,
    completed_date DATE,
    status VARCHAR(50) DEFAULT 'todo',  -- todo, in_progress, review, done
    priority INTEGER DEFAULT 5,  -- 1-10
    redmine_issue_id INTEGER,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 工数記録テーブル
CREATE TABLE IF NOT EXISTS time_entries (
    entry_id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(task_id) ON DELETE CASCADE,
    project_id INTEGER REFERENCES projects(project_id) ON DELETE CASCADE,
    hours DECIMAL(10,2) NOT NULL,
    description TEXT,
    work_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- RedMine設定テーブル
CREATE TABLE IF NOT EXISTS redmine_config (
    config_id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(project_id) ON DELETE CASCADE UNIQUE,
    redmine_url VARCHAR(500) NOT NULL,
    redmine_project_id VARCHAR(100) NOT NULL,
    api_key VARCHAR(255),
    sync_enabled BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- projectsテーブルに工期関連カラム追加
ALTER TABLE projects ADD COLUMN IF NOT EXISTS start_date DATE;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS actual_end_date DATE;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS actual_hours DECIMAL(10,2);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS final_amount DECIMAL(12,2);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_estimate_items_project ON estimate_items(project_id);
CREATE INDEX IF NOT EXISTS idx_milestones_project ON milestones(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_milestone ON tasks(milestone_id);
CREATE INDEX IF NOT EXISTS idx_tasks_redmine ON tasks(redmine_issue_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_task ON time_entries(task_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_project ON time_entries(project_id);
