"""
Entraîne un modèle de prédiction de salaire (mensuel, TND) à partir du dataset
`datasets/tunisia_it_salaries.csv`, en tenant compte du métier (catégorie),
de la SÉNIORITÉ et de l'EXPÉRIENCE — puis sérialise un modèle que
`salary_prediction_service` charge automatiquement (format "piqbit_salary_v1").

Usage :
    pip install scikit-learn pandas numpy
    python train_salary_model.py                 # RandomForest (défaut)
    python train_salary_model.py --model gb      # GradientBoosting
    python train_salary_model.py --csv path.csv --out model.p
"""
import argparse
import pickle
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.join(HERE, "datasets", "tunisia_it_salaries.csv")
DEFAULT_OUT = os.path.join(HERE, "salary_model_piqbit.p")

SENIORITY_ORDER = {"Junior": 1, "Mid": 2, "Senior": 3, "Lead": 4}

# Vocabulaire de compétences TRANSVERSE (Dev, Data, Design, RH, Commercial,
# Finance, Marketing, Management). Multi-hot dérivable des `required_skills`.
SKILL_VOCAB = [
    # Dev / Tech
    "react", "angular", "node", "nestjs", "fastapi", "typescript", "python",
    "java", "php", "docker", "kubernetes", "aws", "sql", "spring", "flutter",
    # Data
    "machine learning", "spark", "power bi", "etl",
    # Design
    "figma",
    # RH
    "recrutement", "paie",
    # Commercial
    "crm", "négociation", "vente",
    # Marketing
    "seo", "content", "analytics",
    # Finance
    "comptabilité", "reporting", "budget",
    # Management
    "agile", "leadership",
]


def skill_vector(skills_text: str) -> list[int]:
    """Multi-hot du texte de compétences sur le vocabulaire (substring, lowercase)."""
    t = (skills_text or "").lower()
    return [1 if term in t else 0 for term in SKILL_VOCAB]


def build_features(df: pd.DataFrame, categories: list[str]) -> tuple[np.ndarray, list[str]]:
    """Construit la matrice de features X et la liste ordonnée des noms."""
    feat_names = ([f"cat_{c}" for c in categories]
                  + ["seniority", "experience_years"]
                  + [f"skill_{s}" for s in SKILL_VOCAB])
    rows = []
    for _, r in df.iterrows():
        vec = [1 if r["category"] == c else 0 for c in categories]
        vec.append(SENIORITY_ORDER.get(str(r["seniority"]), 2))
        emin = float(r.get("experience_years_min", 0) or 0)
        emax = float(r.get("experience_years_max", emin) or emin)
        vec.append((emin + emax) / 2.0)
        vec += skill_vector(str(r.get("top_skills", "")))
        rows.append(vec)
    return np.array(rows, dtype=float), feat_names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--model", choices=["rf", "gb"], default="rf")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df = df.dropna(subset=["salary_avg_tnd", "category", "seniority"])
    y = df["salary_avg_tnd"].astype(float).values

    categories = sorted(df["category"].unique().tolist())
    X, feat_names = build_features(df, categories)

    if args.model == "gb":
        model = GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, random_state=42)
    else:
        model = RandomForestRegressor(n_estimators=400, max_depth=None, min_samples_leaf=1, random_state=42)

    # Évaluation (validation croisée — petit dataset)
    try:
        mae = -cross_val_score(model, X, y, cv=min(5, len(df)), scoring="neg_mean_absolute_error").mean()
        print(f"Validation croisée — MAE ≈ {mae:.0f} TND/mois")
    except Exception as e:
        print(f"(CV ignorée: {e})")

    model.fit(X, y)
    pred = model.predict(X)
    print(f"Entraînement — MAE {mean_absolute_error(y, pred):.0f} TND · R² {r2_score(y, pred):.3f}")

    title_to_category = {str(t).lower(): c for t, c in zip(df["title"], df["category"])}

    payload = {
        "format": "piqbit_salary_v1",
        "model": model,
        "feature_names": feat_names,
        "categories": categories,
        "seniority_order": SENIORITY_ORDER,
        "skill_vocab": SKILL_VOCAB,
        "title_to_category": title_to_category,
        "currency": "TND",
        "period": "mensuel",
    }
    with open(args.out, "wb") as f:
        pickle.dump(payload, f)
    print(f"✓ Modèle sauvegardé : {args.out}")
    print("  → relancez l'API : le service le détecte et passe en mode ML.")


if __name__ == "__main__":
    main()
