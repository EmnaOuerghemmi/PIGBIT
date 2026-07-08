# Dataset — Salaires Tunisie (référence, tous métiers)

**Fichier :** `tunisia_it_salaries.csv` · **131 lignes** (37 métiers × séniorités + 7 postes issus d'une enquête).

Toutes les valeurs sont des salaires **mensuels bruts (TND)** — `period = mensuel_brut`.

### Sources (`source`)
- `estimation_marche_TN_reference` — barème de référence (fourchettes publiques connues).
- `salaryexplorer_TN_2026 (annuel→mensuel, 337 répondants)` — données d'enquête fournies, **annuelles converties en mensuel (÷12)** ; les fourchettes source étant corrompues, min/max = moyenne ±20 %.

Couvre **tous les besoins de l'entreprise**, pas seulement l'IT :
`Tech, Data, Design, Management, RH, Commercial, Marketing, Finance, Admin, Support`
(ex. HR Manager, Recruiter, Sales Manager, Marketing Manager, Accountant, Project Manager…).
Voir la colonne `category`.

## ⚠️ Provenance & honnêteté
Ces données sont des **estimations de référence** du marché IT tunisien, basées sur
les fourchettes **publiquement connues** (≈ 2024–2026). Elles **ne proviennent PAS**
d'un scraping de LinkedIn ou d'autres sites (interdit par leurs CGU). Colonne
`source = estimation_marche_TN_reference`.

À utiliser comme **base de calibrage / démo**, pas comme vérité statistique.

## Colonnes
| Colonne | Description |
|---|---|
| `title` | Intitulé du poste |
| `category` | Famille : Tech / Data / Design / Management / RH / Commercial / Marketing / Finance / Admin / Support |
| `seniority` | Junior / Mid / Senior / Lead |
| `experience_years_min/max` | Fourchette d'expérience attendue |
| `salary_min/avg/max_tnd` | Salaire **mensuel brut** estimé (TND) |
| `currency` / `period` | TND / mensuel_brut |
| `education` | Niveau d'études typique |
| `top_skills` | Compétences clés (séparées par des virgules) |
| `region` | Tunisie |
| `source` | Origine de l'estimation |

## Pour obtenir de vraies données (légalement)
- **APIs/officiel** : exports d'agrégateurs d'offres qui le permettent, enquêtes
  de rémunération (cabinets RH), open data.
- **Sites avec autorisation** : respecter `robots.txt` et les CGU ; privilégier
  les flux RSS / pages publiques explicitement ouvertes.
- **LinkedIn** : le scraping est **interdit** par les CGU — passer par leurs API
  officielles si éligible.

## Brancher un vrai modèle ML
Ce CSV peut entraîner un modèle simple (ex. régression sur métier+séniorité+skills)
puis être sérialisé en `model_comprehensive_serializable.p` — le service
`salary_prediction_service` le détecte automatiquement et bascule du mode
heuristique au mode ML. (Nécessite `pip install scikit-learn pandas numpy`.)
