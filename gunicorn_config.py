import multiprocessing

# Bind
bind = "0.0.0.0:5000"

# Workers (Recommandation: 2-4 x $(NUM_CORES))
workers = multiprocessing.cpu_count() * 2 + 1

# Worker Class
worker_class = "sync"

# Timeout
timeout = 120

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
