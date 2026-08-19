from app import create_app, db, bcrypt
from app.models.user import User
from app.models.team import Team

def seed_data():
    app = create_app()
    with app.app_context():
        # Create Admin
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = User(
                username='admin',
                email='admin@entreprise.com',
                password_hash=hashed_password,
                role='admin',
                full_name='Administrateur Système'
            )
            db.session.add(admin)
            db.session.commit()
            print("Administrateur créé (admin / admin123)")

        # Create Teams and Leaders (from Document)
        team_leaders = [
            {'username': 'ablaye', 'name': 'Ablaye DIOUF'},
            {'username': 'yakhya', 'name': 'Yakhya'},
            {'username': 'cheikh', 'name': 'Cheikh NDIAYE'},
            {'username': 'alysow', 'name': 'Alysow DJIBA'},
            {'username': 'mor', 'name': 'Mor DRAME'}
        ]

        for leader_data in team_leaders:
            user = User.query.filter_by(username=leader_data['username']).first()
            if not user:
                hashed_password = bcrypt.generate_password_hash('pass123').decode('utf-8')
                user = User(
                    username=leader_data['username'],
                    email=f"{leader_data['username']}@entreprise.com",
                    password_hash=hashed_password,
                    role='team_leader',
                    full_name=leader_data['name']
                )
                db.session.add(user)
                db.session.commit()
                
                # Create team
                team = Team(
                    team_name=f"Équipe {leader_data['name']}",
                    team_leader_id=user.id,
                    description=f"Équipe de {leader_data['name']}"
                )
                db.session.add(team)
                db.session.commit()
                
                # Update user with team_id
                user.team_id = team.id
                db.session.commit()
                print(f"Équipe et Chef d'équipe créés : {leader_data['name']} ({leader_data['username']} / pass123)")

if __name__ == '__main__':
    seed_data()
