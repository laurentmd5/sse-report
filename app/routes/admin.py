from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db, bcrypt
from app.models.user import User
from app.models.team import Team
from app.services.activity import log_activity

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin():
        flash("Accès refusé. Vous devez être administrateur.", "danger")
        return redirect(url_for('main.dashboard'))

@bp.route('/teams')
def manage_teams():
    teams = Team.query.all()
    return render_template('admin/manage_teams.html', teams=teams)

@bp.route('/teams/add', methods=['POST'])
def add_team():
    team_name = request.form.get('team_name')
    leader_fullname = request.form.get('leader_fullname')
    leader_username = request.form.get('leader_username')
    leader_email = request.form.get('leader_email')
    leader_password = request.form.get('leader_password')
    
    # 1. Vérifications basiques
    if User.query.filter_by(username=leader_username).first():
        flash(f"L'identifiant '{leader_username}' existe déjà.", 'danger')
        return redirect(url_for('admin.manage_teams'))
        
    if User.query.filter_by(email=leader_email).first():
        flash(f"L'email '{leader_email}' est déjà utilisé.", 'danger')
        return redirect(url_for('admin.manage_teams'))
        
    if Team.query.filter_by(team_name=team_name).first():
        flash(f"L'équipe '{team_name}' existe déjà.", 'danger')
        return redirect(url_for('admin.manage_teams'))
        
    try:
        # 2. Création du Chef d'équipe
        hashed_password = bcrypt.generate_password_hash(leader_password).decode('utf-8')
        new_leader = User(
            username=leader_username,
            email=leader_email,
            password_hash=hashed_password,
            role='team_leader',
            full_name=leader_fullname
        )
        db.session.add(new_leader)
        db.session.flush() # Pour obtenir l'ID de l'utilisateur sans commit
        
        # 3. Création de l'Équipe
        new_team = Team(
            team_name=team_name,
            team_leader_id=new_leader.id,
            description=request.form.get('description', '')
        )
        db.session.add(new_team)
        db.session.flush() # Pour obtenir l'ID de l'équipe
        
        # 4. Lier le chef à son équipe
        new_leader.team_id = new_team.id
        
        db.session.commit()
        log_activity("Création Équipe", f"L'équipe '{team_name}' et le chef '{leader_username}' ont été créés.")
        flash(f"L'équipe '{team_name}' et le compte chef d'équipe ont été créés avec succès !", 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur est survenue lors de la création : {str(e)}", 'danger')
        
    return redirect(url_for('admin.manage_teams'))

@bp.route('/teams/toggle/<int:team_id>', methods=['POST'])
def toggle_team_status(team_id):
    team = Team.query.get_or_404(team_id)
    # Désactiver/Activer l'équipe
    team.is_active = not team.is_active
    
    # Répercuter sur le chef d'équipe
    if team.team_leader:
        team.team_leader.is_active = team.is_active
        
    db.session.commit()
    status = "activée" if team.is_active else "désactivée"
    
    log_activity("Basculer statut équipe", f"L'équipe {team.team_name} (ID: {team.id}) a été {status}.")
    flash(f"L'équipe '{team.team_name}' a été {status}.", 'success')
    return redirect(url_for('admin.manage_teams'))

@bp.route('/users')
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/manage_users.html', users=users)

@bp.route('/users/add_admin', methods=['POST'])
def add_admin():
    admin_fullname = request.form.get('admin_fullname')
    admin_username = request.form.get('admin_username')
    admin_email = request.form.get('admin_email')
    admin_password = request.form.get('admin_password')
    
    if User.query.filter_by(username=admin_username).first():
        flash(f"L'identifiant '{admin_username}' existe déjà.", 'danger')
        return redirect(url_for('admin.manage_users'))
        
    if User.query.filter_by(email=admin_email).first():
        flash(f"L'email '{admin_email}' est déjà utilisé.", 'danger')
        return redirect(url_for('admin.manage_users'))
        
    try:
        hashed_password = bcrypt.generate_password_hash(admin_password).decode('utf-8')
        new_admin = User(
            username=admin_username,
            email=admin_email,
            password_hash=hashed_password,
            role='admin',
            full_name=admin_fullname
        )
        db.session.add(new_admin)
        db.session.commit()
        
        log_activity("Création Admin", f"Le compte administrateur '{admin_username}' a été créé.")
        flash(f"L'administrateur '{admin_fullname}' a été créé avec succès !", 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur: {str(e)}", 'danger')
        
    return redirect(url_for('admin.manage_users'))

@bp.route('/users/reset_password/<int:user_id>', methods=['POST'])
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')
    
    if not new_password or len(new_password) < 6:
        flash("Le nouveau mot de passe doit faire au moins 6 caractères.", 'danger')
        return redirect(url_for('admin.manage_users'))
        
    try:
        user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        
        log_activity("Réinitialisation Mot de passe", f"Le mot de passe de '{user.username}' (ID: {user.id}) a été réinitialisé.")
        flash(f"Le mot de passe de '{user.full_name}' a été réinitialisé avec succès.", 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur: {str(e)}", 'danger')
        
    return redirect(url_for('admin.manage_users'))

from app.models.activity import ActivityLog

@bp.route('/activities')
def view_activities():
    # Afficher les 100 dernières activités
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(100).all()
    return render_template('admin/activities.html', logs=logs)
