from app import create_app

# Point d'entrée pour les serveurs WSGI (comme Gunicorn)
app = create_app()

if __name__ == "__main__":
    app.run()
