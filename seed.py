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



if __name__ == '__main__':
    seed_data()
