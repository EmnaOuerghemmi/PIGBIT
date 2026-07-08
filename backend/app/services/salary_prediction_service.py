"""
Service pour charger et utiliser le modèle de prédiction de salaire
Utilisé par l'agent de négociation

Version 2: Support complet pour tous les job titles trouvés dans les datasets
- Support pour 45+ job titles
- Classification intelligente par catégorie
- Prédiction améliorée avec confiance adaptatif
"""
import pickle
import os
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import warnings

logger = logging.getLogger(__name__)

# numpy/pandas are only needed for the trained-ML path. When they're absent we
# still run perfectly in the rule-based heuristic mode, so import them lazily
# and degrade gracefully instead of crashing the whole negotiations module.
try:
    import numpy as np
    import pandas as pd
    _HAS_ML_DEPS = True
except ImportError:  # pragma: no cover - optional dependency
    np = None  # type: ignore
    pd = None  # type: ignore
    _HAS_ML_DEPS = False

warnings.filterwarnings('ignore')

class SalaryPredictionService:
    """Service pour prédire les salaires basé sur le modèle ML entraîné (version complète)"""
    
    def __init__(self, model_path: str = None):
        """
        Initialise le service avec le chemin du modèle pickle
        
        Args:
            model_path: Chemin vers le fichier model pickle
                       Si None, essaie d'abord model_comprehensive_titles.p (tous les jobs)
                       Puis model_file.p (ancien modèle)
        """
        self.model = None
        self.scaler = None
        self.classifier = None
        self.feature_names = None
        self.all_job_titles = []
        self.model_path = model_path
        self.is_comprehensive = False
        self.heuristic = False  # True when no trained model is available
        self.piqbit = None      # set when a "piqbit_salary_v1" model is loaded
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle depuis le fichier pickle"""
        
        # Essayer d'abord le modèle complet avec tous les titles
        paths_to_try = []
        if self.model_path:
            paths_to_try.append(self.model_path)
        
        # Ajouter les chemins par défaut (priorité au modèle sérialisable)
        paths_to_try.extend([
            "salary_model_piqbit.p",
            "backend/salary_model_piqbit.p",
            "../salary_model_piqbit.p",
            "model_comprehensive_serializable.p",
            "backend/model_comprehensive_serializable.p",
            "../model_comprehensive_serializable.p",
            "model_comprehensive_titles.p",
            "backend/model_comprehensive_titles.p",
            "../model_comprehensive_titles.p",
            "model_file.p",
            "backend/model_file.p",
            "../model_file.p"
        ])
        
        for model_file in paths_to_try:
            if os.path.exists(model_file):
                try:
                    with open(model_file, "rb") as pickled:
                        data = pickle.load(pickled)
                        
                        # Vérifier si c'est le modèle complet ou ancien
                        if isinstance(data, dict):
                            # Nouveau modèle PIQBIT (catégorie + séniorité + expérience)
                            if data.get("format") == "piqbit_salary_v1":
                                self.piqbit = data
                                self.model = data.get("model")
                                logger.info(f"PIQBIT salary model loaded: {model_file} "
                                            f"({len(data.get('categories', []))} catégories)")
                                return
                            self.model = data.get("model")
                            self.scaler = data.get("scaler")
                            self.feature_names = data.get("feature_names")
                            
                            # Nouveau format complet (sérialisable)
                            if data.get("job_to_category") and data.get("category_mapping"):
                                self.classifier = data
                                self.all_job_titles = data.get("all_job_titles", [])
                                self.is_comprehensive = True
                                logger.info(f"Comprehensive salary model loaded: {model_file} "
                                            f"({len(self.all_job_titles)} job titles)")
                                return
                            # Ancien format avec classe CustomClassifier
                            elif data.get("classifier"):
                                self.classifier = data.get("classifier")
                                self.all_job_titles = data.get("all_job_titles", [])
                                self.is_comprehensive = True
                                logger.info(f"Salary model loaded: {model_file} "
                                            f"({len(self.all_job_titles)} job titles)")
                                return
                        else:
                            self.model = data
                            logger.info(f"Legacy salary model loaded: {model_file}")
                            return
                except Exception as e:
                    logger.warning(f"Could not load salary model {model_file}: {e}")
                    continue
        
        # No trained pickle on disk → fall back to a transparent rule-based
        # estimator so the negotiation module stays functional in V1 without
        # requiring a multi-minute training step.
        self.heuristic = True
        logger.info("No trained salary model found - using heuristic estimator (V1 fallback).")
    
    def prepare_features(self, job_data: Dict) -> np.ndarray:
        """
        Prépare les features pour le modèle basé sur les données du job
        
        Version 2: Support pour le modèle complet avec classification intelligente
        
        Args:
            job_data: Dictionnaire avec les informations du job
                - title: Titre du job
                - description: Description du job
                - rating: Note de l'entreprise (0-5)
                - python, spark, aws, excel: Compétences requises (0/1)
        
        Returns:
            Array de features pour le modèle
        """
        
        if self.is_comprehensive and self.classifier:
            # Utiliser le modèle complet avec classification
            return self._prepare_features_comprehensive(job_data)
        else:
            # Fallback sur l'ancien format
            return self._prepare_features_legacy(job_data)
    
    def _prepare_features_comprehensive(self, job_data: Dict) -> np.ndarray:
        """Prépare les features pour le modèle complet"""
        
        job_title = str(job_data.get('title', 'Unknown'))
        
        # Features de base
        features = {
            'rating': float(job_data.get('rating', 3.5)),
            'python': int(job_data.get('python', 0)),
            'spark': int(job_data.get('spark', 0)),
            'aws': int(job_data.get('aws', 0)),
            'excel': int(job_data.get('excel', 0)),
            'description_length': len(str(job_data.get('description', ''))),
        }
        
        # Ajouter les features de catégorie (one-hot encoding)
        if self.classifier and isinstance(self.classifier, dict):
            # Nouveau format sérialisable
            job_to_category = self.classifier.get('job_to_category', {})
            category_mapping = self.classifier.get('category_mapping', {})
            
            category = job_to_category.get(job_title, 'Other')
            category_id = category_mapping.get(category, category_mapping.get('Other', 0))
            
            for cat_name, cat_id in category_mapping.items():
                features[f'category_{cat_name}'] = 1 if cat_id == category_id else 0
        else:
            # Ancien format avec classe
            if self.classifier:
                category = self.classifier.get_category(job_title)
                category_id = self.classifier.encode_category(job_title)
                
                for cat_name, cat_id in self.classifier.category_mapping.items():
                    features[f'category_{cat_name}'] = 1 if cat_id == category_id else 0
        
        # Créer le vecteur de features dans l'ordre des feature_names
        feature_vector = []
        if self.feature_names:
            for fname in self.feature_names:
                if fname in features:
                    feature_vector.append(features[fname])
                else:
                    feature_vector.append(0)  # Default pour les catégories manquantes
        
        return np.array(feature_vector).reshape(1, -1)
    
    def _prepare_features_legacy(self, job_data: Dict) -> np.ndarray:
        """Ancien format de features (legacy)"""
        
        features = {}
        
        # Features numériques
        features['Rating'] = float(job_data.get('rating', 3.5))
        features['Age'] = float(job_data.get('company_age', 10))
        features['desc_len'] = len(str(job_data.get('description', '')))
        features['Num_comp'] = int(job_data.get('competitors_count', 0))
        features['PerHour'] = int(job_data.get('is_hourly', 0))
        features['Employee'] = int(job_data.get('employee_provided', 0))
        features['Same State'] = int(job_data.get('same_state', 0))
        
        # Skills features
        features['Python_yn'] = int(job_data.get('python', 0))
        features['Spark'] = int(job_data.get('spark', 0))
        features['AWS_yn'] = int(job_data.get('aws', 0))
        features['Excel_yn'] = int(job_data.get('excel', 0))
        
        # Job simplification
        job_title_lower = str(job_data.get('title', '')).lower()
        if 'data scientist' in job_title_lower:
            job_simp = 'data scientist'
        elif 'data engineer' in job_title_lower:
            job_simp = 'data engineer'
        elif 'analyst' in job_title_lower:
            job_simp = 'analyst'
        elif 'machine learning' in job_title_lower:
            job_simp = 'mle'
        else:
            job_simp = 'na'
        
        features['Job_simp'] = job_simp
        
        # Seniority
        if 'sr' in job_title_lower or 'senior' in job_title_lower or 'lead' in job_title_lower:
            features['seniority'] = 'senior'
        elif 'jr' in job_title_lower:
            features['seniority'] = 'jr'
        else:
            features['seniority'] = 'na'
        
        # Categorical encoding (one-hot encoding)
        df_temp = pd.DataFrame([features])
        df_encoded = pd.get_dummies(df_temp)
        
        return df_encoded.values
    
    def predict_salary(self, job_data: Dict) -> Dict:
        """
        Prédit le salaire pour un job donné
        
        Version 2: Utilise le modèle complet avec support pour 45+ job titles
        
        Args:
            job_data: Dictionnaire avec les informations du job
        
        Returns:
            Dict avec:
                - predicted_salary: Salaire prédit (en milliers)
                - confidence: Confiance de la prédiction (0-1)
                - range_min: Salaire minimum (0-1 quantile)
                - range_max: Salaire maximum (0-1 quantile)
                - job_category: Catégorie du job (si modèle complet)
                - supported_titles: Nombre de job titles supportés
        """
        # Trained PIQBIT model takes priority (uses seniority + experience).
        if self.piqbit is not None:
            return self._predict_piqbit(job_data)

        if self.model is None:
            # No ML model loaded → use the heuristic estimator.
            return self._predict_salary_heuristic(job_data)

        try:
            features = self.prepare_features(job_data)
            
            # Appliquer le scaler si disponible
            if self.scaler and self.is_comprehensive:
                features = self.scaler.transform(features)
            
            prediction = self.model.predict(features)[0]
            
            # Le modèle retourne une valeur en milliers
            predicted_salary = int(prediction)
            
            # Calculer une confiance basée sur la cohérence des données
            confidence = self._calculate_confidence(job_data)
            
            result = {
                "predicted_salary": predicted_salary,
                "confidence": confidence,
                "range_min": int(predicted_salary * 0.9),
                "range_max": int(predicted_salary * 1.1),
            }
            
            # Ajouter des infos du modèle complet
            if self.is_comprehensive:
                job_title = str(job_data.get('title', 'Unknown'))
                
                # Get category from classifier
                if self.classifier and isinstance(self.classifier, dict):
                    job_to_category = self.classifier.get('job_to_category', {})
                    category = job_to_category.get(job_title, 'Other')
                else:
                    category = self.classifier.get_category(job_title) if self.classifier else 'Other'
                
                result["job_category"] = category
                result["supported_titles"] = len(self.all_job_titles)
                result["model_type"] = "comprehensive"
            else:
                result["model_type"] = "legacy"
            
            return result
            
        except Exception as e:
            raise Exception(f"Erreur lors de la prédiction: {str(e)}")
    
    @staticmethod
    def _guess_category(title: str) -> str:
        t = title.lower()
        if any(k in t for k in ("data scientist", "data engineer", "data analyst", "machine learning", "ml ", "analyst")): return "Data"
        if any(k in t for k in ("design", "ux", "ui")): return "Design"
        if any(k in t for k in ("manager", "lead", "scrum", "product", "project", "architect")): return "Management"
        if any(k in t for k in ("hr", "rh", "recruit", "talent", "ressources humaines")): return "RH"
        if any(k in t for k in ("sales", "commercial", "account", "business develop")): return "Commercial"
        if any(k in t for k in ("marketing", "content", "community", "seo")): return "Marketing"
        if any(k in t for k in ("financ", "account", "comptab")): return "Finance"
        if any(k in t for k in ("support", "customer", "success")): return "Support"
        return "Tech"

    # Mots de séniorité → ordinal (aligné avec l'entraînement : Junior..Lead = 1..4).
    _SENIORITY_WORDS = {
        "junior": 1, "jr": 1, "intern": 1, "stage": 1, "stagiaire": 1, "débutant": 1, "debutant": 1,
        "mid": 2, "confirmé": 2, "confirme": 2, "intermediate": 2, "intermédiaire": 2,
        "senior": 3, "sr": 3,
        "lead": 4, "head": 4, "principal": 4, "manager": 4, "architect": 4, "director": 4,
    }

    @classmethod
    def _seniority_from_title(cls, title: str):
        """Ordinal de séniorité déduit du TITRE, ou None si aucun signal explicite."""
        t = f" {title.lower()} "
        if any(k in t for k in (" lead ", "head", "principal", "manager", "architect", "director")): return 4
        if "senior" in t or " sr " in t or " sr." in t: return 3
        if any(k in t for k in ("junior", " jr ", "intern", "stage", "stagiaire", "débutant", "debutant")): return 1
        if any(k in t for k in (" mid ", "confirmé", "confirme", "intermediate", "intermédiaire")): return 2
        return None

    @staticmethod
    def _seniority_from_experience(exp) -> Optional[int]:
        """Ordinal de séniorité déduit des ANNÉES d'expérience (seuils marché TN)."""
        if exp is None:
            return None
        try:
            exp = float(exp)
        except (TypeError, ValueError):
            return None
        if exp < 2: return 1
        if exp < 5: return 2
        if exp < 8: return 3
        return 4

    @classmethod
    def _normalize_seniority(cls, value) -> Optional[int]:
        """Normalise une séniorité fournie explicitement (mot ou ordinal 1..4)."""
        if value is None:
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            v = int(value)
            return v if 1 <= v <= 4 else None
        return cls._SENIORITY_WORDS.get(str(value).strip().lower())

    @classmethod
    def _resolve_seniority(cls, title: str, exp=None, explicit=None) -> int:
        """
        Séniorité effective, par ordre de priorité :
        1) valeur explicite (job_data['seniority'])
        2) mot-clé dans le titre
        3) déduction depuis les années d'expérience
        4) défaut = Mid (2)
        """
        return (
            cls._normalize_seniority(explicit)
            or cls._seniority_from_title(title)
            or cls._seniority_from_experience(exp)
            or 2
        )

    @classmethod
    def _guess_seniority(cls, title: str) -> int:
        """Rétro-compat : séniorité depuis le titre seul, défaut Mid."""
        return cls._seniority_from_title(title) or 2

    def _predict_piqbit(self, job_data: Dict) -> Dict:
        """Predict using the trained RandomForest (category + seniority + experience + skills)."""
        p = self.piqbit
        title = str(job_data.get("title", ""))
        category = p["title_to_category"].get(title.lower()) or self._guess_category(title)
        exp = job_data.get("experience_years")
        # Séniorité : explicite > titre > expérience > défaut.
        sen_ord = self._resolve_seniority(title, exp, job_data.get("seniority"))
        if exp is None:
            exp = {1: 1.0, 2: 3.0, 3: 6.0, 4: 10.0}.get(sen_ord, 3.0)

        vec = [1 if category == c else 0 for c in p["categories"]]
        vec.append(sen_ord)
        vec.append(float(exp))
        # Multi-hot over the trained skill vocabulary, built from the offer's
        # skills text (falls back to the legacy python/spark/aws/excel flags).
        vocab = p.get("skill_vocab") or p.get("skill_flags") or []
        skills_text = str(job_data.get("skills_text", "")).lower()
        if not skills_text:
            skills_text = " ".join(
                s for s in ("python", "spark", "aws", "excel") if int(job_data.get(s, 0))
            )
        for term in vocab:
            vec.append(1 if term in skills_text else 0)

        pred = float(self.model.predict(np.array(vec, dtype=float).reshape(1, -1))[0])
        predicted = max(800, int(round(pred / 50.0) * 50))
        confidence = self._calculate_confidence(job_data)
        return {
            "predicted_salary": predicted,
            "confidence": round(min(confidence + 0.15, 0.9), 2),
            "range_min": int(round(predicted * 0.9 / 50.0) * 50),
            "range_max": int(round(predicted * 1.1 / 50.0) * 50),
            "model_type": "ml_random_forest",
            "job_category": category,
            "currency": "TND",
            "period": "mensuel",
        }

    def _predict_salary_heuristic(self, job_data: Dict) -> Dict:
        """
        Rule-based estimate of a realistic **Tunisian monthly salary (TND)** used
        when no trained ML model is available. Anchors on a base monthly wage and
        adds premiums for role family, seniority and in-demand skills. Values are
        rounded to the nearest 50 TND. Deterministic and explainable.
        """
        title = str(job_data.get("title", "")).lower()

        base = 1500.0  # base monthly salary in TND
        # Role family premium
        if any(k in title for k in ("data scientist", "machine learning", "ml ", "ai ")):
            base += 1500
        elif any(k in title for k in ("data engineer", "devops", "cloud", "architect")):
            base += 1300
        elif any(k in title for k in ("developer", "engineer", "software", "developpeur", "développeur")):
            base += 900
        elif any(k in title for k in ("analyst", "analyste")):
            base += 500

        # Seniority premium
        if any(k in title for k in ("senior", "sr ", "lead", "principal", "head", "manager")):
            base += 1000
        elif any(k in title for k in ("junior", "jr ", "intern", "stage", "stagiaire")):
            base -= 500

        # In-demand skills premium
        base += 300 * int(job_data.get("python", 0))
        base += 250 * int(job_data.get("spark", 0))
        base += 300 * int(job_data.get("aws", 0))
        base += 80 * int(job_data.get("excel", 0))

        # Company rating nudges the estimate slightly (~0.92x at 0★ to ~1.12x at 5★)
        rating = float(job_data.get("rating", 3.5))
        base *= (0.92 + 0.04 * rating)

        predicted = max(1000, int(round(base / 50.0) * 50))  # round to nearest 50 TND
        confidence = self._calculate_confidence(job_data)
        return {
            "predicted_salary": predicted,
            "confidence": round(min(confidence, 0.7), 2),  # cap confidence for heuristic
            "range_min": int(round(predicted * 0.9 / 50.0) * 50),
            "range_max": int(round(predicted * 1.1 / 50.0) * 50),
            "model_type": "heuristic",
            "currency": "TND",
            "period": "mensuel",
        }

    def _calculate_confidence(self, job_data: Dict) -> float:
        """
        Score de confiance (0-1) fondé sur la complétude des features réellement
        utilisées par le modèle TN : séniorité, expérience et compétences.
        """
        confidence = 0.5

        # Signal de séniorité (titre explicite) : réduit l'incertitude.
        if self._seniority_from_title(str(job_data.get("title", ""))):
            confidence += 0.1
        # Années d'expérience renseignées.
        if job_data.get("experience_years") is not None:
            confidence += 0.15
        # Compétences renseignées (texte riche ou flags legacy).
        has_skills = bool(job_data.get("skills_text")) or any(
            job_data.get(k) for k in ("python", "spark", "aws", "excel")
        )
        if has_skills:
            confidence += 0.15
        # Description présente.
        if job_data.get("description"):
            confidence += 0.1

        return min(confidence, 1.0)


# Instance globale du service
salary_service = None

def get_salary_service() -> SalaryPredictionService:
    """Récupère l'instance du service de prédiction de salaire"""
    global salary_service
    if salary_service is None:
        salary_service = SalaryPredictionService()
    return salary_service
