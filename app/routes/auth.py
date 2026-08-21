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
                flash('Ce compte est dÃ©sactivÃ©.', 'danger')
                return redirect(url_for('auth.login'))
                
            login_user(user, remember=True)
            log_activity("Connexion", "L'utilisateur s'est connectÃ©.")
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Identifiant ou mot de passe incorrect.', 'danger')
            
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    log_activity("DÃ©connexion", "L'utilisateur s'est dÃ©connectÃ©.")
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not new_password or len(new_password) < 6:
            flash("Le mot de passe doit faire au moins 6 caractères.", "danger")
            return redirect(url_for('auth.change_password'))
            
        if new_password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return redirect(url_for('auth.change_password'))
            
        # Update password
        current_user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        current_user.must_change_password = False
        db.session.commit()
        
        log_activity("Changement de mot de passe", "L'utilisateur a changé son mot de passe.")
        flash("Votre mot de passe a été mis à jour avec succès !", "success")
        return redirect(url_for('main.dashboard'))
        
    return render_template('auth/change_password.html')
