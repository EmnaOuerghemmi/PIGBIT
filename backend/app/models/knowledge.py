import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Index, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class KnowledgeEntry(Base):
    """
    Entrée de la base de connaissances RH (FAQ, processus, politiques).
    Sert de corpus au moteur CAG : chaque entrée est embeddée **une seule fois**
    (vecteur mis en cache dans `vector_json`) puis interrogée par similarité.
    """
    __tablename__ = "knowledge_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    # RECRUTEMENT | ENTRETIEN | CANDIDATURE | PROCESS | POLITIQUE | AUTRE
    category = Column(String(40), nullable=False, default="AUTRE")
    source = Column(String(200), nullable=True)  # référence lisible (doc, page…)

    # Cache d'embedding : calculé une fois, réutilisé à chaque question.
    vector_json = Column(JSON, nullable=True)
    model = Column(String(150), nullable=True)  # backend qui a produit le vecteur

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_knowledge_category", "category"),)


class CVChunk(Base):
    """
    Passage (chunk) d'un CV analysé, embeddé et mis en cache pour le Q&A extractif.
    Découpé une fois (à la première question) puis réutilisé — c'est le volet
    « cache » du CAG appliqué aux CV.
    """
    __tablename__ = "cv_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    vector_json = Column(JSON, nullable=False)
    model = Column(String(150), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_cv_chunks_app_idx", "application_id", "chunk_index", unique=True),
    )
