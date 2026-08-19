from app import create_app, db
# Import des modèles pour que Flask-Migrate les détecte
from app.models.user import User
from app.models.team import Team
from app.models.intervention import Intervention
from app.models.ocr_log import OCRLog
from app.models.report import MonthlyReport

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Team': Team, 'Intervention': Intervention, 'OCRLog': OCRLog, 'MonthlyReport': MonthlyReport}

if __name__ == '__main__':
    app.run(debug=True)
