-- ChangeLens 数据库初始化脚本
-- Database initialization script

-- 创建 items 表（用于测试数据库查询性能）
-- Create items table (for testing database query performance)
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引（用于测试有/无索引的性能差异）
-- Create index (for testing performance difference with/without index)
CREATE INDEX IF NOT EXISTS idx_items_name ON items(name);
CREATE INDEX IF NOT EXISTS idx_items_created_at ON items(created_at);

-- 插入测试数据
-- Insert test data
INSERT INTO items (name, value) VALUES
    ('item_1', 'Test value 1'),
    ('item_2', 'Test value 2'),
    ('item_3', 'Test value 3'),
    ('item_4', 'Test value 4'),
    ('item_5', 'Test value 5')
ON CONFLICT DO NOTHING;

-- 创建 metrics 表（用于存储性能指标）
-- Create metrics table (for storing performance metrics)
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    p50_latency_ms FLOAT,
    p95_latency_ms FLOAT,
    p99_latency_ms FLOAT,
    error_rate FLOAT,
    request_count INTEGER,
    deployment_phase VARCHAR(50),
    regression_type VARCHAR(50)
);

-- 创建索引用于快速查询
-- Create index for fast queries
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_deployment_phase ON metrics(deployment_phase);
