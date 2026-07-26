# PIQBIT — API backend

API FastAPI de la plateforme de recrutement PIQBIT : gestion des offres,
analyse de CV assistée par IA, scoring des candidats, entretiens, négociation
salariale et contrats.

---

## Sommaire

- [Prérequis](#prérequis)
- [Démarrage rapide (Docker)](#démarrage-rapide-docker)
- [Développement local](#développement-local)
- [Variables d'environnement](#variables-denvironnement)
- [Migrations de base de données](#migrations-de-base-de-données)
- [Tests](#tests)
- [Architecture](#architecture)
- [Dépannage](#dépannage)

---

## Prérequis

| Outil | Version | Remarque |
|---|---|---|
| Python | 3.14 | Version de référence du `requirements.txt` |
| PostgreSQL | 16+ | Avec l'extension `pgvector` de préférence (voir plus bas) |
| Redis | 7+ | Cache et limitation de tentatives de connexion |
| Docker | 24+ | Pour la pile complète |

---

## Démarrage rapide (Docker)

```bash
# Depuis la racine du dépôt
cp backend/.env.example backend/.env   # puis renseigner SECRET_KEY
docker compose --profile app up -d --build
```

L'application est alors disponible sur **http://localhost:8080**
(nginx sert le frontend et proxifie `/api/` vers le backend).

Sans le profil `app`, seule l'infrastructure démarre — pratique quand on lance
backend et frontend à la main :

```bash
docker compose up -d          # PostgreSQL + Redis uniquement
```

---

## Développement local

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt

cp .env.example .env             # renseigner SECRET_KEY au minimum
docker compose up -d             # PostgreSQL + Redis (depuis la racine)

alembic upgrade head             # créer / mettre à jour le schéma
uvicorn app.main:app --reload
```

Documentation interactive : http://localhost:8000/docs

### Attention aux ports PostgreSQL

Le conteneur PostgreSQL est publié sur **5434**, pas 5432. Ce décalage est
volontaire : plusieurs postes de développement font tourner des services
PostgreSQL Windows qui occupent déjà 5432 et 5433. Sous Windows, plusieurs
processus peuvent se lier au même port sans erreur — l'application semble
alors dialoguer avec le conteneur alors qu'elle parle en réalité au serveur
Windows, ce qui provoque des écarts de schéma très déroutants.

Vérifier à quel serveur on est réellement connecté :

```bash
docker exec piqbit-postgres psql -U postgres -d piqbit \
  -c "SELECT current_setting('data_directory');"
# Conteneur  -> /var/lib/postgresql/data
# PostgreSQL Windows -> C:/Program Files/PostgreSQL/xx/data
```

---

## Variables d'environnement

Copier `.env.example` vers `.env`. Le fichier `.env` est ignoré par git et ne
doit **jamais** être committé.

### Obligatoires

| Variable | Description |
|---|---|
| `SECRET_KEY` | Clé de signature des JWT. Générer avec `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DATABASE_URL` | URL PostgreSQL, pilote **asyncpg** : `postgresql+asyncpg://user:pass@host:port/base` |

### Importantes en production

| Variable | Défaut | Description |
|---|---|---|
| `ALLOWED_ORIGINS` | `localhost:4200,localhost:3000` | Domaines autorisés à appeler l'API, séparés par des virgules |
| `ALLOW_LOCALHOST_ORIGINS` | `true` | **Passer à `false`** : sinon tout port localhost reste accepté |
| `DEBUG` | `false` | Ne jamais activer en production |

Inutile de renseigner `ALLOWED_ORIGINS` dans le déploiement Docker fourni :
frontend et backend partagent la même origine via nginx, aucune requête n'est
donc cross-origin.

### Optionnelles

| Variable | Effet si absente |
|---|---|
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` | Les e-mails sont journalisés au lieu d'être envoyés — l'application reste fonctionnelle |
| `GOOGLE_CLIENT_ID` | La connexion Google est indisponible, l'authentification classique fonctionne |
| `EMBEDDING_MODEL_NAME` | Repli sur un encodage par hachage, moins précis mais opérationnel |

---

## Migrations de base de données

Le schéma est géré **exclusivement** par Alembic. L'application ne crée ni ne
modifie aucune table : au démarrage, elle vérifie que la base porte bien la
dernière révision et journalise une erreur explicite sinon.

```bash
alembic upgrade head                          # appliquer les migrations
alembic revision --autogenerate -m "message"  # générer après modif de modèle
alembic downgrade -1                          # revenir d'un cran
alembic current                               # révision actuelle
```

> **Toujours relire une migration générée avant de l'appliquer.**
> L'autogenerate ne détecte pas les renommages (il produit un `DROP` suivi
> d'un `ADD`, avec perte de données) et gère mal certains types spécifiques.

### Ajouter un modèle

Tout nouveau module de modèle **doit** être importé dans
`app/models/__init__.py`. Sans cet import, `Base.metadata` l'ignore : Alembic
ne verra pas la table, et — plus grave — si la metadata est vide, il générera
une migration qui supprime tout le schéma existant.

### pgvector

La migration `9b1c4d2e7f30` ajoute la colonne `embeddings.vec` et un index
HNSW pour la recherche sémantique vectorielle. Elle est conditionnelle : si
l'extension `vector` est absente, la migration passe sans échouer et le
service sémantique bascule sur un calcul de cosinus en Python — plus lent,
mais fonctionnellement équivalent.

Vérifier l'état :

```sql
SELECT count(*) FROM pg_extension WHERE extname = 'vector';
```

---

## Tests

```bash
pytest                       # suite complète (~19 min)
pytest tests/test_auth.py    # un fichier
pytest -q --no-header        # sortie compacte
```

110 tests couvrant authentification, recrutement, entretiens, contrats,
négociation, notifications, rapports, sémantique et prédiction salariale.

> Les tests utilisent un fichier SQLite partagé (`./test.db`) et ne peuvent
> donc **pas** tourner en parallèle : deux exécutions simultanées se
> disputeraient le fichier et produiraient des erreurs
> « table already exists » trompeuses.

---

## Architecture

```
app/
├── api/v1/endpoints/   # Routes HTTP (17 modules, ~130 routes)
├── agents/             # Agents IA (scoring, analyse, décision, rapports)
├── core/               # Configuration, sécurité, dépendances
├── db/                 # Session SQLAlchemy, base déclarative, amorçage
├── models/             # Modèles ORM — __init__.py DOIT tous les importer
├── schemas/            # Schémas Pydantic (validation entrée/sortie)
└── services/           # Logique métier (23 services)
```

Points notables :

- **Scoring des candidats** — pondération compétences / expérience / formation,
  paramétrable par offre.
- **Prédiction salariale** — modèle scikit-learn entraîné
  (`salary_model_piqbit.p`), avec estimateur heuristique en repli.
- **Recherche sémantique** — embeddings `sentence-transformers`, index
  pgvector natif ou cosinus Python selon disponibilité.
- **Notifications temps réel** — WebSocket avec registre de connexions par
  utilisateur.

---

## Dépannage

| Symptôme | Cause probable |
|---|---|
| `SCHÉMA DÉSYNCHRONISÉ` au démarrage | Migrations non appliquées → `alembic upgrade head` |
| `asyncio extension requires an async driver` | `DATABASE_URL` sans `+asyncpg` |
| Alembic génère une migration qui supprime tout | Un modèle n'est pas importé dans `app/models/__init__.py` |
| `No module named 'alembic.config'` | Un `__init__.py` traîne dans `alembic/` et masque la bibliothèque |
| Les tables n'apparaissent pas dans le conteneur | Connexion au PostgreSQL Windows au lieu du conteneur (voir *Attention aux ports*) |
| Les e-mails ne partent pas | `SMTP_HOST`/`SMTP_USER` non renseignés — comportement normal en développement |
