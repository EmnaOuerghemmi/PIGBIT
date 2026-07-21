"""
Génération PDF d'un contrat de travail tunisien (CDI/CDD/Stage/Alternance)
+ certificat de signature électronique — reportlab, 100 % hors-ligne.

Le PDF reprend la structure d'un contrat de travail de droit tunisien
(soussignés, articles 1 à 17, mention « lu et approuvé », signatures), et
l'en-tête société est configurable (`COMPANY_*` dans les settings).
"""
import base64
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, HRFlowable, PageBreak,
)

from app.core.config import settings

INK = colors.HexColor("#1F2D2D")
MUTED = colors.HexColor("#788888")
GOLD = colors.HexColor("#B98A2E")
GREEN = colors.HexColor("#3DA76F")
LINE = colors.HexColor("#D8CFBB")
SURFACE = colors.HexColor("#FBF8F1")

TYPE_TITLES = {
    "CDI": "CONTRAT DE TRAVAIL À DURÉE INDÉTERMINÉE",
    "CDD": "CONTRAT DE TRAVAIL À DURÉE DÉTERMINÉE",
    "STAGE": "CONVENTION DE STAGE",
    "ALTERNANCE": "CONTRAT D'ALTERNANCE",
}

FERIES = [
    ("Jour de l'an", "1 janvier"), ("Fête de la Révolution", "14 janvier"),
    ("Fête de l'Indépendance", "20 mars"), ("Fête des Martyrs", "9 avril"),
    ("Fête du Travail", "1 mai"), ("Fête de la République", "25 juillet"),
    ("Fête de la Femme", "13 août"), ("Fête de l'Évacuation", "15 octobre"),
]


def _v(x):
    return x.value if hasattr(x, "value") else str(x)


def _fmt_date(dt, default="__/__/____"):
    return dt.strftime("%d/%m/%Y") if dt else default


def _fmt_money(amount, currency="TND"):
    return f"{amount:,.0f} {currency}".replace(",", " ")


def _styles():
    base = getSampleStyleSheet()
    return {
        "doctitle": ParagraphStyle("dt", parent=base["Title"], textColor=INK, fontSize=15,
                                   alignment=1, spaceAfter=3 * mm, leading=19),
        "center": ParagraphStyle("c", parent=base["Normal"], textColor=INK, fontSize=10,
                                  alignment=1, leading=14),
        "art": ParagraphStyle("a", parent=base["Heading3"], textColor=GOLD, fontSize=10.5,
                              spaceBefore=4 * mm, spaceAfter=1 * mm),
        "body": ParagraphStyle("b", parent=base["Normal"], textColor=INK, fontSize=9.5,
                               leading=14, alignment=4, spaceAfter=1.5 * mm),
        "li": ParagraphStyle("li", parent=base["Normal"], textColor=INK, fontSize=9.5,
                             leading=13.5, leftIndent=8 * mm, bulletIndent=3 * mm, spaceAfter=1 * mm),
        "small": ParagraphStyle("sm", parent=base["Normal"], textColor=MUTED, fontSize=8.5, leading=12),
        "cert": ParagraphStyle("ce", parent=base["Title"], textColor=GREEN, fontSize=15, spaceAfter=1 * mm),
    }


def _decode_signature(data_uri):
    try:
        if "," in data_uri:
            data_uri = data_uri.split(",", 1)[1]
        return BytesIO(base64.b64decode(data_uri))
    except Exception:
        return None


def render_contract_pdf(*, contract, candidate_name, candidate_email,
                        job_title, company_name=None):
    st = _styles()
    company = company_name or settings.COMPANY_NAME
    manager = settings.COMPANY_MANAGER
    tax_id = settings.COMPANY_TAX_ID
    address = settings.COMPANY_ADDRESS
    city = settings.COMPANY_CITY

    ctype = _v(contract.contract_type)
    status = _v(contract.status)
    birth = _fmt_date(getattr(contract, "employee_birth_date", None))
    cin = getattr(contract, "employee_cin", None) or "________"
    cin_issue = _fmt_date(getattr(contract, "employee_cin_issue_date", None))
    emp_addr = getattr(contract, "employee_address", None) or "________"
    fonction = contract.position or job_title
    start = _fmt_date(contract.start_date)
    salaire = _fmt_money(contract.salary, contract.currency)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=16 * mm, bottomMargin=15 * mm,
        title=f"Contrat — {candidate_name}", author=company,
    )
    S = []

    # ── Titre + soussignés ────────────────────────────────────────────────────
    S += [
        Paragraph(TYPE_TITLES.get(ctype, TYPE_TITLES["CDI"]), st["doctitle"]),
        Paragraph("<b>ENTRE LES SOUSSIGNÉS</b>", st["center"]),
        Spacer(1, 2 * mm),
    ]
    matricule = f"au matricule fiscal n° {tax_id}, " if tax_id else ""
    S += [
        Paragraph(
            f"La société <b>{company}</b>, {matricule}élisant domicile à {address}, "
            f"représentée par son gérant <b>M. {manager}</b>, ci-après dénommée "
            "« <b>L'Employeur</b> »,", st["body"]),
        Paragraph("<b>D'UNE PART</b>", st["center"]),
        Spacer(1, 1.5 * mm),
        Paragraph("Et", st["center"]),
        Spacer(1, 1.5 * mm),
        Paragraph(
            f"<b>M./Mme {candidate_name}</b>, né(e) le <b>{birth}</b>, titulaire de la "
            f"C.I.N. n° <b>{cin}</b> délivrée le {cin_issue}, demeurant à {emp_addr}, "
            "ci-après dénommé(e) « <b>L'Employé(e)</b> »,", st["body"]),
        Paragraph("<b>D'AUTRE PART</b>", st["center"]),
        Spacer(1, 2 * mm),
        HRFlowable(width="100%", color=LINE, thickness=0.7, spaceAfter=2 * mm),
        Paragraph("Il a été arrêté et convenu ce qui suit :", st["body"]),
    ]

    def art(num, title, *paras):
        S.append(Paragraph(f"Article {num} — {title}", st["art"]))
        for p in paras:
            S.append(Paragraph(p, st["body"]))

    art("1", "Principes généraux",
        "Les parties signataires du présent contrat s'engagent à promouvoir les "
        "intérêts de l'entreprise et à œuvrer pour son développement, dans le cadre "
        "du respect des dispositions légales et conventionnelles applicables sur le "
        "territoire tunisien, de la bonne foi contractuelle et de l'éthique professionnelle.")

    art("2", "Déclarations sur l'honneur",
        "L'employé(e) déclare sur l'honneur être libre de tout engagement légalement "
        "incompatible avec le présent contrat, toute fausse déclaration sur ce point "
        "pouvant entraîner la résiliation immédiate et de plein droit du présent "
        "contrat. Il/elle s'engage à consacrer tous ses soins et diligences "
        "professionnels pour le compte de l'employeur.")

    if ctype == "CDD" and contract.end_date:
        art("3", "Fonctions et durée",
            f"L'employé(e) est engagé(e) pour exercer les fonctions de <b>{fonction}</b>, "
            f"à compter du <b>{start}</b>. Le présent contrat est conclu pour une durée "
            f"déterminée prenant fin le <b>{_fmt_date(contract.end_date)}</b>.")
    else:
        art("3", "Fonctions",
            f"L'employé(e) est engagé(e) par l'employeur pour exercer les fonctions de "
            f"<b>{fonction}</b> sur tout le territoire tunisien, à compter du <b>{start}</b>.")

    art("4", "Durée du contrat",
        f"Le présent contrat est conclu pour une période "
        f"{'indéterminée' if ctype == 'CDI' else 'déterminée'}, assortie d'une période "
        f"d'essai de <b>{contract.trial_period_months} mois</b> renouvelable une seule "
        "fois, au cours de laquelle il pourra prendre fin à la volonté de l'une ou "
        "l'autre des parties, sans indemnité, en respectant un préavis d'un mois. Toute "
        "suspension de l'exécution du contrat entraînera une prolongation de la période "
        "d'essai d'une durée équivalente.")

    S.append(Paragraph("Article 5 — Obligations professionnelles", st["art"]))
    S.append(Paragraph("L'employé(e) s'engage à :", st["body"]))
    for item in [
        "Consacrer tout son temps, pendant l'horaire de travail, au service où il/elle est affecté(e) ;",
        "Respecter scrupuleusement le règlement, les procédures internes et les notes de service ;",
        "Se conformer strictement aux instructions et directives de sa hiérarchie ;",
        "Observer une discrétion absolue et le secret professionnel, sans limitation dans le "
        "temps, y compris après la fin du présent contrat ;",
        "Adopter une conduite professionnelle exemplaire et s'interdire tout acte pouvant "
        "porter atteinte aux intérêts légitimes de l'employeur ;",
        "Communiquer à l'employeur tous les documents nécessaires à son dossier administratif "
        "et l'informer de toute modification de sa situation.",
    ]:
        S.append(Paragraph(item, st["li"], bulletText="•"))

    art("6", "Rémunération",
        f"L'employé(e) percevra un salaire mensuel net de <b>{salaire}</b>. Cette "
        "rémunération comprend toutes les primes prévues par le droit du travail. Toute "
        "modification ultérieure fera l'objet d'un avenant au présent contrat.")

    S.append(Paragraph("Article 7 — Horaire de travail", st["art"]))
    S.append(Paragraph(
        f"Il est fait application d'un régime de travail de <b>{contract.weekly_hours} heures "
        "par semaine</b>. L'employé(e) accepte l'horaire de travail affiché au sein de la "
        "société. Les jours fériés chômés et payés sont les suivants :", st["body"]))
    frows = [[a, b] for a, b in FERIES]
    ftab = Table([[frows[i][0], frows[i][1], (frows[i + 1][0] if i + 1 < len(frows) else ""),
                   (frows[i + 1][1] if i + 1 < len(frows) else "")] for i in range(0, len(frows), 2)],
                 colWidths=[42 * mm, 30 * mm, 42 * mm, 30 * mm])
    ftab.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE), ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"), ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
    ]))
    S += [ftab, Spacer(1, 1.5 * mm)]

    art("8", "Congés",
        "Le régime de congés payés est de <b>22 jours ouvrés</b> par an. Le choix des "
        "périodes de congé est déterminé par accord entre les parties, compte tenu des "
        "nécessités de service.")
    art("9", "Biens de l'entreprise",
        "L'employé(e) est tenu(e) de garder en parfait état les biens, matériels, "
        "documents et dossiers de l'entreprise en sa possession ou sous son contrôle, et "
        "d'informer la gérance de tout manquement à cette règle.")
    art("10", "Résiliation du contrat",
        "Le présent contrat pourra être résilié de plein droit : d'un commun accord des "
        "deux parties ; par démission de l'employé(e) notifiée trois (3) mois à l'avance ; "
        "ou pour faute grave, insuffisance professionnelle, manque de discrétion ou "
        "indiscipline, auquel cas le licenciement n'est pas considéré comme abusif.")
    art("11", "Obligation de fidélité",
        "Pendant la durée du présent contrat, l'employé(e) s'engage à ne participer, sous "
        "quelque forme que ce soit, à aucune activité susceptible de concurrencer, "
        "directement ou indirectement, celle de la société qui l'emploie.")
    art("12", "Modifications portées au contrat",
        "Toute annulation, modification ou remplacement d'un article, décidé d'un commun "
        "accord, fera l'objet d'une décision écrite annexée au présent contrat, sans "
        "affecter les autres articles qui demeurent applicables.")
    art("13", "Élection de domicile",
        "Les deux signataires élisent domicile chacun à l'adresse ci-dessus indiquée.")
    art("14", "Litige",
        "En cas de contestation quant à l'interprétation ou l'exécution du présent "
        f"contrat, les tribunaux de {city} seront seuls compétents.")
    art("15", "Non-concurrence",
        "Compte tenu de la nature des fonctions exercées, le Salarié s'engage, "
        "postérieurement à la rupture de son contrat quelle qu'en soit la cause, à ne pas "
        "exercer directement ou indirectement de fonctions similaires ou concurrentes de "
        "celles exercées au sein de la société. Cet engagement est limité au territoire "
        "tunisien, à la clientèle et aux prospects de la société, pour une durée de deux ans.")

    S += [
        Spacer(1, 2 * mm),
        Paragraph(
            "Le présent contrat entre en vigueur dès sa signature par les deux parties. "
            "Il est rédigé en deux (2) exemplaires originaux.", st["body"]),
        Paragraph(f"Fait à {city}, le {_fmt_date(datetime.now())}.", st["body"]),
        Spacer(1, 2 * mm),
        Paragraph(
            "<i>Mention manuscrite requise du salarié : « Lu et approuvé ».</i>", st["small"]),
    ]

    # ── Bloc signatures ───────────────────────────────────────────────────────
    sig = Paragraph("<i>Signature en attente</i>", st["small"])
    if status in ("SIGNED", "ACTIVE") and contract.signature_image:
        img = _decode_signature(contract.signature_image)
        if img:
            try:
                sig = Image(img, width=46 * mm, height=20 * mm, kind="proportional")
            except Exception:
                sig = Paragraph(f"<b>{contract.signer_name}</b> — signé", st["small"])

    sigtab = Table([
        ["L'Employeur — Le Gérant", "L'Employé(e)"],
        [Paragraph(f"<b>{manager}</b><br/>{company}", st["small"]), sig],
        ["", Paragraph(
            (f"<b>{contract.signer_name or candidate_name}</b>" +
             (f"<br/>« Lu et approuvé »<br/>Signé le {contract.signed_at.strftime('%d/%m/%Y %H:%M UTC')}"
              if contract.signed_at else "")), st["small"])],
    ], colWidths=[80 * mm, 80 * mm])
    sigtab.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 9.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), INK), ("TOPPADDING", (0, 1), (-1, 1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, LINE),
    ]))
    S += [Spacer(1, 4 * mm), sigtab]

    # ── Certificat de signature électronique ──────────────────────────────────
    if status in ("SIGNED", "ACTIVE") and contract.certificate_id:
        S.append(PageBreak())
        S += _certificate(st, contract, candidate_name, candidate_email, company)

    doc.build(S)
    return buf.getvalue()


def _certificate(st, contract, candidate_name, candidate_email, company):
    audit = [
        ["Document", f"Contrat de travail — réf. {str(contract.id)[:8].upper()}"],
        ["Signataire", contract.signer_name or candidate_name],
        ["Email", candidate_email],
        ["Date de signature", contract.signed_at.strftime("%d/%m/%Y à %H:%M:%S UTC") if contract.signed_at else "—"],
        ["Adresse IP", contract.signer_ip or "—"],
        ["Navigateur", (contract.signer_user_agent or "—")[:70]],
        ["Empreinte du document (SHA-256)", contract.document_hash or "—"],
        ["Identifiant de certificat", contract.certificate_id or "—"],
    ]
    t = Table(audit, colWidths=[62 * mm, 98 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), SURFACE), ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
        ("TEXTCOLOR", (1, 0), (1, -1), INK), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (1, -2), (1, -1), "Courier"), ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return [
        Paragraph("✓ Certificat de signature électronique", st["cert"]),
        Paragraph(
            "Ce certificat atteste que le document ci-avant a été signé électroniquement "
            "selon un procédé de signature simple (consentement explicite, horodatage et "
            "scellement par empreinte cryptographique).", st["small"]),
        Spacer(1, 4 * mm), t, Spacer(1, 4 * mm),
        Paragraph(
            "L'intégrité du document est garantie par l'empreinte SHA-256 ci-dessus : toute "
            f"modification des termes invaliderait cette empreinte. Émis par {company}.", st["small"]),
    ]
