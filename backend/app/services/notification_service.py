"""
Service de notifications in-app + temps réel (WebSocket).

Deux helpers de haut niveau couvrent les deux flux demandés :
- `notify_user(...)`      : notifie un destinataire précis (ex. le candidat).
- `notify_admins(...)`    : notifie **tous les comptes ADMIN** — utilisé quand
  un compte RH_MANAGER/RH_STAFF effectue une action significative. N'envoie
  rien si l'acteur est lui-même ADMIN (un admin n'a pas besoin d'être notifié
  de ses propres actions).
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import User, UserRole
from app.services.notification_ws import notification_ws_manager

# Libellés FR partagés (candidature) — utilisés dans les messages de notification.
APPLICATION_STATUS_LABELS = {
    "PENDING": "En attente",
    "REVIEWED": "Examinée",
    "ACCEPTED": "Acceptée",
    "REJECTED": "Rejetée",
    "INTERVIEW_SCHEDULED": "Entretien planifié",
    "NEGOTIATION": "Négociation",
}


def _serialize(n: Notification) -> dict:
    return {
        "id": str(n.id),
        "type": n.type,
        "title": n.title,
        "message": n.message,
        "link": n.link,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "actor_id": str(n.actor_id) if n.actor_id else None,
    }


class NotificationService:

    async def create(
        self,
        db: AsyncSession,
        *,
        recipient_id: UUID,
        type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        actor_id: Optional[UUID] = None,
        broadcast: bool = True,
    ) -> Notification:
        notif = Notification(
            recipient_id=recipient_id, actor_id=actor_id,
            type=type, title=title, message=message, link=link,
        )
        db.add(notif)
        await db.flush()
        await db.refresh(notif)
        if broadcast:
            await notification_ws_manager.send_to_user(
                recipient_id, {"event": "notification", "data": _serialize(notif)}
            )
        return notif

    async def notify_user(
        self,
        db: AsyncSession,
        *,
        recipient_id: UUID,
        type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        actor_id: Optional[UUID] = None,
    ) -> Notification:
        """Notifie un destinataire précis (ex. le candidat concerné)."""
        return await self.create(
            db, recipient_id=recipient_id, type=type, title=title,
            message=message, link=link, actor_id=actor_id,
        )

    async def notify_admins(
        self,
        db: AsyncSession,
        *,
        actor: User,
        type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
    ) -> list[Notification]:
        """
        Notifie tous les comptes ADMIN d'une action réalisée par un compte
        RH (RH_MANAGER/RH_STAFF). No-op si l'acteur est lui-même ADMIN.
        """
        if actor.role == UserRole.ADMIN:
            return []

        admin_ids = (
            await db.execute(
                select(User.id).where(User.role == UserRole.ADMIN, User.deleted_at.is_(None))
            )
        ).scalars().all()

        created: list[Notification] = []
        for admin_id in admin_ids:
            created.append(await self.create(
                db, recipient_id=admin_id, type=type, title=title,
                message=message, link=link, actor_id=actor.id,
            ))
        return created

    # ── Lecture ───────────────────────────────────────────────────────────────

    async def list_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> dict:
        query = select(Notification).where(Notification.recipient_id == user_id)
        count_query = select(func.count(Notification.id)).where(Notification.recipient_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read.is_(False))
            count_query = count_query.where(Notification.is_read.is_(False))

        total = (await db.execute(count_query)).scalar_one()
        rows = (
            await db.execute(
                query.order_by(Notification.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        pages = max(1, -(-total // page_size))
        return {
            "items": [_serialize(n) for n in rows],
            "total": total, "page": page, "pages": pages, "page_size": page_size,
        }

    async def unread_count(self, db: AsyncSession, user_id: UUID) -> int:
        return (
            await db.execute(
                select(func.count(Notification.id)).where(
                    Notification.recipient_id == user_id, Notification.is_read.is_(False)
                )
            )
        ).scalar_one()

    # ── Écriture ──────────────────────────────────────────────────────────────

    async def mark_read(self, db: AsyncSession, *, notification_id: UUID, user_id: UUID) -> Optional[Notification]:
        notif = (
            await db.execute(
                select(Notification).where(
                    Notification.id == notification_id, Notification.recipient_id == user_id
                )
            )
        ).scalar_one_or_none()
        if not notif:
            return None
        if not notif.is_read:
            notif.is_read = True
            notif.read_at = func.now()
            await db.flush()
            await db.refresh(notif)
        return notif

    async def mark_all_read(self, db: AsyncSession, user_id: UUID) -> int:
        result = await db.execute(
            update(Notification)
            .where(Notification.recipient_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True, read_at=func.now())
        )
        return result.rowcount or 0

    async def delete(self, db: AsyncSession, *, notification_id: UUID, user_id: UUID) -> bool:
        notif = (
            await db.execute(
                select(Notification).where(
                    Notification.id == notification_id, Notification.recipient_id == user_id
                )
            )
        ).scalar_one_or_none()
        if not notif:
            return False
        await db.delete(notif)
        await db.flush()
        return True


notification_service = NotificationService()
