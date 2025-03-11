import os
import sqlite3

# Remover banco de dados se existir
if os.path.exists('uptime.db'):
    os.remove('uptime.db')
    print("Banco de dados antigo removido")

# Criar banco de dados do zero
conn = sqlite3.connect('uptime.db')
cursor = conn.cursor()

# Criar tabela de usuários com os campos atualizados
cursor.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE,
    password_hash VARCHAR(128) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    last_failed_login TIMESTAMP,
    locked_until TIMESTAMP
)
''')

# Criar usuário admin
cursor.execute('''
INSERT INTO users (username, email, password_hash, is_admin)
VALUES (?, ?, ?, ?)
''', ('admin', 'admin@example.com', '$pbkdf2-sha256$29000$svYeoxTCuDdGaK21do4xBg$ADBn/YLqvj0.DOgYhS4DSmMSYmjNFQ7lZ.p.GqTJhXQ', 1))

# Criar outras tabelas necessárias para o sistema funcionar
cursor.execute('''
CREATE TABLE probes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT,
    api_key VARCHAR(64) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    last_seen TIMESTAMP,
    last_connected TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    job_type VARCHAR(20) DEFAULT 'ping' NOT NULL,
    target_host VARCHAR(256) NOT NULL,
    kuma_url VARCHAR(256) NOT NULL,
    interval_seconds INTEGER DEFAULT 300 NOT NULL,
    timeout_seconds INTEGER DEFAULT 10 NOT NULL,
    retries INTEGER DEFAULT 3 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_run TIMESTAMP,
    probe_id INTEGER NOT NULL,
    FOREIGN KEY (probe_id) REFERENCES probes (id)
)
''')

cursor.execute('''
CREATE TABLE job_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT FALSE,
    response_time INTEGER,
    status_code INTEGER,
    error_message TEXT,
    output TEXT,
    kuma_status_code INTEGER,
    kuma_response TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs (id)
)
''')

cursor.execute('''
CREATE TABLE probe_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    probe_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(50) NOT NULL,
    ip_address VARCHAR(50),
    details TEXT,
    FOREIGN KEY (probe_id) REFERENCES probes (id)
)
''')

# Confirmar todas as alterações
conn.commit()
conn.close()

print("Banco de dados inicializado com sucesso!")
print("Usuário admin criado: admin / admin")
