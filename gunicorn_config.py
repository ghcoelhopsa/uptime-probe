# Gunicorn configuration file

# Server socket binding
bind = "0.0.0.0:5001"

# Worker configuration
workers = 4  # Aumentado para suportar mais requisições simultâneas
threads = 2  # Número de threads por worker
worker_class = "gthread"  # Usar gthread para melhor performance em I/O
timeout = 120  # Aumenta o timeout para 120 segundos (2 minutos)
keepalive = 5

# Logging
loglevel = "info"
accesslog = "logs/gunicorn-access.log"  # Arquivo de log separado
errorlog = "logs/gunicorn-error.log"    # Arquivo de log separado

# Process naming
proc_name = "uptime-monitor"

# Server mechanics
preload_app = True    # Pré-carrega a aplicação para evitar múltiplos schedulers
max_requests = 1000   # Limita o número máximo de requisições por worker
max_requests_jitter = 50  # Adiciona jitter para prevenir reinicializações simultâneas

# Aplicar limites de tempo mais razoáveis
graceful_timeout = 60  # Tempo para encerrar workers

# Otimizações de performance
reload = False  # Desabilita reload automático em produção
checkinterval = 30  # Verifica changes at a longer interval
