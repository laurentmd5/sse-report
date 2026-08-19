# Utiliser une image Python officielle
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Mettre à jour les paquets et installer Tesseract-OCR et OpenCV dépendances (libgl1)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers requirements et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code
COPY . .

# Exposer le port (5000 pour Flask/Gunicorn)
EXPOSE 5000

# Commande pour démarrer l'application avec Gunicorn
# wsgi:app pointe vers l'instance Flask
CMD ["gunicorn", "-c", "gunicorn_config.py", "wsgi:app"]
