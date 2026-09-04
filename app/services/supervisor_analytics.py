import io
from datetime import datetime, date, timedelta
from sqlalchemy import func, distinct
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app import db
from app.models.team import Team
from app.models.user import User
from app.models.supervisor import (
    SupervisorDailyBatch,
    SupervisorPlanningEntry,
    SupervisorSAVEntry,
    SupervisorRecapEntry
)

def get_period_dates(period_type='day', target_date=None, start_date=None, end_date=None):
    """Calcule la plage de dates selon le type de période."""
    if not target_date:
        # Chercher la dernière date avec des données
        latest_batch = SupervisorDailyBatch.query.order_by(SupervisorDailyBatch.batch_date.desc()).first()
        target_date = latest_batch.batch_date if latest_batch else date.today()
        
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

    if period_type == 'day':
        s_date = target_date
        e_date = target_date
        label = f"Journée du {target_date.strftime('%d/%m/%Y')}"
    elif period_type == 'week':
        # Du Lundi au Dimanche de la semaine de target_date
        s_date = target_date - timedelta(days=target_date.weekday())
        e_date = s_date + timedelta(days=6)
        label = f"Semaine du {s_date.strftime('%d/%m')} au {e_date.strftime('%d/%m/%Y')}"
    elif period_type == 'month':
        # Du 1er au dernier jour du mois
        s_date = date(target_date.year, target_date.month, 1)
        next_month = date(target_date.year + (target_date.month // 12), ((target_date.month % 12) + 1), 1)
        e_date = next_month - timedelta(days=1)
        mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        label = f"Mois de {mois_fr[target_date.month - 1]} {target_date.year}"
    elif period_type == 'custom' and start_date and end_date:
        if isinstance(start_date, str): start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str): end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        s_date = start_date
        e_date = end_date
        label = f"Du {s_date.strftime('%d/%m/%Y')} au {e_date.strftime('%d/%m/%Y')}"
    else:
        s_date = target_date
        e_date = target_date
        label = f"Journée du {target_date.strftime('%d/%m/%Y')}"
        
    return s_date, e_date, label, target_date


def get_supervisor_kpis(period_type='day', target_date=None, start_date=None, end_date=None):
    """
    Calcule tous les KPI opérationnels et comparatifs pour le Superviseur sur une période donnée.
    """
    s_date, e_date, period_label, current_ref_date = get_period_dates(period_type, target_date, start_date, end_date)
    
    # 1. Requêtes de base filtrées sur la période
    planning_q = SupervisorPlanningEntry.query.filter(SupervisorPlanningEntry.batch_date.between(s_date, e_date))
    sav_q = SupervisorSAVEntry.query.filter(SupervisorSAVEntry.batch_date.between(s_date, e_date))
    recap_q = SupervisorRecapEntry.query.filter(SupervisorRecapEntry.batch_date.between(s_date, e_date))

    total_planning = planning_q.count()
    total_sav = sav_q.count()
    total_project_instances = total_planning + total_sav
    
    # Équipes actives globales (nombre d'équipes distinctes dans les fichiers)
    distinct_planning_teams = db.session.query(distinct(SupervisorPlanningEntry.raw_team_name)).filter(SupervisorPlanningEntry.batch_date.between(s_date, e_date)).all()
    distinct_sav_teams = db.session.query(distinct(SupervisorSAVEntry.raw_team_name)).filter(SupervisorSAVEntry.batch_date.between(s_date, e_date)).all()
    all_distinct_team_names = set([t[0] for t in distinct_planning_teams if t[0]] + [t[0] for t in distinct_sav_teams if t[0]])
    total_teams_count = len(all_distinct_team_names)

    # 2. Volumes Nos Équipes (Internes)
    internal_planning_q = planning_q.filter_by(is_internal_team=True)
    internal_sav_q = sav_q.filter_by(is_internal_team=True)
    
    internal_planning_count = internal_planning_q.count()
    internal_sav_count = internal_sav_q.count()
    internal_total_instances = internal_planning_count + internal_sav_count
    
    market_share_pct = round((internal_total_instances / total_project_instances * 100), 2) if total_project_instances > 0 else 0.0

    # 3. Détail et Comparaison par Équipe Interne
    internal_teams_list = Team.query.filter_by(is_active=True).all()
    internal_teams_stats = []
    
    for t in internal_teams_list:
        p_count = planning_q.filter(SupervisorPlanningEntry.team_id == t.id).count()
        s_count = sav_q.filter(SupervisorSAVEntry.team_id == t.id).count()
        tot = p_count + s_count
        
        # Répartition des tâches planning pour cette équipe
        tasks_dist = db.session.query(
            SupervisorPlanningEntry.tache, func.count(SupervisorPlanningEntry.id)
        ).filter(
            SupervisorPlanningEntry.batch_date.between(s_date, e_date),
            SupervisorPlanningEntry.team_id == t.id
        ).group_by(SupervisorPlanningEntry.tache).all()
        
        tasks_breakdown = {t_name or 'Non précisé': count for t_name, count in tasks_dist}
        
        # Récapitulatif pour cette équipe (somme sur la période)
        recap_agg = db.session.query(
            func.sum(SupervisorRecapEntry.nb_cases),
            func.sum(SupervisorRecapEntry.nb_ok),
            func.sum(SupervisorRecapEntry.nb_nok)
        ).filter(
            SupervisorRecapEntry.batch_date.between(s_date, e_date),
            SupervisorRecapEntry.team_id == t.id
        ).first()
        
        rc_cases = recap_agg[0] or 0
        rc_ok = recap_agg[1] or 0
        rc_nok = recap_agg[2] or 0
        rc_taux = round((rc_ok / rc_cases * 100), 1) if rc_cases > 0 else 0.0
        
        internal_teams_stats.append({
            'team_id': t.id,
            'team_name': t.team_name,
            'leader_name': t.team_leader.full_name if t.team_leader else t.team_name,
            'planning_count': p_count,
            'sav_count': s_count,
            'total_instances': tot,
            'tasks_breakdown': tasks_breakdown,
            'recap_cases': rc_cases,
            'recap_ok': rc_ok,
            'recap_nok': rc_nok,
            'recap_taux': rc_taux
        })

    # Trier les équipes internes par volume total décroissant
    internal_teams_stats.sort(key=lambda x: x['total_instances'], reverse=True)
    
    top_charged_internal = internal_teams_stats[0] if internal_teams_stats and internal_teams_stats[0]['total_instances'] > 0 else None
    least_charged_internal = internal_teams_stats[-1] if internal_teams_stats and internal_teams_stats[-1]['total_instances'] > 0 else None
    
    # Équipe interne avec le plus d'installations validées (OK)
    top_ok_internal = max(internal_teams_stats, key=lambda x: x['recap_ok'], default=None) if internal_teams_stats else None
    top_nok_internal = max(internal_teams_stats, key=lambda x: x['recap_nok'], default=None) if internal_teams_stats else None

    # 4. Classement Général de Toutes les Équipes du Projet (Planning + SAV)
    # Agrégation des volumes par nom brut d'équipe
    all_teams_agg = {}
    
    for row in planning_q.all():
        eq = row.raw_team_name or 'Non assigné'
        if eq not in all_teams_agg:
            all_teams_agg[eq] = {'raw_team_name': eq, 'planning': 0, 'sav': 0, 'total': 0, 'is_internal': row.is_internal_team}
        all_teams_agg[eq]['planning'] += 1
        all_teams_agg[eq]['total'] += 1
        if row.is_internal_team:
            all_teams_agg[eq]['is_internal'] = True
            
    for row in sav_q.all():
        eq = row.raw_team_name or 'Non assigné'
        if eq not in all_teams_agg:
            all_teams_agg[eq] = {'raw_team_name': eq, 'planning': 0, 'sav': 0, 'total': 0, 'is_internal': row.is_internal_team}
        all_teams_agg[eq]['sav'] += 1
        all_teams_agg[eq]['total'] += 1
        if row.is_internal_team:
            all_teams_agg[eq]['is_internal'] = True

    all_teams_ranking = sorted(all_teams_agg.values(), key=lambda x: x['total'], reverse=True)
    for idx, item in enumerate(all_teams_ranking, 1):
        item['rank'] = idx

    # 5. Synthèse Récapitulatif Global (Installations, Passages / Blocages, Taux %)
    all_recap_agg = {}
    for r in recap_q.all():
        eq = r.raw_team_name
        if eq not in all_recap_agg:
            all_recap_agg[eq] = {'raw_team_name': eq, 'cases': 0, 'ok': 0, 'nok': 0, 'is_internal': r.is_internal_team}
        all_recap_agg[eq]['cases'] += r.nb_cases
        all_recap_agg[eq]['ok'] += r.nb_ok
        all_recap_agg[eq]['nok'] += r.nb_nok
        if r.is_internal_team:
            all_recap_agg[eq]['is_internal'] = True
            
    all_recap_ranking = []
    for eq, d in all_recap_agg.items():
        taux = round((d['ok'] / d['cases'] * 100), 1) if d['cases'] > 0 else 0.0
        all_recap_ranking.append({
            'raw_team_name': eq,
            'cases': d['cases'],
            'ok': d['ok'],
            'nok': d['nok'],
            'taux_ok': taux,
            'is_internal': d['is_internal']
        })
    all_recap_ranking.sort(key=lambda x: x['ok'], reverse=True)

    # Totaux globaux Récap
    global_recap_cases = sum(r['cases'] for r in all_recap_ranking)
    global_recap_ok = sum(r['ok'] for r in all_recap_ranking)
    global_recap_nok = sum(r['nok'] for r in all_recap_ranking)
    global_recap_taux = round((global_recap_ok / global_recap_cases * 100), 1) if global_recap_cases > 0 else 0.0

    # Totaux internes Récap
    internal_recap_cases = sum(r['recap_cases'] for r in internal_teams_stats)
    internal_recap_ok = sum(r['recap_ok'] for r in internal_teams_stats)
    internal_recap_nok = sum(r['recap_nok'] for r in internal_teams_stats)
    internal_recap_taux = round((internal_recap_ok / internal_recap_cases * 100), 1) if internal_recap_cases > 0 else 0.0

    # 6. Historique / Time-series pour graphique d'évolution
    # On prend les 14 derniers jours d'activité
    time_series = []
    daily_batches = SupervisorDailyBatch.query.filter(
        SupervisorDailyBatch.batch_date.between(s_date - timedelta(days=14), e_date)
    ).order_by(SupervisorDailyBatch.batch_date.asc()).all()
    
    for b in daily_batches:
        b_p_tot = SupervisorPlanningEntry.query.filter_by(batch_id=b.id).count()
        b_s_tot = SupervisorSAVEntry.query.filter_by(batch_id=b.id).count()
        b_glob = b_p_tot + b_s_tot
        
        b_p_int = SupervisorPlanningEntry.query.filter_by(batch_id=b.id, is_internal_team=True).count()
        b_s_int = SupervisorSAVEntry.query.filter_by(batch_id=b.id, is_internal_team=True).count()
        b_int = b_p_int + b_s_int
        
        time_series.append({
            'date': b.batch_date.strftime('%d/%m'),
            'iso_date': b.batch_date.strftime('%Y-%m-%d'),
            'total_global': b_glob,
            'total_internal': b_int,
            'pct': round((b_int / b_glob * 100), 1) if b_glob > 0 else 0.0
        })

    # Liste des dates disponibles pour le sélecteur
    available_dates = [b.batch_date.strftime('%Y-%m-%d') for b in SupervisorDailyBatch.query.order_by(SupervisorDailyBatch.batch_date.desc()).limit(30).all()]

    return {
        'period_type': period_type,
        'period_label': period_label,
        'start_date': s_date.strftime('%Y-%m-%d'),
        'end_date': e_date.strftime('%Y-%m-%d'),
        'current_ref_date': current_ref_date.strftime('%Y-%m-%d'),
        'available_dates': available_dates,
        
        # Volumes Globaux Projet
        'total_planning': total_planning,
        'total_sav': total_sav,
        'total_project_instances': total_project_instances,
        'total_teams_count': total_teams_count,
        
        # Volumes Entreprise (Nos Équipes)
        'internal_planning_count': internal_planning_count,
        'internal_sav_count': internal_sav_count,
        'internal_total_instances': internal_total_instances,
        'market_share_pct': market_share_pct,
        
        # Performance Récap
        'global_recap_cases': global_recap_cases,
        'global_recap_ok': global_recap_ok,
        'global_recap_nok': global_recap_nok,
        'global_recap_taux': global_recap_taux,
        'internal_recap_cases': internal_recap_cases,
        'internal_recap_ok': internal_recap_ok,
        'internal_recap_nok': internal_recap_nok,
        'internal_recap_taux': internal_recap_taux,
        
        # Highlights & Insights
        'internal_teams_stats': internal_teams_stats,
        'top_charged_internal': top_charged_internal,
        'least_charged_internal': least_charged_internal,
        'top_ok_internal': top_ok_internal,
        'top_nok_internal': top_nok_internal,
        
        # Tableaux de classement
        'all_teams_ranking': all_teams_ranking,
        'all_recap_ranking': all_recap_ranking,
        
        # Time-series
        'time_series': time_series
    }


def generate_supervisor_excel_report(period_type='day', target_date=None, start_date=None, end_date=None):
    """
    Génère un classeur Excel complet et stylisé pour le rapport superviseur.
    """
    stats = get_supervisor_kpis(period_type, target_date, start_date, end_date)
    s_date = datetime.strptime(stats['start_date'], '%Y-%m-%d').date()
    e_date = datetime.strptime(stats['end_date'], '%Y-%m-%d').date()
    
    wb = openpyxl.Workbook()
    
    # Styles
    font_title = Font(name='Calibri', size=16, bold=True, color='FFFFFF')
    font_section = Font(name='Calibri', size=12, bold=True, color='003366')
    font_header = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    font_bold = Font(name='Calibri', size=11, bold=True)
    font_normal = Font(name='Calibri', size=11)
    
    fill_navy = PatternFill(start_color='003366', end_color='003366', fill_type='solid')
    fill_cyan = PatternFill(start_color='00AEEF', end_color='00AEEF', fill_type='solid')
    fill_light_blue = PatternFill(start_color='E6F3FA', end_color='E6F3FA', fill_type='solid')
    fill_light_green = PatternFill(start_color='E2F0D9', end_color='E2F0D9', fill_type='solid')
    fill_light_yellow = PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid')
    
    border_thin = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    
    # ==========================================
    # 1. ONGLET : SYNTHÈSE DES KPI
    # ==========================================
    ws_kpi = wb.active
    ws_kpi.title = "Synthèse KPI"
    ws_kpi.views.sheetView[0].showGridLines = True
    
    # Titre
    ws_kpi.merge_cells('A1:G2')
    cell_t = ws_kpi['A1']
    cell_t.value = f"SUIVI FTTH — RAPPORT SUPERVISEUR ({stats['period_label'].upper()})"
    cell_t.font = font_title
    cell_t.fill = fill_navy
    cell_t.alignment = Alignment(horizontal='center', vertical='center')
    
    # Blocs KPI résumés
    ws_kpi['A4'] = "INDICATEURS CLÉS DE PERFORMANCE (KPI)"
    ws_kpi['A4'].font = font_section
    
    kpi_cards = [
        ("Instances Globales Projet", stats['total_project_instances']),
        ("Instances Nos Équipes", stats['internal_total_instances']),
        ("Part d'Attribution (%)", f"{stats['market_share_pct']}%"),
        ("Installations Réalisées (OK)", stats['internal_recap_ok']),
        ("Passages / Blocages (NOK)", stats['internal_recap_nok']),
        ("Taux de Réussite (%)", f"{stats['internal_recap_taux']}%")
    ]
    
    for col_idx, (k_title, k_val) in enumerate(kpi_cards, 1):
        cell_h = ws_kpi.cell(row=5, column=col_idx, value=k_title)
        cell_h.font = Font(name='Calibri', size=10, bold=True, color='003366')
        cell_h.fill = fill_light_blue
        cell_h.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell_h.border = border_thin
        
        cell_v = ws_kpi.cell(row=6, column=col_idx, value=k_val)
        cell_v.font = Font(name='Calibri', size=14, bold=True, color='003366')
        cell_v.alignment = Alignment(horizontal='center', vertical='center')
        cell_v.border = border_thin

    # Tableau Nos Équipes
    ws_kpi['A8'] = "RÉPARTITION ET PERFORMANCE DE NOS ÉQUIPES"
    ws_kpi['A8'].font = font_section
    
    team_headers = ["Chef d'équipe / Équipe", "Instances Planning", "Instances SAV", "Total Confié", "Installations (OK)", "Passages (NOK)", "Taux de Succès"]
    for col_idx, h in enumerate(team_headers, 1):
        c = ws_kpi.cell(row=9, column=col_idx, value=h)
        c.font = font_header
        c.fill = fill_navy
        c.alignment = Alignment(horizontal='center', vertical='center')
        c.border = border_thin
        
    row_curr = 10
    for t in stats['internal_teams_stats']:
        ws_kpi.cell(row=row_curr, column=1, value=t['leader_name']).font = font_bold
        ws_kpi.cell(row=row_curr, column=2, value=t['planning_count']).alignment = Alignment(horizontal='center')
        ws_kpi.cell(row=row_curr, column=3, value=t['sav_count']).alignment = Alignment(horizontal='center')
        ws_kpi.cell(row=row_curr, column=4, value=t['total_instances']).font = font_bold
        ws_kpi.cell(row=row_curr, column=4).alignment = Alignment(horizontal='center')
        ws_kpi.cell(row=row_curr, column=5, value=t['recap_ok']).alignment = Alignment(horizontal='center')
        ws_kpi.cell(row=row_curr, column=6, value=t['recap_nok']).alignment = Alignment(horizontal='center')
        
        c_taux = ws_kpi.cell(row=row_curr, column=7, value=f"{t['recap_taux']}%")
        c_taux.alignment = Alignment(horizontal='center')
        c_taux.font = font_bold
        c_taux.fill = fill_light_green if t['recap_taux'] >= 50 else fill_light_yellow
        
        for c_idx in range(1, 8):
            ws_kpi.cell(row=row_curr, column=c_idx).border = border_thin
        row_curr += 1
        
    # Ligne Total Entreprise
    ws_kpi.cell(row=row_curr, column=1, value="TOTAL NOTRE ENTREPRISE").font = font_bold
    ws_kpi.cell(row=row_curr, column=2, value=stats['internal_planning_count']).font = font_bold
    ws_kpi.cell(row=row_curr, column=3, value=stats['internal_sav_count']).font = font_bold
    ws_kpi.cell(row=row_curr, column=4, value=stats['internal_total_instances']).font = font_bold
    ws_kpi.cell(row=row_curr, column=5, value=stats['internal_recap_ok']).font = font_bold
    ws_kpi.cell(row=row_curr, column=6, value=stats['internal_recap_nok']).font = font_bold
    ws_kpi.cell(row=row_curr, column=7, value=f"{stats['internal_recap_taux']}%").font = font_bold
    
    for c_idx in range(1, 8):
        c = ws_kpi.cell(row=row_curr, column=c_idx)
        c.fill = fill_light_blue
        c.border = border_thin
        if c_idx > 1: c.alignment = Alignment(horizontal='center')

    # Ajustement largeur colonnes
    for col in ws_kpi.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_kpi.column_dimensions[col_letter].width = max(max_len + 4, 15)

    # ==========================================
    # 2. ONGLET : DÉTAIL PLANNING NOS ÉQUIPES
    # ==========================================
    ws_plan = wb.create_sheet(title="Planning Nos Équipes")
    ws_plan.views.sheetView[0].showGridLines = True
    
    plan_headers = ["Date", "Équipe Interne", "ND", "N° Demande", "Tâche", "Client", "Contact", "OLT", "Pilotes"]
    for col_idx, h in enumerate(plan_headers, 1):
        c = ws_plan.cell(row=1, column=col_idx, value=h)
        c.font = font_header
        c.fill = fill_navy
        c.alignment = Alignment(horizontal='center', vertical='center')
        
    p_entries = SupervisorPlanningEntry.query.filter(
        SupervisorPlanningEntry.batch_date.between(s_date, e_date),
        SupervisorPlanningEntry.is_internal_team == True
    ).order_by(SupervisorPlanningEntry.raw_team_name.asc(), SupervisorPlanningEntry.id.asc()).all()
    
    for r_idx, row in enumerate(p_entries, 2):
        ws_plan.cell(row=r_idx, column=1, value=str(row.batch_date))
        ws_plan.cell(row=r_idx, column=2, value=row.raw_team_name).font = font_bold
        ws_plan.cell(row=r_idx, column=3, value=row.nd)
        ws_plan.cell(row=r_idx, column=4, value=row.demande)
        ws_plan.cell(row=r_idx, column=5, value=row.tache)
        ws_plan.cell(row=r_idx, column=6, value=row.client_name)
        ws_plan.cell(row=r_idx, column=7, value=row.contact_client)
        ws_plan.cell(row=r_idx, column=8, value=row.olt)
        ws_plan.cell(row=r_idx, column=9, value=row.pilotes)
        for c_idx in range(1, 10):
            ws_plan.cell(row=r_idx, column=c_idx).border = border_thin
            
    for col in ws_plan.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        ws_plan.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 14)

    # ==========================================
    # 3. ONGLET : DÉTAIL SAV NOS ÉQUIPES
    # ==========================================
    ws_sav = wb.create_sheet(title="SAV Nos Équipes")
    ws_sav.views.sheetView[0].showGridLines = True
    
    sav_headers = ["Date", "Équipe Interne", "ND", "ID Dérangement", "Offre", "Client", "Contact", "Commune / Quartier", "Pilotes"]
    for col_idx, h in enumerate(sav_headers, 1):
        c = ws_sav.cell(row=1, column=col_idx, value=h)
        c.font = font_header
        c.fill = fill_navy
        c.alignment = Alignment(horizontal='center', vertical='center')
        
    s_entries = SupervisorSAVEntry.query.filter(
        SupervisorSAVEntry.batch_date.between(s_date, e_date),
        SupervisorSAVEntry.is_internal_team == True
    ).order_by(SupervisorSAVEntry.raw_team_name.asc(), SupervisorSAVEntry.id.asc()).all()
    
    for r_idx, row in enumerate(s_entries, 2):
        ws_sav.cell(row=r_idx, column=1, value=str(row.batch_date))
        ws_sav.cell(row=r_idx, column=2, value=row.raw_team_name).font = font_bold
        ws_sav.cell(row=r_idx, column=3, value=row.nd)
        ws_sav.cell(row=r_idx, column=4, value=row.id_drgt)
        ws_sav.cell(row=r_idx, column=5, value=row.offre)
        ws_sav.cell(row=r_idx, column=6, value=row.client_name)
        ws_sav.cell(row=r_idx, column=7, value=row.contact_client)
        ws_sav.cell(row=r_idx, column=8, value=f"{row.libelle_commune or ''} {row.libelle_quartier or ''}".strip())
        ws_sav.cell(row=r_idx, column=9, value=row.pilotes)
        for c_idx in range(1, 10):
            ws_sav.cell(row=r_idx, column=c_idx).border = border_thin
            
    for col in ws_sav.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        ws_sav.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 14)

    # ==========================================
    # 4. ONGLET : CLASSEMENT GLOBAL DU PROJET
    # ==========================================
    ws_all = wb.create_sheet(title="Classement Marché Global")
    ws_all.views.sheetView[0].showGridLines = True
    
    all_headers = ["Rang", "Équipe", "Statut", "Planning", "SAV", "Total Instances Confiées"]
    for col_idx, h in enumerate(all_headers, 1):
        c = ws_all.cell(row=1, column=col_idx, value=h)
        c.font = font_header
        c.fill = fill_navy
        c.alignment = Alignment(horizontal='center', vertical='center')
        
    for r_idx, item in enumerate(stats['all_teams_ranking'], 2):
        c_rk = ws_all.cell(row=r_idx, column=1, value=item['rank'])
        c_rk.alignment = Alignment(horizontal='center')
        c_eq = ws_all.cell(row=r_idx, column=2, value=item['raw_team_name'])
        c_st = ws_all.cell(row=r_idx, column=3, value="NOTRE ÉQUIPE" if item['is_internal'] else "Autre")
        c_pl = ws_all.cell(row=r_idx, column=4, value=item['planning'])
        c_pl.alignment = Alignment(horizontal='center')
        c_sv = ws_all.cell(row=r_idx, column=5, value=item['sav'])
        c_sv.alignment = Alignment(horizontal='center')
        c_tt = ws_all.cell(row=r_idx, column=6, value=item['total'])
        c_tt.alignment = Alignment(horizontal='center')
        c_tt.font = font_bold
        
        if item['is_internal']:
            for c_i in range(1, 7):
                ws_all.cell(row=r_idx, column=c_i).fill = fill_light_blue
                ws_all.cell(row=r_idx, column=c_i).font = font_bold
        for c_i in range(1, 7):
            ws_all.cell(row=r_idx, column=c_i).border = border_thin
            
    for col in ws_all.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        ws_all.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 14)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
