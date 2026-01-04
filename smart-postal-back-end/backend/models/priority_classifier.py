"""
Priority Classification Model
Classifies mail items as urgent or regular using XGBoost
"""
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.utils.class_weight import compute_class_weight
import xgboost as xgb
from typing import Dict


class PriorityClassificationModel:
    """
    Priority Classification using XGBoost
    Classifies mail items as urgent or regular
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model = None
        self.encoders = {}
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False

        # Feature spaces for Sri Lankan postal context
        self.MAIL_TYPES = [
            'Court Notice', 'Legal Document', 'Registered Letter', 'Speed Post',
            'Express Mail', 'Tax Document', 'Government Letter', 'Bank Document',
            'Medical Report', 'Insurance Document', 'Certificate', 'Parcel',
            'Standard Letter', 'Magazine', 'Bill', 'Advertisement'
        ]

        self.SENDER_TYPES = [
            'Court', 'Law Firm', 'Government Office', 'Tax Office', 'Bank',
            'Hospital', 'Insurance Company', 'Educational Institute',
            'Business', 'Individual', 'NGO'
        ]

        self.RECIPIENT_TYPES = [
            'Individual', 'Business', 'Government Office', 'Law Firm',
            'Educational Institute', 'Hospital', 'Bank', 'Insurance Company'
        ]

        self.TIME_SLOTS = ['08:00', '09:30', '11:00', '13:00', '14:30', '16:00']
        self.DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    def preprocess_features(self, df, fit: bool = True) -> np.ndarray:
        """Feature engineering pipeline"""
        df = df.copy()

        # Encode categorical features
        categorical_features = ['mail_type', 'sender_type', 'recipient_type', 
                               'time_received', 'day_of_week']

        for feature in categorical_features:
            if fit:
                self.encoders[feature] = LabelEncoder()
                df[f'{feature}_encoded'] = self.encoders[feature].fit_transform(df[feature])
            else:
                df[f'{feature}_encoded'] = self.encoders[feature].transform(df[feature])

        # Temporal features
        time_to_category = {
            '08:00': 0, '09:30': 0,
            '11:00': 1, '13:00': 1,
            '14:30': 2, '16:00': 2
        }
        df['time_category'] = df['time_received'].map(time_to_category)

        # Binary indicators
        df['is_priority_sender'] = df['sender_type'].isin(
            ['Court', 'Law Firm', 'Government Office', 'Tax Office']
        ).astype(int)

        df['is_priority_mail'] = df['mail_type'].isin(
            ['Court Notice', 'Legal Document', 'Registered Letter', 
             'Speed Post', 'Express Mail', 'Tax Document', 'Certificate']
        ).astype(int)

        df['is_early_week'] = df['day_of_week'].isin(['Monday', 'Tuesday']).astype(int)
        df['is_morning'] = df['time_received'].isin(['08:00', '09:30']).astype(int)

        # Interaction features
        df['priority_sender_mail'] = df['is_priority_sender'] * df['is_priority_mail']
        df['morning_priority'] = df['is_morning'] * df['is_priority_mail']
        df['early_week_priority'] = df['is_early_week'] * df['is_priority_mail']
        df['morning_early_week'] = df['is_morning'] * df['is_early_week']

        # Feature selection
        self.feature_names = [
            'mail_type_encoded', 'sender_type_encoded', 'recipient_type_encoded',
            'time_received_encoded', 'day_of_week_encoded', 'time_category',
            'is_priority_sender', 'is_priority_mail', 'is_early_week', 'is_morning',
            'priority_sender_mail', 'morning_priority', 'early_week_priority',
            'morning_early_week'
        ]

        X = df[self.feature_names].values

        # Scale features
        if fit:
            X = self.scaler.fit_transform(X)
        else:
            X = self.scaler.transform(X)

        return X

    def train(self, training_data, labels):
        """Train the classification model"""
        df = pd.DataFrame(training_data)
        X = self.preprocess_features(df, fit=True)

        # Encode target
        le_target = LabelEncoder()
        y = le_target.fit_transform(labels)
        self.encoders['target'] = le_target

        # Calculate class weights
        class_weights = compute_class_weight(
            'balanced', 
            classes=np.unique(y), 
            y=y
        )
        scale_pos_weight = class_weights[1] / class_weights[0]

        # Train model
        self.model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=8,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            scale_pos_weight=scale_pos_weight,
            random_state=self.random_state,
            eval_metric='logloss',
            use_label_encoder=False
        )

        self.model.fit(X, y)
        self.is_trained = True

        return {"status": "success", "message": "Model trained successfully"}

    def predict(self, mail_data: Dict) -> Dict:
        """Predict priority for a single mail item"""
        if not self.is_trained:
            raise ValueError("Model not trained. Load a trained model first.")

        df = pd.DataFrame([mail_data])
        X = self.preprocess_features(df, fit=False)

        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]

        priority_label = self.encoders['target'].inverse_transform([prediction])[0]

        return {
            'priority': priority_label,
            'confidence': float(probabilities.max()),
            'probability_regular': float(probabilities[0]),
            'probability_urgent': float(probabilities[1])
        }

    def save_model(self, filepath: str):
        """Save trained model to disk"""
        model_data = {
            'model': self.model,
            'encoders': self.encoders,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'random_state': self.random_state
        }
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

    def load_model(self, filepath: str):
        """Load trained model from disk"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.encoders = model_data['encoders']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.random_state = model_data['random_state']
        self.is_trained = True