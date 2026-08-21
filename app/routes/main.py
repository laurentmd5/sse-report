import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, request, current_app, flash
from flask_login import login_required, current_user
from app.models.intervention import Intervention
from app.services.parser import parse_filename
from app.services.ocr import extract_pdf_data
from app.services.validation import validate_extracted_data
from app.services.activity import log_activity
from app import db

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        from datetime import datetime
        from app.services.reporting import get_monthly_stats
        
        now = datetime.now()
        stats = get_monthly_stats(now.year, now.month)
        
        mois_fr = ["Janvier", "FÃ©vrier", "Mars", "Avril", "Mai", "Juin", "Juillet", "AoÃ»t", "Septembre", "Octobre", "Novembre", "DÃ©cembre"]
        month_str = f"{mois_fr[now.month - 1]} {now.year}"
        
        return render_template('admin/dashboard.html', stats=stats, month=month_str)
    else:
        # Dashboard Chef d'Ãquipe
        interventions = Intervention.query.filter_by(
            team_leader_id=current_user.id
        ).order_by(Intervention.intervention_date.desc()).all()
        
        return render_template('team_leader/dashboard.html', interventions=interventions)

@bp.route('/export_excel')
@login_required
def export_excel():
    if not current_user.is_admin():
        flash("AccÃ¨s refusÃ©.", "danger")
        return redirect(url_for('main.dashboard'))
        
    from datetime import datetime
    from flask import send_file
    from app.services.reporting import generate_excel_report
    
    now = datetime.now()
    month_str = now.strftime("%Y_%m")
    
    excel_buffer = generate_excel_report(now.year, now.month, month_str)
    
    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name=f"rapport_interventions_{month_str}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@bp.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'pdf_file' not in request.files:
        flash('Aucun fichier sÃ©lectionnÃ©.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    file = request.files['pdf_file']
    if file.filename == '':
        flash('Aucun fichier sÃ©lectionnÃ©.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(file.filename)
        # On sauvegarde le fichier
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 1. Parsing
        parsed_data = parse_filename(file.filename)
        
        # 2. OCR
        ocr_data = extract_pdf_data(filepath)
        
        # 3. Validation
        validation_data = validate_extracted_data(parsed_data, ocr_data)
        
        # Redirection vers la vue de validation
        return render_template(
            'team_leader/validation.html',
            filename=file.filename,
            filepath=filepath,
            validation_data=validation_data
        )
    else:
        flash('Format de fichier non autorisÃ©. Uniquement PDF.', 'danger')
        return redirect(url_for('main.dashboard'))

@bp.route('/save_intervention', methods=['POST'])
@login_required
def save_intervention():
    # RÃ©cupÃ©ration des donnÃ©es du formulaire validÃ©
    nd = request.form.get('nd')
    demande_no = request.form.get('demande_no')
    task_type = request.form.get('task_type')
    client_name = request.form.get('client_name')
    filename = request.form.get('filename')
    filepath = request.form.get('filepath')
    confidence = int(request.form.get('confidence_score', 0))
    extraction_method = request.form.get('extraction_method', 'manual')
    
    # RÃ¨gle anti-doublon : MÃªme ND + MÃªme TÃ¢che + MÃªme NumÃ©ro de demande
    existing_intervention = Intervention.query.filter_by(
        nd=nd, 
        task_type=task_type, 
        demande_no=demande_no
    ).first()
    
    if existing_intervention:
        flash(f"Impossible d'enregistrer : Une intervention avec ce ND ({nd}), cette tÃ¢che ({task_type}) et ce NÂ° Demande ({demande_no}) existe dÃ©jÃ .", "danger")
        # On peut optionnellement supprimer le fichier uploadÃ© pour ne pas polluer le disque
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass
        return redirect(url_for('main.dashboard'))
    
    # CrÃ©ation de l'enregistrement
    from datetime import date
    new_intervention = Intervention(
        nd=nd,
        demande_no=demande_no,
        client_name=client_name,
        task_type=task_type,
        team_leader_id=current_user.id,
        intervention_date=date.today(), # Par dÃ©faut, on pourrait l'extraire ou demander
        pdf_filename=filename,
        pdf_path=filepath,
        confidence_score=confidence,
        extraction_method=extraction_method,
        validation_status='validated' if confidence >= 80 else 'corrected',
        validated_by=current_user.id
    )
    
    db.session.add(new_intervention)
    db.session.commit()
    
    log_activity("CrÃ©ation Intervention", f"Intervention ND {nd} (Demande: {demande_no}) crÃ©Ã©e.")
    flash(f"L'intervention {nd} a Ã©tÃ© enregistrÃ©e avec succÃ¨s !", "success")
    return redirect(url_for('main.dashboard'))

@bp.route('/edit_intervention/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_intervention(id):
    intervention = Intervention.query.get_or_404(id)
    
    # VÃ©rifier que le chef d'Ã©quipe a le droit de modifier (ou admin)
    if not current_user.is_admin() and intervention.team_leader_id != current_user.id:
        flash("AccÃ¨s refusÃ©.", "danger")
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        old_nd = intervention.nd
        intervention.nd = request.form.get('nd')
        intervention.task_type = request.form.get('task_type')
        intervention.client_name = request.form.get('client_name')
        intervention.demande_no = request.form.get('demande_no')
        intervention.validation_status = 'corrected' # Marquer comme corrigÃ© aprÃ¨s coup
        
        db.session.commit()
        log_activity("Modification Intervention", f"Intervention {old_nd} modifiÃ©e.")
        flash(f"L'intervention {intervention.nd} a Ã©tÃ© modifiÃ©e avec succÃ¨s.", "success")
        return redirect(url_for('main.dashboard'))
        
    return render_template('team_leader/edit_intervention.html', intervention=intervention)

@bp.route('/delete_intervention/<int:id>', methods=['POST'])
@login_required
def delete_intervention(id):
    intervention = Intervention.query.get_or_404(id)
    
    # VÃ©rifier que le chef d'Ã©quipe a le droit de supprimer (ou admin)
    if not current_user.is_admin() and intervention.team_leader_id != current_user.id:
        flash("AccÃ¨s refusÃ©.", "danger")
        return redirect(url_for('main.dashboard'))
        
    # Suppression du fichier physique associÃ©
    if intervention.pdf_path and os.path.exists(intervention.pdf_path):
        try:
            os.remove(intervention.pdf_path)
        except Exception:
            pass # Si le fichier n'existe plus, on l'ignore
            
    # TraÃ§abilitÃ©
    log_activity("Suppression Intervention", f"Intervention {intervention.nd} (Demande: {intervention.demande_no}) supprimÃ©e.")
    
    # Suppression en base de donnÃ©es
    db.session.delete(intervention)
    db.session.commit()
    
    flash("La fiche d'intervention a Ã©tÃ© supprimÃ©e avec succÃ¨s.", "success")
    return redirect(url_for('main.dashboard'))

@bp.before_app_request
def check_password_change():
    if current_user.is_authenticated and getattr(current_user, 'must_change_password', False):
        # Allow access to change password and logout
        if request.endpoint and request.endpoint not in ['auth.change_password', 'auth.logout', 'static']:
            flash("Veuillez configurer un nouveau mot de passe pour sécuriser votre compte.", "warning")
            return redirect(url_for('auth.change_password'))


