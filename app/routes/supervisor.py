import os
from datetime import datetime, date
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, request, current_app, flash, send_file
from flask_login import login_required, current_user

from app import db
from app.models.team import Team
from app.models.user import User
from app.models.supervisor import (
    SupervisorDailyBatch,
    SupervisorPlanningEntry,
    SupervisorSAVEntry,
    SupervisorRecapEntry,
    TeamAlias
)
from app.services.supervisor_parser import (
    parse_planning_excel,
    parse_sav_excel,
    parse_recap_excel,
    parse_recap_image,
    resync_team_associations
)
from app.services.supervisor_analytics import (
    get_supervisor_kpis,
    generate_supervisor_excel_report
)
from app.services.activity import log_activity

bp = Blueprint('supervisor', __name__, url_prefix='/supervisor')

@bp.before_request
@login_required
def require_supervisor():
    if not (current_user.is_supervisor() or current_user.is_admin()):
        flash("Accès réservé au Superviseur et à l'Administrateur.", "danger")
        return redirect(url_for('main.dashboard'))


@bp.route('/dashboard')
def dashboard():
    # Resynchronise automatiquement les entrées si de nouvelles équipes/alias ont été créés
    resync_team_associations()
    
    period_type = request.args.get('period', 'day')
    target_date = request.args.get('date')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    stats = get_supervisor_kpis(
        period_type=period_type,
        target_date=target_date,
        start_date=start_date,
        end_date=end_date
    )
    
    return render_template('supervisor/dashboard.html', stats=stats)


@bp.route('/import', methods=['GET', 'POST'])
def import_files():
    if request.method == 'POST':
        batch_date_str = request.form.get('batch_date')
        if not batch_date_str:
            target_date = date.today()
        else:
            try:
                target_date = datetime.strptime(batch_date_str, '%Y-%m-%d').date()
            except ValueError:
                target_date = date.today()

        # Récupérer ou créer le lot du jour
        batch = SupervisorDailyBatch.query.filter_by(batch_date=target_date).first()
        if not batch:
            batch = SupervisorDailyBatch(
                batch_date=target_date,
                imported_by_id=current_user.id
            )
            db.session.add(batch)
            db.session.flush()

        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        supervisor_upload_dir = os.path.join(upload_folder, 'supervisor', str(target_date))
        os.makedirs(supervisor_upload_dir, exist_ok=True)

        imported_messages = []

        # 1. Fichier Planning
        if 'planning_file' in request.files and request.files['planning_file'].filename:
            f = request.files['planning_file']
            if f.filename.lower().endswith(('.xlsx', '.xls')):
                fname = secure_filename(f.filename)
                fpath = os.path.join(supervisor_upload_dir, f"planning_{fname}")
                f.save(fpath)
                
                # Supprimer les entrées planning existantes pour ce batch
                SupervisorPlanningEntry.query.filter_by(batch_id=batch.id).delete()
                
                try:
                    entries = parse_planning_excel(fpath)
                    for e in entries:
                        p_entry = SupervisorPlanningEntry(
                            batch_id=batch.id,
                            batch_date=target_date,
                            segment=e['segment'],
                            olt=e['olt'],
                            demande=e['demande'],
                            coper=e['coper'],
                            nd=e['nd'],
                            commande_client=e['commande_client'],
                            date_validation=e['date_validation'],
                            client_name=e['client_name'],
                            type_logement=e['type_logement'],
                            contact_client=e['contact_client'],
                            date_intervention=e['date_intervention'],
                            heure=e['heure'],
                            pilotes=e['pilotes'],
                            st=e['st'],
                            raw_team_name=e['raw_team_name'],
                            tache=e['tache'],
                            team_id=e['team_id'],
                            is_internal_team=e['is_internal_team']
                        )
                        db.session.add(p_entry)
                        
                    batch.planning_filename = fname
                    batch.planning_imported_at = datetime.utcnow()
                    imported_messages.append(f"Planning : {len(entries)} lignes importées")
                except Exception as err:
                    flash(f"Erreur lors de la lecture du Planning : {str(err)}", "danger")

        # 2. Fichier SAV
        if 'sav_file' in request.files and request.files['sav_file'].filename:
            f = request.files['sav_file']
            if f.filename.lower().endswith(('.xlsx', '.xls')):
                fname = secure_filename(f.filename)
                fpath = os.path.join(supervisor_upload_dir, f"sav_{fname}")
                f.save(fpath)
                
                SupervisorSAVEntry.query.filter_by(batch_id=batch.id).delete()
                
                try:
                    entries = parse_sav_excel(fpath)
                    for e in entries:
                        s_entry = SupervisorSAVEntry(
                            batch_id=batch.id,
                            batch_date=target_date,
                            nd=e['nd'],
                            offre=e['offre'],
                            plage=e['plage'],
                            id_drgt=e['id_drgt'],
                            client_name=e['client_name'],
                            contact_client=e['contact_client'],
                            acces_rx=e['acces_rx'],
                            date_si=e['date_si'],
                            zone_rs=e['zone_rs'],
                            libelle_commune=e['libelle_commune'],
                            libelle_quartier=e['libelle_quartier'],
                            pilotes=e['pilotes'],
                            constitution=e['constitution'],
                            raw_team_name=e['raw_team_name'],
                            team_id=e['team_id'],
                            is_internal_team=e['is_internal_team']
                        )
                        db.session.add(s_entry)
                        
                    batch.sav_filename = fname
                    batch.sav_imported_at = datetime.utcnow()
                    imported_messages.append(f"SAV : {len(entries)} dérangements importés")
                except Exception as err:
                    flash(f"Erreur lors de la lecture du SAV : {str(err)}", "danger")

        # 3. Fichier Récapitulatif (Excel ou Image)
        if 'recap_file' in request.files and request.files['recap_file'].filename:
            f = request.files['recap_file']
            fname = secure_filename(f.filename)
            fpath = os.path.join(supervisor_upload_dir, f"recap_{fname}")
            f.save(fpath)
            
            SupervisorRecapEntry.query.filter_by(batch_id=batch.id).delete()
            
            try:
                if fname.lower().endswith(('.xlsx', '.xls')):
                    entries = parse_recap_excel(fpath)
                elif fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                    entries = parse_recap_image(fpath)
                else:
                    entries = []
                    
                for e in entries:
                    r_entry = SupervisorRecapEntry(
                        batch_id=batch.id,
                        batch_date=target_date,
                        raw_team_name=e['raw_team_name'],
                        team_id=e['team_id'],
                        is_internal_team=e['is_internal_team'],
                        nb_cases=e['nb_cases'],
                        nb_ok=e['nb_ok'],
                        nb_nok=e['nb_nok'],
                        taux_ok=e['taux_ok']
                    )
                    db.session.add(r_entry)
                    
                batch.recap_filename = fname
                batch.recap_imported_at = datetime.utcnow()
                imported_messages.append(f"Récapitulatif : {len(entries)} équipes traitées")
            except Exception as err:
                flash(f"Erreur lors de la lecture du Récapitulatif : {str(err)}", "danger")

        db.session.commit()
        
        if imported_messages:
            log_activity("Import Superviseur", f"Fichiers importés pour le {target_date}: {', '.join(imported_messages)}")
            flash(f"Import réussi pour le {target_date.strftime('%d/%m/%Y')} ! ({' | '.join(imported_messages)})", "success")
            return redirect(url_for('supervisor.dashboard', date=target_date.strftime('%Y-%m-%d')))
        else:
            flash("Aucun fichier sélectionné ou format non pris en charge.", "warning")
            return redirect(url_for('supervisor.import_files'))

    # GET
    batches = SupervisorDailyBatch.query.order_by(SupervisorDailyBatch.batch_date.desc()).limit(15).all()
    today_str = date.today().strftime('%Y-%m-%d')
    return render_template('supervisor/import.html', batches=batches, today_str=today_str)


@bp.route('/history')
def history():
    batches = SupervisorDailyBatch.query.order_by(SupervisorDailyBatch.batch_date.desc()).all()
    return render_template('supervisor/history.html', batches=batches)


@bp.route('/batch/<int:id>/delete', methods=['POST'])
def delete_batch(id):
    batch = SupervisorDailyBatch.query.get_or_404(id)
    b_date = batch.batch_date
    db.session.delete(batch)
    db.session.commit()
    log_activity("Suppression Import", f"Données du {b_date} supprimées par le superviseur.")
    flash(f"Les données de la journée du {b_date.strftime('%d/%m/%Y')} ont été supprimées.", "success")
    return redirect(url_for('supervisor.history'))


@bp.route('/export/excel')
def export_excel():
    period_type = request.args.get('period', 'day')
    target_date = request.args.get('date')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    excel_buffer = generate_supervisor_excel_report(
        period_type=period_type,
        target_date=target_date,
        start_date=start_date,
        end_date=end_date
    )
    
    now_str = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"rapport_superviseur_{period_type}_{now_str}.xlsx"
    
    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@bp.route('/report/view')
def report_view():
    period_type = request.args.get('period', 'day')
    target_date = request.args.get('date')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    stats = get_supervisor_kpis(
        period_type=period_type,
        target_date=target_date,
        start_date=start_date,
        end_date=end_date
    )
    
    return render_template('supervisor/report_view.html', stats=stats)


@bp.route('/aliases', methods=['GET', 'POST'])
def manage_aliases():
    teams = Team.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        team_id = request.form.get('team_id')
        alias_name = request.form.get('alias_name', '').strip()
        
        if team_id and alias_name:
            existing = TeamAlias.query.filter_by(alias_name=alias_name).first()
            if existing:
                flash(f"L'alias '{alias_name}' est déjà assigné à l'équipe '{existing.team.team_name}'.", "danger")
            else:
                new_alias = TeamAlias(team_id=team_id, alias_name=alias_name)
                db.session.add(new_alias)
                db.session.commit()
                flash(f"L'alias '{alias_name}' a été ajouté avec succès !", "success")
        return redirect(url_for('supervisor.manage_aliases'))
        
    aliases = TeamAlias.query.order_by(TeamAlias.team_id.asc(), TeamAlias.alias_name.asc()).all()
    return render_template('supervisor/aliases.html', teams=teams, aliases=aliases)


@bp.route('/aliases/<int:id>/delete', methods=['POST'])
def delete_alias(id):
    alias = TeamAlias.query.get_or_404(id)
    alias_name = alias.alias_name
    db.session.delete(alias)
    db.session.commit()
    flash(f"L'alias '{alias_name}' a été supprimé.", "success")
    return redirect(url_for('supervisor.manage_aliases'))
