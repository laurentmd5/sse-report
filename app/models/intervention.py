from datetime import datetime
from app import db

class Intervention(db.Model):
    __tablename__ = 'interventions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nd = db.Column(db.String(20), nullable=False, index=True)
    demande_no = db.Column(db.String(20), nullable=True)
    client_name = db.Column(db.String(255), nullable=False)
    task_type = db.Column(db.String(50), nullable=False, index=True)
    team_leader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    intervention_date = db.Column(db.Date, nullable=False, index=True)
    pdf_filename = db.Column(db.String(255), nullable=True)
    pdf_path = db.Column(db.String(500), nullable=True)
    
    extraction_method = db.Column(db.Enum('filename_only', 'filename_ocr', 'manual'), default='filename_ocr')
    confidence_score = db.Column(db.Integer, default=0) # 0-100
    
    validation_status = db.Column(db.Enum('pending', 'validated', 'corrected'), default='pending', index=True)
    validated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    validated_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    team_leader = db.relationship('User', foreign_keys=[team_leader_id])
    validator = db.relationship('User', foreign_keys=[validated_by])

    def __repr__(self):
        return f'<Intervention {self.nd} - {self.task_type}>'
