# Application de Suivi des Interventions FTTH

Cette application web (Flask + MySQL) permet d'automatiser l'extraction des données des rapports PDF d'interventions FTTH (Senpil Pro) pour les chefs d'équipe, et offre un tableau de bord analytique et des exports Excel pour les administrateurs.

## 🛠️ Stack Technologique
* **Backend** : Python 3, Flask, SQLAlchemy
* **Base de Données** : MySQL (ou MariaDB via WampServer/XAMPP)
* **Frontend** : HTML/CSS, Bootstrap 5, Chart.js
* **Moteur d'Extraction** : PyMuPDF (PDF vers Image), OpenCV (Filtres), pytesseract (OCR), Expressions Régulières (Regex).

## 🚀 Installation & Configuration (Environnement Local / Dev)

### 1. Prérequis
* Python 3.8+ installé
* Serveur MySQL actif (via WampServer par exemple)
* **Tesseract OCR** : 
  * Sous Windows : [Télécharger Tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
  * Lors de l'installation, notez bien le chemin (ex: `C:\Program Files\Tesseract-OCR\tesseract.exe`).
  * Assurez-vous d'installer la langue française (`fra`).

### 2. Configuration du projet
Ouvrez un terminal à la racine du projet et exécutez :

```bash
# 1. Créer un environnement virtuel
python -m venv venv

# 2. Activer l'environnement
# Sous Windows :
.\venv\Scripts\Activate.ps1
# Sous Linux/Mac :
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt
```

### 3. Base de données
Assurez-vous que MySQL est lancé.
Ouvrez le fichier `.env` à la racine (ou renommez `.env_example` en `.env`) et vérifiez l'URL de connexion :
`DATABASE_URL=mysql+pymysql://root:@localhost/ftth_reporting`

Puis créez les tables et insérez les données par défaut :
```bash
# Créer la base si elle n'existe pas via un client MySQL ou phpMyAdmin :
# CREATE DATABASE ftth_reporting;

# Générer les tables
flask db upgrade

# Insérer l'admin et les équipes de test
python seed.py
```

### 4. Lancement
Pour démarrer le serveur de développement localement :
```bash
python run.py
```
L'application est accessible sur : `http://127.0.0.1:5000`

---

## 🌍 Déploiement en Production (Linux / Ubuntu)

Pour déployer l'application sur un vrai serveur, on utilisera **Gunicorn** derrière un reverse-proxy **Nginx**.

1. Installer les paquets systèmes nécessaires :
```bash
sudo apt update
sudo apt install python3-venv python3-pip mysql-server tesseract-ocr tesseract-ocr-fra nginx
```

2. Configurer le `.env` pour la production :
Modifier `SECRET_KEY` avec une clé très complexe et configurer le bon utilisateur/mot de passe pour MySQL.

3. Démarrer Gunicorn :
```bash
# Test manuel
gunicorn --config gunicorn_config.py wsgi:app
```

En production, vous devrez créer un service systemd pour Gunicorn (ex: `/etc/systemd/system/ftth.service`) pour qu'il tourne en tâche de fond et se lance au démarrage.

4. Exemple de configuration Nginx (`/etc/nginx/sites-available/ftth`) :
```nginx
server {
    listen 80;
    server_name votre_nom_de_domaine_ou_ip;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Pour servir directement les fichiers statiques (optimisation)
    location /static {
        alias /chemin/vers/projet/app/static;
    }
}
```

## 👥 Comptes de test par défaut
* **Administrateur** : `admin` / `admin123`
* **Chefs d'équipe** : `ablaye`, `yakhya`, `cheikh`, `alysow`, `mor` / Mot de passe : `pass123`
