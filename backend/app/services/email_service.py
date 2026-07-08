import smtplib
import logging
import asyncio
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings

logger = logging.getLogger(__name__)

# Read from pydantic-settings (which loads .env). Falling back to os.environ
# directly silently lost the values configured in the project's .env file.
SMTP_HOST = settings.SMTP_HOST
SMTP_PORT = settings.SMTP_PORT
SMTP_USER = settings.SMTP_USER
SMTP_PASS = settings.SMTP_PASSWORD
FROM_EMAIL = settings.EMAILS_FROM_EMAIL or SMTP_USER or "noreply@piqbit.com"
FROM_NAME = settings.EMAILS_FROM_NAME or "PIQBIT Recrutement"

_executor = ThreadPoolExecutor(max_workers=4)


def _send_sync(to_email: str, subject: str, html: str, attachments: list[tuple[str, bytes, str]] | None = None) -> bool:
    """
    attachments: list of (filename, content_bytes, mimetype) tuples.
    """
    if not SMTP_HOST or not SMTP_USER:
        logger.info(
            f"[EMAIL-DEV] To: {to_email} | Subject: {subject}\n"
            f"(attachments: {[a[0] for a in attachments] if attachments else 'none'})\n"
            f"Configure SMTP_HOST/SMTP_USER env vars to send real emails."
        )
        return True
    try:
        msg = MIMEMultipart("mixed" if attachments else "alternative")
        msg["Subject"] = subject
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"] = to_email

        if attachments:
            body = MIMEMultipart("alternative")
            body.attach(MIMEText(html, "html", "utf-8"))
            msg.attach(body)
            for filename, content, mimetype in attachments:
                maintype, subtype = (mimetype.split("/", 1) + ["octet-stream"])[:2]
                part = MIMEBase(maintype, subtype)
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename=\"{filename}\"")
                msg.attach(part)
        else:
            msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as exc:
        logger.error(f"Email send failed to {to_email}: {exc}")
        return False


async def send_email(
    to_email: str,
    subject: str,
    html: str,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _send_sync, to_email, subject, html, attachments)


# ── ICS helper ─────────────────────────────────────────────────────

def _ics_dt(dt: datetime) -> str:
    """Format as UTC for an .ics file (e.g. 20260611T090000Z)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(
    *,
    summary: str,
    description: str,
    start_at: datetime,
    end_at: datetime,
    organizer_email: str = FROM_EMAIL,
    attendee_email: str | None = None,
    location: str = "Visioconférence",
) -> bytes:
    """Build a minimal RFC-5545 .ics file as bytes."""
    uid = f"{uuid.uuid4()}@piqbit"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PIQBIT//Interview//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_ics_dt(datetime.now(timezone.utc))}",
        f"DTSTART:{_ics_dt(start_at)}",
        f"DTEND:{_ics_dt(end_at)}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description.replace(chr(10), ' ')}",
        f"LOCATION:{location}",
        f"ORGANIZER;CN={FROM_NAME}:mailto:{organizer_email}",
    ]
    if attendee_email:
        lines.append(f"ATTENDEE;CN={attendee_email};RSVP=TRUE:mailto:{attendee_email}")
    lines += [
        "STATUS:CONFIRMED",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ]
    return "\r\n".join(lines).encode("utf-8")


def _slot_rows(slots: list[str]) -> str:
    return "".join(
        f"<li style='margin:6px 0;padding:8px 14px;background:#f0f9ff;"
        f"border-left:3px solid #0ea5e9;border-radius:4px;'>"
        f"📅 {s}</li>"
        for s in slots
    )


async def send_interview_invitation(
    to_email: str,
    candidate_name: str,
    job_title: str,
    slots: list[str],
    message: str = "",
) -> bool:
    extra = f"<p style='color:#374151;'>{message}</p>" if message else ""
    html = f"""
    <div style='font-family:Arial,sans-serif;max-width:600px;margin:auto;'>
      <div style='background:#1e40af;color:#fff;padding:24px;border-radius:8px 8px 0 0;'>
        <h2 style='margin:0;'>Invitation à un entretien</h2>
        <p style='margin:4px 0 0;opacity:.85;'>{job_title}</p>
      </div>
      <div style='background:#fff;padding:28px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px;'>
        <p>Bonjour <strong>{candidate_name}</strong>,</p>
        <p>Suite à l'examen de votre candidature pour le poste de <strong>{job_title}</strong>,
           nous souhaitons vous rencontrer pour un entretien.</p>
        <p><strong>Créneaux disponibles :</strong></p>
        <ul style='padding-left:0;list-style:none;'>
          {_slot_rows(slots)}
        </ul>
        <p>Veuillez nous indiquer le créneau qui vous convient le mieux en répondant à cet email.</p>
        {extra}
        <hr style='border:none;border-top:1px solid #e5e7eb;margin:20px 0;'/>
        <p style='color:#6b7280;font-size:.85rem;'>
          Cordialement,<br/>L'équipe Recrutement — PIQBIT
        </p>
      </div>
    </div>
    """
    return await send_email(to_email, f"Entretien — {job_title}", html)


# ───────────────────────────────────────────────────────────────────
# NEW WORKFLOW : link-based invitation with public confirm page
# ───────────────────────────────────────────────────────────────────

def _fmt_slot_fr(dt: datetime) -> str:
    """Format an ISO datetime in French long form for emails."""
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        months = ["janvier", "février", "mars", "avril", "mai", "juin",
                  "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        return f"{days[dt.weekday()]} {dt.day} {months[dt.month - 1]} {dt.year} à {dt.strftime('%Hh%M')}"
    except Exception:
        return str(dt)


def _slot_link_rows(slots: list[datetime]) -> str:
    return "".join(
        f"<li style='margin:8px 0;padding:10px 14px;background:#f0f9ff;"
        f"border-left:3px solid #0ea5e9;border-radius:6px;font-size:14px;'>"
        f"📅 {_fmt_slot_fr(s)}</li>"
        for s in slots
    )


async def send_interview_invitation_link(
    *,
    to_email: str,
    candidate_name: str,
    job_title: str,
    slots: list[datetime],
    public_url: str,
    message: str = "",
    expires_at: datetime | None = None,
) -> bool:
    extra = f"<p style='color:#374151;margin:18px 0;'>{message}</p>" if message else ""
    exp = ""
    if expires_at:
        exp = (f"<p style='color:#9CA3AF;font-size:.82rem;margin-top:16px;'>"
               f"⏰ Ce lien est valable jusqu'au {_fmt_slot_fr(expires_at)}.</p>")
    html = f"""
    <div style='font-family:Inter,Arial,sans-serif;max-width:600px;margin:auto;'>
      <div style='background:#18534F;color:#FEEAA1;padding:28px;border-radius:12px 12px 0 0;text-align:center;'>
        <h2 style='margin:0;font-size:1.5rem;letter-spacing:-.02em;'>Invitation à un entretien</h2>
        <p style='margin:8px 0 0;color:rgba(254,234,161,.78);font-size:.92rem;'>{job_title}</p>
      </div>
      <div style='background:#FFFFFF;padding:32px 28px;border:1px solid #ECF8F6;border-top:none;border-radius:0 0 12px 12px;'>
        <p style='margin:0 0 16px;font-size:15px;'>Bonjour <strong>{candidate_name}</strong>,</p>
        <p style='font-size:14.5px;line-height:1.55;color:#1F2937;'>Suite à l'examen de votre candidature pour le poste de
           <strong>{job_title}</strong>, nous souhaitons vous rencontrer pour un entretien.</p>
        <p style='font-size:14.5px;color:#1F2937;margin-top:18px;'>👉 <strong>Cliquez sur le bouton ci-dessous</strong> pour choisir
           le créneau qui vous convient le mieux :</p>
        <div style='text-align:center;margin:28px 0;'>
          <a href="{public_url}" style='display:inline-block;padding:14px 30px;background:#18534F;color:#FEEAA1;
             border-radius:50px;font-weight:700;text-decoration:none;font-size:15px;'>
            ✔ Choisir mon créneau
          </a>
        </div>
        <p style='font-size:13px;color:#6B7280;text-align:center;margin:8px 0;'>
          ou copiez ce lien : <br/>
          <span style='font-family:monospace;font-size:12px;color:#18534F;word-break:break-all;'>{public_url}</span>
        </p>
        <p style='font-size:13.5px;color:#6B7280;margin-top:22px;'>Créneaux proposés :</p>
        <ul style='padding-left:0;list-style:none;margin:8px 0 0;'>
          {_slot_link_rows(slots)}
        </ul>
        {extra}
        {exp}
        <hr style='border:none;border-top:1px solid #ECF8F6;margin:24px 0;'/>
        <p style='color:#9CA3AF;font-size:.82rem;margin:0;'>
          Cordialement,<br/>L'équipe Recrutement — PIQBIT
        </p>
      </div>
    </div>
    """
    return await send_email(to_email, f"Invitation Entretien — {job_title}", html)


async def send_interview_confirmation_candidate(
    *,
    to_email: str,
    candidate_name: str,
    job_title: str,
    slot_start: datetime,
    slot_end: datetime,
) -> bool:
    ics = build_ics(
        summary=f"Entretien — {job_title}",
        description=f"Entretien avec {candidate_name} pour le poste {job_title}.",
        start_at=slot_start,
        end_at=slot_end,
        attendee_email=to_email,
    )
    html = f"""
    <div style='font-family:Inter,Arial,sans-serif;max-width:600px;margin:auto;'>
      <div style='background:#1F6F47;color:#fff;padding:28px;border-radius:12px 12px 0 0;text-align:center;'>
        <div style='font-size:2.4rem;margin-bottom:6px;'>✅</div>
        <h2 style='margin:0;font-size:1.4rem;'>Entretien confirmé</h2>
        <p style='margin:6px 0 0;opacity:.82;'>{job_title}</p>
      </div>
      <div style='background:#FFFFFF;padding:32px 28px;border:1px solid #ECF8F6;border-top:none;border-radius:0 0 12px 12px;'>
        <p style='margin:0 0 16px;font-size:15px;'>Bonjour <strong>{candidate_name}</strong>,</p>
        <p style='font-size:14.5px;color:#1F2937;line-height:1.55;'>Votre entretien est <strong>confirmé</strong> aux date et heure suivantes :</p>
        <div style='background:#ECF8F6;padding:20px 22px;border-radius:12px;border-left:4px solid #18534F;margin:18px 0;'>
          <p style='margin:0 0 6px;font-size:.78rem;color:#5B7B79;text-transform:uppercase;letter-spacing:.1em;font-weight:700;'>Date & heure</p>
          <p style='margin:0;font-size:18px;font-weight:700;color:#18534F;'>{_fmt_slot_fr(slot_start)}</p>
          <p style='margin:8px 0 0;font-size:.85rem;color:#5B7B79;'>📹 Format : Visioconférence</p>
        </div>
        <p style='font-size:13.5px;color:#6B7280;line-height:1.55;'>Un fichier d'invitation calendrier (.ics) est joint à cet email — vous pouvez
           l'ajouter à Google Calendar, Outlook ou Apple Calendar en un clic.</p>
        <p style='font-size:13.5px;color:#6B7280;line-height:1.55;'>💡 Besoin de modifier ou d'annuler ? Contactez-nous : rh@piqbit.tn</p>
        <hr style='border:none;border-top:1px solid #ECF8F6;margin:24px 0;'/>
        <p style='color:#9CA3AF;font-size:.82rem;margin:0;'>
          À très bientôt,<br/>L'équipe Recrutement — PIQBIT
        </p>
      </div>
    </div>
    """
    return await send_email(
        to_email,
        f"Confirmation entretien — {job_title}",
        html,
        attachments=[("entretien.ics", ics, "text/calendar")],
    )


async def send_interview_notification_rh(
    *,
    to_email: str,
    candidate_name: str,
    candidate_email: str,
    job_title: str,
    slot_start: datetime,
    slot_end: datetime,
) -> bool:
    html = f"""
    <div style='font-family:Inter,Arial,sans-serif;max-width:600px;margin:auto;'>
      <div style='background:#18534F;color:#FEEAA1;padding:24px;border-radius:12px 12px 0 0;'>
        <h2 style='margin:0;font-size:1.25rem;'>📅 Nouvelle confirmation d'entretien</h2>
      </div>
      <div style='background:#FFFFFF;padding:28px;border:1px solid #ECF8F6;border-top:none;border-radius:0 0 12px 12px;'>
        <p style='font-size:14.5px;color:#1F2937;'>
          <strong>{candidate_name}</strong> (<a style='color:#18534F;' href="mailto:{candidate_email}">{candidate_email}</a>)
          vient de confirmer un créneau d'entretien.
        </p>
        <div style='background:#ECF8F6;padding:16px 20px;border-radius:10px;border-left:4px solid #18534F;margin:14px 0;'>
          <p style='margin:0;color:#5B7B79;font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;'>Poste</p>
          <p style='margin:2px 0 10px;font-size:15px;font-weight:700;color:#18534F;'>{job_title}</p>
          <p style='margin:0;color:#5B7B79;font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;'>Date</p>
          <p style='margin:2px 0 0;font-size:15px;font-weight:700;color:#18534F;'>{_fmt_slot_fr(slot_start)}</p>
        </div>
        <p style='font-size:13px;color:#6B7280;'>Les autres créneaux proposés ont été libérés automatiquement.</p>
      </div>
    </div>
    """
    return await send_email(to_email, f"Entretien confirmé — {candidate_name}", html)


async def send_interview_cancellation(
    *,
    to_email: str,
    candidate_name: str,
    job_title: str,
    reason: str = "",
) -> bool:
    reason_block = (
        f"<p style='color:#374151;padding:12px 16px;background:#FEF3F2;border-left:3px solid #D45B5B;border-radius:6px;'>{reason}</p>"
        if reason else ""
    )
    html = f"""
    <div style='font-family:Inter,Arial,sans-serif;max-width:600px;margin:auto;'>
      <div style='background:#8C3838;color:#fff;padding:24px;border-radius:12px 12px 0 0;'>
        <h2 style='margin:0;font-size:1.3rem;'>Entretien annulé</h2>
        <p style='margin:6px 0 0;opacity:.82;'>{job_title}</p>
      </div>
      <div style='background:#FFFFFF;padding:28px;border:1px solid #ECF8F6;border-top:none;border-radius:0 0 12px 12px;'>
        <p>Bonjour <strong>{candidate_name}</strong>,</p>
        <p style='color:#1F2937;line-height:1.55;'>Nous vous informons que votre entretien prévu pour le poste de
          <strong>{job_title}</strong> a été <strong>annulé</strong>.</p>
        {reason_block}
        <p style='color:#6B7280;font-size:.9rem;'>Nous reviendrons vers vous prochainement si une nouvelle opportunité se présente.</p>
      </div>
    </div>
    """
    return await send_email(to_email, f"Entretien annulé — {job_title}", html)


async def send_rejection_email(
    to_email: str,
    candidate_name: str,
    job_title: str,
    message: str = "",
) -> bool:
    extra = f"<p style='color:#374151;'>{message}</p>" if message else ""
    html = f"""
    <div style='font-family:Arial,sans-serif;max-width:600px;margin:auto;'>
      <div style='background:#374151;color:#fff;padding:24px;border-radius:8px 8px 0 0;'>
        <h2 style='margin:0;'>Réponse à votre candidature</h2>
        <p style='margin:4px 0 0;opacity:.85;'>{job_title}</p>
      </div>
      <div style='background:#fff;padding:28px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px;'>
        <p>Bonjour <strong>{candidate_name}</strong>,</p>
        <p>Nous vous remercions pour l'intérêt que vous portez au poste de <strong>{job_title}</strong>
           et pour le temps consacré à votre candidature.</p>
        <p>Après examen attentif de votre profil, nous avons décidé de poursuivre avec d'autres candidats
           dont le profil correspond davantage à nos besoins actuels.</p>
        {extra}
        <p>Nous conservons votre dossier et n'hésiterons pas à vous recontacter si une opportunité
           adaptée à votre profil se présente.</p>
        <hr style='border:none;border-top:1px solid #e5e7eb;margin:20px 0;'/>
        <p style='color:#6b7280;font-size:.85rem;'>
          Cordialement,<br/>L'équipe Recrutement — PIQBIT
        </p>
      </div>
    </div>
    """
    return await send_email(to_email, f"Candidature — {job_title}", html)
