import uuid
from sqlalchemy import Column, String, Integer, DateTime, Index, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Embedding(Base):
    """
    Vecteur d'embedding d'une entité métier (offre d'emploi ou CV analysé),
    pour le matching sémantique CV↔offre et la recherche de candidats similaires.

    Stockage double, par conception :
    - `vector_json` (JSON) : portable partout (SQLite en tests, PostgreSQL sans
      extension) — sert au fallback de similarité calculée en Python (numpy).
    - colonne `vec vector(N)` (pgvector) : ajoutée par micro-migration au boot
      **uniquement** si l'extension `vector` est disponible sur PostgreSQL ;
      volontairement absente du modèle SQLAlchemy pour ne pas casser la
      création de schéma sur SQLite. Les recherches pgvector passent par du
      SQL brut (`ORDER BY vec <=> ...`).
    """
    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 'job_offer' | 'cv'
    entity_type = Column(String(20), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    # Nom du modèle qui a produit le vecteur (ou 'hash-v1' pour le fallback) —
    # deux vecteurs ne sont comparables que s'ils viennent du même backend.
    model = Column(String(150), nullable=False)
    dim = Column(Integer, nullable=False)
    vector_json = Column(JSON, nullable=False)
    # Aperçu du texte encodé (debug / explicabilité dans l'UI).
    text_preview = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_embeddings_entity", "entity_type", "entity_id", unique=True),
        Index("ix_embeddings_type_model", "entity_type", "model"),
    )
