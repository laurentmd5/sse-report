"""
Script d'initialisation et de migration pour le module Superviseur.
Peut être exécuté sur le VPS (via docker exec) ou en local pour créer les tables
et configurer les alias des équipes.
"""
from app import create_app, db
from app.models.user import User
from app.models.team import Team
from app.models.supervisor import TeamAlias

def init_supervisor_schema():
    app = create_app()
    with app.app_context():
        print("1. Création des tables Superviseur...")
        
        # Mise à jour de l'énumération role dans MySQL si applicable
        try:
            db.session.execute(db.text("ALTER TABLE users MODIFY COLUMN role ENUM('admin', 'team_leader', 'supervisor') NOT NULL;"))
            db.session.commit()
            print("   -> Énumération User.role mise à jour avec 'supervisor'.")
        except Exception as e:
            db.session.rollback()
            print(f"   -> Note modification enum: {e}")

        # Création de toutes les nouvelles tables (batches, planning, sav, recap, aliases)
        db.create_all()
        print("   -> Tables supervisor_daily_batches, supervisor_planning_entries, supervisor_sav_entries, supervisor_recap_entries, team_aliases créées.")

        # 2. Création automatique des alias pour les équipes connues
        print("2. Configuration des alias d'équipes par défaut...")
        teams = Team.query.all()
        for t in teams:
            leader_name = (t.team_leader.full_name if t.team_leader else "").upper()
            team_name = t.team_name.upper()
            
            aliases_to_add = []
            if "BARRO" in leader_name or "BARRO" in team_name:
                aliases_to_add = ["YAKHYA BARRO", "BARRO"]
            elif "DIOUF" in leader_name or "DIOUF" in team_name or "BOUPAKAL" in leader_name or "BOUKAPAL" in leader_name:
                aliases_to_add = ["ABLAYE BOUKAPAL DIOUF", "ABDOULAYE DIOUF", "ABDOULAY BOUPAKAL DIOUF", "ABLAYE DIOUF"]
            elif "DJIBA" in leader_name or "DJIBA" in team_name or "ALY" in leader_name:
                aliases_to_add = ["ALY SOW DJIBA", "ALY SOW", "DJIBA"]
                
            for a_name in aliases_to_add:
                existing = TeamAlias.query.filter_by(alias_name=a_name).first()
                if not existing:
                    alias = TeamAlias(team_id=t.id, alias_name=a_name)
                    db.session.add(alias)
                    print(f"   -> Alias ajouté : '{a_name}' -> Équipe '{t.team_name}'")
                    
        db.session.commit()
        print("\nInitialisation du module Superviseur terminée avec succès !")

if __name__ == '__main__':
    init_supervisor_schema()
