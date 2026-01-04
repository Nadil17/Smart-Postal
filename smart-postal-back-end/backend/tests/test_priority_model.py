"""
Unit tests for Priority Classification Model
"""
import unittest
import sys
sys.path.append('..')

from models.priority_classifier import PriorityClassificationModel


class TestPriorityModel(unittest.TestCase):
    """Test cases for priority classification"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.model = PriorityClassificationModel(random_state=42)
        
        # Sample training data
        self.training_data = [
            {
                'mail_type': 'Court Notice',
                'sender_type': 'Court',
                'recipient_type': 'Individual',
                'time_received': '08:00',
                'day_of_week': 'Monday'
            },
            {
                'mail_type': 'Advertisement',
                'sender_type': 'Business',
                'recipient_type': 'Individual',
                'time_received': '14:30',
                'day_of_week': 'Friday'
            }
        ] * 50  # Multiply for minimum training size
        
        self.labels = ['urgent', 'regular'] * 50
    
    def test_model_initialization(self):
        """Test model initialization"""
        self.assertIsNotNone(self.model)
        self.assertEqual(self.model.random_state, 42)
        self.assertFalse(self.model.is_trained)
    
    def test_training(self):
        """Test model training"""
        result = self.model.train(self.training_data, self.labels)
        self.assertEqual(result['status'], 'success')
        self.assertTrue(self.model.is_trained)
    
    def test_prediction_urgent(self):
        """Test urgent mail prediction"""
        self.model.train(self.training_data, self.labels)
        
        test_data = {
            'mail_type': 'Court Notice',
            'sender_type': 'Court',
            'recipient_type': 'Individual',
            'time_received': '08:00',
            'day_of_week': 'Monday'
        }
        
        result = self.model.predict(test_data)
        
        self.assertIn('priority', result)
        self.assertIn('confidence', result)
        self.assertGreater(result['confidence'], 0)
        self.assertLessEqual(result['confidence'], 1)
    
    def test_prediction_regular(self):
        """Test regular mail prediction"""
        self.model.train(self.training_data, self.labels)
        
        test_data = {
            'mail_type': 'Advertisement',
            'sender_type': 'Business',
            'recipient_type': 'Individual',
            'time_received': '14:30',
            'day_of_week': 'Friday'
        }
        
        result = self.model.predict(test_data)
        
        self.assertIn('priority', result)
        self.assertIn('confidence', result)
    
    def test_save_load_model(self):
        """Test model persistence"""
        import tempfile
        import os
        
        self.model.train(self.training_data, self.labels)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as tmp:
            tmp_path = tmp.name
        
        try:
            self.model.save_model(tmp_path)
            
            new_model = PriorityClassificationModel()
            new_model.load_model(tmp_path)
            
            self.assertTrue(new_model.is_trained)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == '__main__':
    unittest.main()