from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db, bcrypt
from app.services.activity import log_activity

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('Ce compte est désactivé.', 'danger')
                return redirect(url_for('auth.login'))
                
            login_user(user, remember=True)
            log_activity("Connexion", "L'utilisateur s'est connecté.")
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Identifiant ou mot de passe incorrect.', 'danger')
            
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    log_activity("Déconnexion", "L'utilisateur s'est déconnecté.")
    logout_user()
    return redirect(url_for('auth.login'))
