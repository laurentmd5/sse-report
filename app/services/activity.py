from flask import request
from flask_login import current_user
from app import db
from app.models.activity import ActivityLog

def log_activity(action, details=None):
    """
    Enregistre une action dans le journal d'activité.
    Utilise request.remote_addr pour l'IP et current_user pour l'ID si connecté.
    """
    try:
        user_id = current_user.id if current_user and current_user.is_authenticated else None
        
        # Récupérer l'IP correctement (gérer le proxy Nginx)
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip:
            ip = ip.split(',')[0].strip() # Prendre la première IP si y'en a plusieurs
            
        activity = ActivityLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip
        )
        
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Fallback silencieux en prod, on affiche l'erreur en dev
        print(f"Erreur lors de l'enregistrement de l'activité: {e}")
