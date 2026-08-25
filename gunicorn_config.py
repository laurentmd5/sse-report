import multiprocessing

# Bind
bind = "0.0.0.0:5000"

# Workers : FIXE A 2 pour eviter OOM sur VPS avec OCR Tesseract
# (chaque worker peut lancer un Tesseract, 2 workers = max 2 Tesseract en parallele)
# multiprocessing.cpu_count() * 2 + 1 etait trop agressif pour cette charge
workers = 2

# Worker Class
worker_class = "sync"

# Timeout : 3 minutes pour laisser le temps a l'OCR de se terminer
timeout = 180

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
