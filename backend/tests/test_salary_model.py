"""
Tests du modèle ML de prédiction de salaire entraîné sur
`datasets/tunisia_it_salaries.csv` (script scripts/train_salary_model.py).

On valide :
  - la construction des features (longueur cohérente avec l'inférence)
  - le contrat d'entraînement -> sérialisation piqbit_salary_v1
  - que le service charge le modèle et prédit un salaire réaliste (chemin ML,
    pas le fallback heuristique)

Ces tests sont purs (pas de DB) et s'exécutent hors event-loop.
"""
import importlib.util
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATASET = BACKEND_DIR / "datasets" / "tunisia_it_salaries.csv"
MODEL_FILE = BACKEND_DIR / "salary_model_piqbit.p"

sklearn = pytest.importorskip("sklearn")


def _load_train_module():
    spec = importlib.util.spec_from_file_location(
        "train_salary_model", BACKEND_DIR / "scripts" / "train_salary_model.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_features_length_matches_vocab():
    train = _load_train_module()
    rows = train.load_rows(DATASET)
    categories, skill_vocab = train.build_vocab(rows)

    vec = train.build_features(rows[0], categories, skill_vocab)
    # one-hot(catégories) + séniorité + expérience + multi-hot(skills)
    assert len(vec) == len(categories) + 2 + len(skill_vocab)


def test_seniority_ordinal_scale():
    train = _load_train_module()
    assert train._seniority_ordinal("Junior") == 1
    assert train._seniority_ordinal("Mid") == 2
    assert train._seniority_ordinal("Senior") == 3
    assert train._seniority_ordinal("Lead") == 4
    # Valeur inconnue -> mid (2), comme _guess_seniority côté inférence.
    assert train._seniority_ordinal("???") == 2


def test_dataset_present_and_nonempty():
    train = _load_train_module()
    rows = train.load_rows(DATASET)
    assert len(rows) > 100
    assert all(float(r["salary_avg_tnd"]) > 0 for r in rows)


@pytest.mark.skipif(not MODEL_FILE.exists(), reason="modèle non entraîné (lancer train_salary_model.py)")
def test_service_loads_trained_model():
    from app.services.salary_prediction_service import SalaryPredictionService

    svc = SalaryPredictionService()
    assert svc.piqbit is not None, "le modèle piqbit_salary_v1 doit être chargé"
    assert svc.heuristic is False


@pytest.mark.skipif(not MODEL_FILE.exists(), reason="modèle non entraîné")
def test_predict_returns_realistic_tnd_salary():
    from app.services.salary_prediction_service import SalaryPredictionService

    svc = SalaryPredictionService()
    result = svc.predict_salary({
        "title": "Senior Data Scientist",
        "skills_text": "python sql machine learning",
        "experience_years": 6,
    })
    assert result["model_type"] == "ml_random_forest"
    assert result["currency"] == "TND"
    # Salaire mensuel tunisien plausible pour un senior data scientist.
    assert 1500 <= result["predicted_salary"] <= 10000
    assert result["range_min"] < result["predicted_salary"] < result["range_max"]


@pytest.mark.skipif(not MODEL_FILE.exists(), reason="modèle non entraîné")
def test_seniority_increases_salary():
    """Un profil senior doit être prédit au-dessus d'un profil junior équivalent."""
    from app.services.salary_prediction_service import SalaryPredictionService

    svc = SalaryPredictionService()
    junior = svc.predict_salary({"title": "Junior Backend Developer", "skills_text": "python sql"})
    senior = svc.predict_salary({"title": "Senior Backend Developer", "skills_text": "python sql"})
    assert senior["predicted_salary"] >= junior["predicted_salary"]


# ── Corrections V1.2 : features riches réellement prises en compte ────────────

def test_seniority_from_experience_thresholds():
    from app.services.salary_prediction_service import SalaryPredictionService as S
    assert S._seniority_from_experience(1) == 1
    assert S._seniority_from_experience(3) == 2
    assert S._seniority_from_experience(6) == 3
    assert S._seniority_from_experience(12) == 4
    assert S._seniority_from_experience(None) is None


def test_resolve_seniority_priority():
    from app.services.salary_prediction_service import SalaryPredictionService as S
    # Explicite > titre > expérience.
    assert S._resolve_seniority("Developer", 2, "lead") == 4
    # Titre prime sur l'expérience.
    assert S._resolve_seniority("Senior Developer", 1, None) == 3
    # Sans signal de titre : déduit de l'expérience.
    assert S._resolve_seniority("Frontend Developer", 10, None) == 4
    assert S._resolve_seniority("Frontend Developer", 1, None) == 1
    # Aucun signal : défaut Mid.
    assert S._resolve_seniority("Frontend Developer", None, None) == 2


@pytest.mark.skipif(not MODEL_FILE.exists(), reason="modèle non entraîné")
def test_experience_drives_prediction_without_title_keyword():
    """Correctif clé : l'expérience influence la prédiction même si le titre
    ne contient aucun mot de séniorité (avant le fix, elle était ignorée)."""
    from app.services.salary_prediction_service import SalaryPredictionService

    svc = SalaryPredictionService()
    base = {"title": "Backend Developer", "skills_text": "php sql", "description": "x"}
    junior = svc.predict_salary({**base, "experience_years": 1})["predicted_salary"]
    senior = svc.predict_salary({**base, "experience_years": 10})["predicted_salary"]
    assert senior > junior * 1.2


@pytest.mark.skipif(not MODEL_FILE.exists(), reason="modèle non entraîné")
def test_confidence_increases_with_rich_features():
    from app.services.salary_prediction_service import SalaryPredictionService

    svc = SalaryPredictionService()
    poor = svc.predict_salary({"title": "Developer"})["confidence"]
    rich = svc.predict_salary({
        "title": "Senior Developer",
        "skills_text": "python aws",
        "experience_years": 6,
        "description": "poste backend",
    })["confidence"]
    assert rich > poor


def test_jobdatarequest_schema_carries_rich_features():
    """Non-régression du bug principal : le schéma ne doit PLUS dropper
    skills_text / experience_years / seniority (sinon le modèle les perd)."""
    from app.api.v1.endpoints.negotiations import JobDataRequest

    payload = JobDataRequest(
        job_id="j1", title="Frontend Developer",
        skills_text="react, angular, typescript",
        experience_years=5, seniority="senior",
    )
    dumped = payload.model_dump()
    assert dumped["skills_text"] == "react, angular, typescript"
    assert dumped["experience_years"] == 5
    assert dumped["seniority"] == "senior"
