-- Freelance CRM Database Schema
-- Version: 1.0.0
-- Purpose: 案件管理・営業チャネル分析

-- 獲得チャネルマスタ
CREATE TABLE IF NOT EXISTS acquisition_channels (
    channel_id SERIAL PRIMARY KEY,
    channel_name VARCHAR(100) UNIQUE NOT NULL,
    channel_category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO acquisition_channels (channel_name, channel_category) VALUES
    ('ランサーズ', 'クラウドソーシング'),
    ('クラウドワークス', 'クラウドソーシング'),
    ('ココナラ', 'クラウドソーシング'),
    ('Twitter/X', 'SNS'),
    ('LinkedIn', 'SNS'),
    ('紹介', '紹介'),
    ('直接営業', '直接営業'),
    ('その他', 'その他')
ON CONFLICT (channel_name) DO NOTHING;

-- 業種マスタ
CREATE TABLE IF NOT EXISTS industries (
    industry_id SERIAL PRIMARY KEY,
    industry_name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO industries (industry_name) VALUES
    ('IT・通信'), ('製造業'), ('小売・EC'), ('金融・保険'),
    ('医療・ヘルスケア'), ('教育'), ('不動産'), ('飲食・サービス'),
    ('メディア・広告'), ('コンサルティング'), ('スタートアップ'),
    ('個人事業主'), ('その他')
ON CONFLICT (industry_name) DO NOTHING;

-- 案件ステータスマスタ
CREATE TABLE IF NOT EXISTS project_statuses (
    status_id SERIAL PRIMARY KEY,
    status_name VARCHAR(50) UNIQUE NOT NULL,
    status_order INTEGER DEFAULT 0,
    is_terminal BOOLEAN DEFAULT FALSE
);

INSERT INTO project_statuses (status_name, status_order, is_terminal) VALUES
    ('問い合わせ', 10, FALSE), ('見積中', 20, FALSE), ('見積提出済', 30, FALSE),
    ('交渉中', 40, FALSE), ('受注確定', 50, FALSE), ('進行中', 60, FALSE),
    ('レビュー中', 70, FALSE), ('納品済', 80, TRUE), ('完了', 90, TRUE),
    ('失注', 100, TRUE), ('キャンセル', 110, TRUE)
ON CONFLICT (status_name) DO NOTHING;

-- クライアントテーブル
CREATE TABLE IF NOT EXISTS clients (
    client_id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    industry_id INTEGER REFERENCES industries(industry_id),
    company_size VARCHAR(50),
    contact_person VARCHAR(100),
    contact_email VARCHAR(255),
    payment_due_day INTEGER,
    payment_terms INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 案件テーブル
CREATE TABLE IF NOT EXISTS projects (
    project_id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(client_id),
    project_name VARCHAR(255) NOT NULL,
    acquisition_channel_id INTEGER REFERENCES acquisition_channels(channel_id),
    contact_method VARCHAR(100),
    first_contact_date DATE,
    request_date DATE,
    deadline DATE,
    estimated_hours DECIMAL(10,2),
    status_id INTEGER REFERENCES project_statuses(status_id),
    won_lost VARCHAR(20),
    lost_reason TEXT,
    estimated_amount DECIMAL(12,2),
    requirements TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_projects_client_id ON projects(client_id);
CREATE INDEX IF NOT EXISTS idx_projects_status_id ON projects(status_id);
CREATE INDEX IF NOT EXISTS idx_projects_acquisition_channel ON projects(acquisition_channel_id);
