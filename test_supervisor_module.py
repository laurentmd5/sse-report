import os
import unittest
from datetime import date
from app import create_app, db
from app.models.user import User
from app.models.team import Team
from app.models.supervisor import (
    SupervisorDailyBatch,
    SupervisorPlanningEntry,
    SupervisorSAVEntry,
    SupervisorRecapEntry,
    TeamAlias
)
from app.services.supervisor_parser import (
    parse_planning_excel,
    parse_sav_excel,
    parse_recap_excel,
    parse_recap_image,
    match_team_name
)
from app.services.supervisor_analytics import (
    get_supervisor_kpis,
    generate_supervisor_excel_report
)

class TestSupervisorModule(unittest.TestCase):
    def setUp(self):
        class TestConfig:
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            SECRET_KEY = 'test-secret'
            UPLOAD_FOLDER = 'uploads'
            
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # 1. Créer les équipes et utilisateurs de test
        self.u_admin = User(username='admin', email='admin@test.sn', password_hash='hash', role='admin', full_name='Admin Principal')
        self.u_sup = User(username='supervisor', email='sup@test.sn', password_hash='hash', role='supervisor', full_name='Superviseur Test')
        
        self.u_barro = User(username='barro', email='barro@test.sn', password_hash='hash', role='team_leader', full_name='Yakhya Barro')
        self.u_diouf = User(username='diouf', email='diouf@test.sn', password_hash='hash', role='team_leader', full_name='Abdoulay Boupakal Diouf')
        self.u_djiba = User(username='djiba', email='djiba@test.sn', password_hash='hash', role='team_leader', full_name='Aly Sow Djiba')
        
        db.session.add_all([self.u_admin, self.u_sup, self.u_barro, self.u_diouf, self.u_djiba])
        db.session.flush()
        
        self.t_barro = Team(team_name='Équipe Yakhya Barro', team_leader_id=self.u_barro.id)
        self.t_diouf = Team(team_name='Équipe Abdoulaye Diouf', team_leader_id=self.u_diouf.id)
        self.t_djiba = Team(team_name='Équipe Aly Sow Djiba', team_leader_id=self.u_djiba.id)
        
        db.session.add_all([self.t_barro, self.t_diouf, self.t_djiba])
        db.session.flush()
        
        self.u_barro.team_id = self.t_barro.id
        self.u_diouf.team_id = self.t_diouf.id
        self.u_djiba.team_id = self.t_djiba.id
        
        # Ajouter alias pour variations
        a1 = TeamAlias(team_id=self.t_diouf.id, alias_name='ABLAYE BOUKAPAL DIOUF')
        a2 = TeamAlias(team_id=self.t_diouf.id, alias_name='ABDOULAYE DIOUF')
        a3 = TeamAlias(team_id=self.t_djiba.id, alias_name='ALY SOW DJIBA')
        a4 = TeamAlias(team_id=self.t_barro.id, alias_name='YAKHYA BARRO')
        db.session.add_all([a1, a2, a3, a4])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_team_matching(self):
        """Teste la reconnaissance intelligente des équipes."""
        t_id1, is_int1 = match_team_name('ABLAYE BOUKAPAL DIOUF')
        self.assertTrue(is_int1)
        self.assertEqual(t_id1, self.t_diouf.id)
        
        t_id2, is_int2 = match_team_name('YAKHYA BARRO')
        self.assertTrue(is_int2)
        self.assertEqual(t_id2, self.t_barro.id)
        
        t_id3, is_int3 = match_team_name('ALY SOW DJIBA')
        self.assertTrue(is_int3)
        self.assertEqual(t_id3, self.t_djiba.id)
        
        t_id_ext, is_int_ext = match_team_name('BAMBA MBENGUE')
        self.assertFalse(is_int_ext)
        self.assertIsNone(t_id_ext)
        print("[OK] match_team_name")

    def test_planning_parsing_and_kpis(self):
        """Teste l'ingestion du fichier réel Planning Global et le calcul des KPI."""
        planning_file = 'PLANNING GLOBAL FTTH SOFATELCOM 04-09-2026.xlsx'
        self.assertTrue(os.path.exists(planning_file))
        
        entries = parse_planning_excel(planning_file)
        self.assertGreater(len(entries), 350)
        
        # Vérifier le nombre d'instances pour nos équipes
        internal_entries = [e for e in entries if e['is_internal_team']]
        self.assertEqual(len(internal_entries), 19)
        print(f"[OK] Planning parsing: {len(entries)} lignes totales, {len(internal_entries)} instances internes.")
        
        # Créer un batch et insérer
        target_date = date(2026, 9, 4)
        batch = SupervisorDailyBatch(batch_date=target_date, imported_by_id=self.u_sup.id, planning_filename='planning.xlsx')
        db.session.add(batch)
        db.session.flush()
        
        for e in entries:
            p = SupervisorPlanningEntry(batch_id=batch.id, batch_date=target_date, **e)
            db.session.add(p)
        db.session.commit()
        
        # Calculer les KPI
        kpis = get_supervisor_kpis(period_type='day', target_date=target_date)
        self.assertEqual(kpis['total_planning'], len(entries))
        self.assertEqual(kpis['internal_planning_count'], 19)
        self.assertGreater(kpis['market_share_pct'], 0)
        self.assertEqual(len(kpis['internal_teams_stats']), 3)
        print(f"[OK] KPI Planning: Part entreprise = {kpis['market_share_pct']}%")

    def test_sav_parsing(self):
        """Teste l'ingestion du fichier réel SAV."""
        sav_file = 'INSTANCES FIBRE THIES SOFATEL DU 29 08 2026.xlsx'
        self.assertTrue(os.path.exists(sav_file))
        
        entries = parse_sav_excel(sav_file)
        self.assertGreater(len(entries), 130)
        
        internal_sav = [e for e in entries if e['is_internal_team']]
        self.assertGreater(len(internal_sav), 10)
        print(f"[OK] SAV parsing: {len(entries)} lignes totales, {len(internal_sav)} dérangements internes.")

    def test_recap_image_parsing(self):
        """Teste l'ingestion de l'image Récap via OCR."""
        recap_img = 'image recap.jpeg'
        if os.path.exists(recap_img):
            entries = parse_recap_image(recap_img)
            self.assertIsInstance(entries, list)
            print(f"[OK] Image Recap OCR: {len(entries)} équipes extraites.")

    def test_excel_export_generation(self):
        """Teste la génération du fichier Excel exporté."""
        target_date = date(2026, 9, 4)
        batch = SupervisorDailyBatch(batch_date=target_date, imported_by_id=self.u_sup.id)
        db.session.add(batch)
        db.session.commit()
        
        buf = generate_supervisor_excel_report(period_type='day', target_date=target_date)
        self.assertIsNotNone(buf)
        self.assertGreater(len(buf.getvalue()), 1000)
        print("[OK] Génération Rapport Excel validée.")

if __name__ == '__main__':
    unittest.main()
