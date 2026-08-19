from datetime import datetime
from app import db

class Team(db.Model):
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    team_name = db.Column(db.String(50), unique=True, nullable=False)
    team_leader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    # On précise foreign_keys pour éviter le conflit avec le team_id de User
    team_leader = db.relationship('User', foreign_keys=[team_leader_id], backref='led_team')

    def __repr__(self):
        return f'<Team {self.team_name}>'
