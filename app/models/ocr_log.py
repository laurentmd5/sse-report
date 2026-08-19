from datetime import datetime
from app import db

class OCRLog(db.Model):
    __tablename__ = 'ocr_logs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    intervention_id = db.Column(db.Integer, db.ForeignKey('interventions.id', ondelete='CASCADE'), index=True)
    page_number = db.Column(db.Integer, nullable=True)
    raw_text = db.Column(db.Text, nullable=True)
    extracted_value = db.Column(db.String(50), nullable=True)
    extraction_pattern = db.Column(db.String(100), nullable=True)
    processing_time_ms = db.Column(db.Integer, nullable=True)
    error_code = db.Column(db.String(20), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    intervention = db.relationship('Intervention', backref=db.backref('ocr_logs', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<OCRLog {self.id} for Intervention {self.intervention_id}>'
