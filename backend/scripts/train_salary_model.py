"""
Entraîne le modèle de prédiction de salaire PIQBIT sur le dataset marché tunisien
(`backend/datasets/tunisia_it_salaries.csv`) et sérialise le résultat au format
`piqbit_salary_v1` consommé par `SalaryPredictionService._predict_piqbit`.

Le vecteur de features est construit EXACTEMENT comme à l'inférence :
    [ one-hot(categories) ] + [ seniority_ordinal ] + [ experience_years ] + [ multi-hot(skill_vocab) ]

Usage :
    cd backend
    python scripts/train_salary_model.py
    # → écrit backend/salary_model_piqbit.p
"""
import csv
import pickle
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# Doit rester aligné avec DecisionService/_guess_seniority (échelle ordinale 1..4).
SENIORITY_ORDINAL = {"junior": 1, "mid": 2, "senior": 3, "lead": 4}

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATASET = BACKEND_DIR / "datasets" / "tunisia_it_salaries.csv"
OUTPUT = BACKEND_DIR / "salary_model_piqbit.p"

# Taille du vocabulaire de compétences retenu (les plus fréquentes du marché).
SKILL_VOCAB_SIZE = 40


def _seniority_ordinal(label: str) -> int:
    return SENIORITY_ORDINAL.get(str(label).strip().lower(), 2)


def _tokenize_skills(raw: str) -> list[str]:
    return [s.strip().lower() for s in str(raw).split(",") if s.strip()]


def load_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_vocab(rows: list[dict]) -> tuple[list[str], list[str]]:
    """Catégories (ordre one-hot) et vocabulaire de compétences (multi-hot)."""
    categories = sorted({r["category"].strip() for r in rows})
    skill_counter: Counter = Counter()
    for r in rows:
        for s in _tokenize_skills(r["top_skills"]):
            skill_counter[s] += 1
    skill_vocab = [s for s, _ in skill_counter.most_common(SKILL_VOCAB_SIZE)]
    return categories, skill_vocab


def build_features(row: dict, categories: list[str], skill_vocab: list[str]) -> list[float]:
    """Construit le vecteur de features d'une ligne, à l'identique de l'inférence."""
    category = row["category"].strip()
    vec = [1.0 if category == c else 0.0 for c in categories]

    vec.append(float(_seniority_ordinal(row["seniority"])))

    exp_min = float(row.get("experience_years_min") or 0)
    exp_max = float(row.get("experience_years_max") or exp_min)
    vec.append((exp_min + exp_max) / 2.0)

    skills = " ".join(_tokenize_skills(row["top_skills"]))
    for term in skill_vocab:
        vec.append(1.0 if term in skills else 0.0)
    return vec


def main() -> None:
    if not DATASET.exists():
        raise SystemExit(f"Dataset introuvable : {DATASET}")

    rows = load_rows(DATASET)
    print(f"Dataset chargé : {len(rows)} lignes depuis {DATASET.name}")

    categories, skill_vocab = build_vocab(rows)
    print(f"Catégories ({len(categories)}) : {categories}")
    print(f"Compétences retenues ({len(skill_vocab)}) : {skill_vocab}")

    X, y, title_to_category = [], [], {}
    for r in rows:
        X.append(build_features(r, categories, skill_vocab))
        y.append(float(r["salary_avg_tnd"]))
        title_to_category[r["title"].strip().lower()] = r["category"].strip()

    X = np.array(X, dtype=float)
    y = np.array(y, dtype=float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=1,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, pred)
    r2 = r2_score(y_test, pred)
    print(f"\nÉvaluation (hold-out 20%) : MAE = {mae:.0f} TND | R² = {r2:.3f}")

    # Ré-entraînement final sur 100% des données pour le modèle livré.
    model.fit(X, y)

    payload = {
        "format": "piqbit_salary_v1",
        "model": model,
        "categories": categories,
        "title_to_category": title_to_category,
        "skill_vocab": skill_vocab,
        "target": "salary_avg_tnd",
        "currency": "TND",
        "period": "mensuel_brut",
        "metrics": {"mae": round(float(mae), 1), "r2": round(float(r2), 4)},
        "n_samples": len(rows),
    }
    with open(OUTPUT, "wb") as f:
        pickle.dump(payload, f)
    print(f"\nModèle sérialisé -> {OUTPUT}")
    print("Format : piqbit_salary_v1 (compatible SalaryPredictionService._predict_piqbit)")


if __name__ == "__main__":
    main()
