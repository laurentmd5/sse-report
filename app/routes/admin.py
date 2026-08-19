from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db, bcrypt
from app.models.user import User
from app.models.team import Team

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
    flash(f"L'équipe '{team.team_name}' a été {status}.", 'success')
    return redirect(url_for('admin.manage_teams'))
