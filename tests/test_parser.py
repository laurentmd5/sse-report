import unittest
import sys
import os

# Ajouter le chemin parent pour pouvoir importer 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.parser import parse_filename

class TestParser(unittest.TestCase):
    
    def test_format_standard(self):
        filename = "339683059-Survey-Serigne Mbaye Seck.pdf"
        result = parse_filename(filename)
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['nd'], "339683059")
        self.assertEqual(result['data']['task_type'], "Survey")
        self.assertEqual(result['data']['client_name'], "Serigne Mbaye Seck")
        
    def test_format_inl(self):
        filename = "339755404-RIT-INL-Khadim seck.pdf"
        result = parse_filename(filename)
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['nd'], "339755404")
        self.assertEqual(result['data']['task_type'], "RIT")
        self.assertEqual(result['data']['client_name'], "Khadim seck")
        
    def test_format_with_parentheses(self):
        filename = "339683059-Passage-(INL)-Ousmane Ndiaye.pdf"
        result = parse_filename(filename)
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['nd'], "339683059")
        self.assertEqual(result['data']['task_type'], "Passage")
        self.assertEqual(result['data']['client_name'], "Ousmane Ndiaye")

    def test_invalid_filename(self):
        filename = "rapport_intervention_07_juillet.pdf"
        result = parse_filename(filename)
        self.assertFalse(result['success'])
        self.assertIsNone(result['data'])

if __name__ == '__main__':
    unittest.main()
