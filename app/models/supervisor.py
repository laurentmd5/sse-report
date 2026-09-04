from datetime import datetime, date
from app import db

class SupervisorDailyBatch(db.Model):
    __tablename__ = 'supervisor_daily_batches'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    batch_date = db.Column(db.Date, nullable=False, index=True)
    
    planning_filename = db.Column(db.String(255), nullable=True)
    planning_imported_at = db.Column(db.DateTime, nullable=True)
    
    sav_filename = db.Column(db.String(255), nullable=True)
    sav_imported_at = db.Column(db.DateTime, nullable=True)
    
    recap_filename = db.Column(db.String(255), nullable=True)
    recap_imported_at = db.Column(db.DateTime, nullable=True)
    
    imported_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    imported_by = db.relationship('User', foreign_keys=[imported_by_id])
    planning_entries = db.relationship('SupervisorPlanningEntry', backref='batch', cascade='all, delete-orphan', lazy='dynamic')
    sav_entries = db.relationship('SupervisorSAVEntry', backref='batch', cascade='all, delete-orphan', lazy='dynamic')
    recap_entries = db.relationship('SupervisorRecapEntry', backref='batch', cascade='all, delete-orphan', lazy='dynamic')

    def __repr__(self):
        return f'<SupervisorDailyBatch {self.batch_date} (ID: {self.id})>'


class SupervisorPlanningEntry(db.Model):
    __tablename__ = 'supervisor_planning_entries'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('supervisor_daily_batches.id', ondelete='CASCADE'), nullable=False, index=True)
    batch_date = db.Column(db.Date, nullable=False, index=True)
    
    segment = db.Column(db.String(50), nullable=True)
    olt = db.Column(db.String(100), nullable=True)
    demande = db.Column(db.String(50), nullable=True, index=True)
    coper = db.Column(db.String(50), nullable=True)
    nd = db.Column(db.String(30), nullable=True, index=True)
    commande_client = db.Column(db.String(50), nullable=True)
    date_validation = db.Column(db.String(50), nullable=True)
    client_name = db.Column(db.String(255), nullable=True)
    type_logement = db.Column(db.String(100), nullable=True)
    contact_client = db.Column(db.String(100), nullable=True)
    date_intervention = db.Column(db.String(50), nullable=True)
    heure = db.Column(db.String(50), nullable=True)
    pilotes = db.Column(db.String(100), nullable=True)
    st = db.Column(db.String(100), nullable=True)
    raw_team_name = db.Column(db.String(150), nullable=True, index=True)
    tache = db.Column(db.String(100), nullable=True, index=True)
    
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True, index=True)
    is_internal_team = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    team = db.relationship('Team', foreign_keys=[team_id])

    def __repr__(self):
        return f'<PlanningEntry {self.nd} - {self.raw_team_name}>'


class SupervisorSAVEntry(db.Model):
    __tablename__ = 'supervisor_sav_entries'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('supervisor_daily_batches.id', ondelete='CASCADE'), nullable=False, index=True)
    batch_date = db.Column(db.Date, nullable=False, index=True)
    
    nd = db.Column(db.String(30), nullable=True, index=True)
    offre = db.Column(db.String(50), nullable=True)
    plage = db.Column(db.String(50), nullable=True)
    id_drgt = db.Column(db.String(50), nullable=True, index=True)
    client_name = db.Column(db.String(255), nullable=True)
    contact_client = db.Column(db.String(100), nullable=True)
    acces_rx = db.Column(db.String(100), nullable=True)
    date_si = db.Column(db.String(50), nullable=True)
    zone_rs = db.Column(db.String(100), nullable=True)
    libelle_commune = db.Column(db.String(100), nullable=True)
    libelle_quartier = db.Column(db.String(100), nullable=True)
    pilotes = db.Column(db.String(100), nullable=True)
    constitution = db.Column(db.String(100), nullable=True)
    raw_team_name = db.Column(db.String(150), nullable=True, index=True)
    
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True, index=True)
    is_internal_team = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    team = db.relationship('Team', foreign_keys=[team_id])

    def __repr__(self):
        return f'<SAVEntry {self.nd} - {self.raw_team_name}>'


class SupervisorRecapEntry(db.Model):
    __tablename__ = 'supervisor_recap_entries'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('supervisor_daily_batches.id', ondelete='CASCADE'), nullable=False, index=True)
    batch_date = db.Column(db.Date, nullable=False, index=True)
    
    raw_team_name = db.Column(db.String(150), nullable=False, index=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True, index=True)
    is_internal_team = db.Column(db.Boolean, default=False, index=True)
    
    nb_cases = db.Column(db.Integer, default=0)
    nb_ok = db.Column(db.Integer, default=0)
    nb_nok = db.Column(db.Integer, default=0)
    taux_ok = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    team = db.relationship('Team', foreign_keys=[team_id])

    def __repr__(self):
        return f'<RecapEntry {self.raw_team_name}: {self.nb_cases} cas ({self.taux_ok}%)>'


class TeamAlias(db.Model):
    __tablename__ = 'team_aliases'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True)
    alias_name = db.Column(db.String(150), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    team = db.relationship('Team', backref=db.backref('aliases', cascade='all, delete-orphan', lazy='dynamic'))

    def __repr__(self):
        return f'<TeamAlias "{self.alias_name}" -> Team {self.team_id}>'
