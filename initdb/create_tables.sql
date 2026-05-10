CREATE TABLE IF NOT EXISTS users (
    -- システム管理用ID
    id SERIAL PRIMARY KEY,
    -- ログイン用ID (一意識別)
    user_id VARCHAR(5) UNIQUE NOT NULL,
    user_name VARCHAR(50),
    mail_address VARCHAR(255),
    password_hash TEXT NOT NULL,
    
    -- 権限・状態管理
    administrator_flg BOOLEAN DEFAULT FALSE,
    delete_flg BOOLEAN DEFAULT FALSE,
    
    -- セキュリティ・監査用
    last_login_at TIMESTAMP,
    login_failure_count INT DEFAULT 0,
    
    -- タイムスタンプ
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

