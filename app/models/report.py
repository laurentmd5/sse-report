from datetime import datetime
from app import db

class MonthlyReport(db.Model):
    __tablename__ = 'monthly_reports'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    report_month = db.Column(db.String(7), nullable=False) # Format YYYY-MM
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    team_name = db.Column(db.String(50), nullable=True)
    
    # Statistiques
    total_sav = db.Column(db.Integer, default=0)
    total_diag_reor = db.Column(db.Integer, default=0)
    total_installation = db.Column(db.Integer, default=0)
    total_passage = db.Column(db.Integer, default=0)
    total_survey = db.Column(db.Integer, default=0)
    total_upgrade = db.Column(db.Integer, default=0)
    total_survey_install = db.Column(db.Integer, default=0)
    total_modif_interieur = db.Column(db.Integer, default=0)
    total_clients = db.Column(db.Integer, default=0)
    
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Contrainte d'unicité sur le mois et l'équipe
    __table_args__ = (
        db.UniqueConstraint('report_month', 'team_id', name='uk_month_team'),
    )
    
    # Relations
    team = db.relationship('Team', backref='monthly_reports')

    def __repr__(self):
        return f'<MonthlyReport {self.report_month} for Team {self.team_name}>'
