"""
AquaDiag - Génération du rapport de diagnostic au format PDF (reportlab).
"""

import io
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from diagnostic import NATURES, libelle, libelle_etape, unite

BLEU = colors.HexColor("#0066cc")
ROUGE = colors.HexColor("#c62828")
GRIS = colors.HexColor("#f0f2f6")

# Les polices standard du PDF ne contiennent ni émojis ni indices Unicode :
# on les remplace par des équivalents lisibles.
_REMPLACEMENTS = str.maketrans({
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    "⁻": "-", "⁺": "+", "↓": "", "→": "->", "≤": "<=", "≥": ">=", "–": "-", "—": "-",
    "−": "-", "·": ".", "µ": "u", "μ": "u", "’": "'", "³": "3", "≈": "env. ",
})
_EMOJIS = re.compile("[\U0001F000-\U0001FFFF⌀-⏿☀-➿⬀-⯿️‍]")


def texte_pdf(valeur):
    """Rend un texte compatible avec les polices PDF standard et échappe le XML."""
    texte = _EMOJIS.sub("", str(valeur)).translate(_REMPLACEMENTS).strip()
    return texte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles():
    base = getSampleStyleSheet()
    return {
        "titre": ParagraphStyle("titre", parent=base["Title"], textColor=BLEU, fontSize=20),
        "sous_titre": ParagraphStyle("sous_titre", parent=base["Normal"], alignment=TA_CENTER,
                                     textColor=colors.grey),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], textColor=BLEU, spaceBefore=12),
        "normal": base["Normal"],
        "petit": ParagraphStyle("petit", parent=base["Normal"], fontSize=8, textColor=colors.grey),
        "cellule": ParagraphStyle("cellule", parent=base["Normal"], fontSize=9, leading=11),
    }


def _tableau(lignes, largeurs, styles, entete=True):
    donnees = [[Paragraph(texte_pdf(c), styles["cellule"]) for c in ligne] for ligne in lignes]
    table = Table(donnees, colWidths=largeurs, repeatRows=1 if entete else 0)
    commandes = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if entete:
        commandes.append(("BACKGROUND", (0, 0), (-1, 0), GRIS))
    table.setStyle(TableStyle(commandes))
    return table


def generer_pdf(rapport, chloration=None, libelle_type=None):
    """Construit le PDF à partir de DiagnosticEau.generer_rapport_complet().

    chloration : résultat facultatif de dimensionner_chloration().
    Retourne le contenu du fichier en octets.
    """
    styles = _styles()
    tampon = io.BytesIO()
    doc = SimpleDocTemplate(tampon, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title="AquaDiag - Rapport de diagnostic", author="AquaDiag")
    largeur = A4[0] - 4 * cm
    h = []

    def titre(texte):
        h.append(Paragraph(texte_pdf(texte), styles["h2"]))

    def paragraphe(texte, style="normal"):
        h.append(Paragraph(texte_pdf(texte), styles[style]))

    h.append(Paragraph("AquaDiag - Rapport de diagnostic", styles["titre"]))
    h.append(Paragraph(texte_pdf(f"Établi le {rapport['date_diagnostic']}"), styles["sous_titre"]))
    h.append(Spacer(1, 10))
    h.append(_tableau([
        ["Type d'eau", libelle_type or rapport["type_eau"]],
        ["Référentiel", rapport["norme_reference"]],
    ], [4 * cm, largeur - 4 * cm], styles, entete=False))

    # Paramètres
    titre("1. Paramètres mesurés")
    lignes = [["Paramètre", "Valeur", "Unité"]]
    lignes += [[libelle(p), f"{v:g}" if isinstance(v, (int, float)) else str(v), unite(p)]
               for p, v in rapport["parametres_saisis"].items()]
    h.append(_tableau(lignes, [largeur * 0.5, largeur * 0.25, largeur * 0.25], styles))

    # Conformité
    titre("2. Conformité")
    if rapport["non_conformites"]:
        lignes = [["Paramètre", "Mesuré", "Norme", "Nature"]]
        lignes += [[nc["libelle"], f"{nc['valeur']:g} {nc['unite']}", f"{nc['norme']} {nc['unite']}",
                    NATURES[nc["nature"]]] for nc in rapport["non_conformites"]]
        table = _tableau(lignes, [largeur * 0.22, largeur * 0.2, largeur * 0.2, largeur * 0.38], styles)
        table.setStyle(TableStyle([("TEXTCOLOR", (0, 1), (0, -1), ROUGE)]))
        h.append(table)
    else:
        paragraphe("Tous les paramètres saisis sont conformes au référentiel.")

    # Bactériologie
    bacterio = rapport.get("bacteriologie")
    if bacterio:
        titre("3. Bactériologie")
        if "risque" in bacterio:
            paragraphe(f"Classe de risque (E. coli, OMS) : {bacterio['risque']}")
        paragraphe("Contamination fécale détectée." if bacterio["contamination_fecale"]
                   else "Aucun indicateur de contamination fécale.")

    # Équilibre
    equilibre = rapport.get("equilibre_calcocarbonique")
    if equilibre:
        titre("4. Équilibre calcocarbonique")
        indice = equilibre["indice"]
        etat = ("eau agressive (risque de corrosion)" if indice < -0.5
                else "eau incrustante (risque d'entartrage)" if indice > 0.5
                else "eau proche de l'équilibre")
        paragraphe(f"Indice de Langelier Is = {indice:+.2f} ; pH de saturation = {equilibre['phs']:.2f} : {etat}.")
        for hypothese in equilibre["hypotheses"]:
            paragraphe(f"Hypothèse : {hypothese}", "petit")

    # Traitements
    titre("5. Traitements prescrits")
    if rapport["traitements_proposes"]:
        lignes = [["Étape", "Détail"]]
        for t in rapport["traitements_proposes"]:
            detail = " - ".join(x for x in (t.get("methode"), t.get("detail")) if x)
            doses = [f"{nom} : {t[cle]} mg/L" for cle, nom in (
                ("dose_chaux_mgL", "chaux Ca(OH)2"), ("dose_soude_mgL", "carbonate de sodium"),
                ("dose_chlore_mgL", "chlore"), ("dose_kmno4_mgL", "KMnO4"),
                ("dose_coagulant_mgL", "coagulant"), ("dose_aluminium_mgL", "aluminium")) if cle in t]
            if doses:
                detail += ". Doses : " + ", ".join(doses)
            lignes.append([libelle_etape(t["etape"]), detail])
        h.append(_tableau(lignes, [largeur * 0.28, largeur * 0.72], styles))
    else:
        paragraphe("Aucun traitement spécifique nécessaire.")

    # Filière
    titre("6. Filière de traitement")
    for i, etape in enumerate(rapport["filiere_traitement"], 1):
        paragraphe(f"{i}. {etape}")

    # Chloration
    if chloration:
        titre("7. Dimensionnement de la chloration")
        h.append(_tableau([
            ["Grandeur", "Valeur"],
            ["Débit traité", f"{chloration['debit_m3j']:g} m³/j"],
            ["Dose de chlore", f"{chloration['dose_mgL']} mg/L"],
            ["Chlore actif consommé", f"{chloration['chlore_actif_kg_j']} kg/j"],
            [f"Hypochlorite de calcium ({chloration['purete_hth']:.0%})", f"{chloration['hth_kg_j']} kg/j"],
            [f"Eau de Javel ({chloration['degre_javel']:g} °chl)", f"{chloration['javel_L_j']} L/j"],
            ["Fraction HOCl au pH de l'eau", f"{chloration['fraction_hocl']:.0%}"],
            ["CT requis / T10", f"{chloration['ct_requis']:g} mg.min/L / {chloration['t10_min']} min"],
            ["Temps de séjour", f"{chloration['temps_sejour_min']} min"],
            ["Volume du bassin de contact", f"{chloration['volume_contact_m3']} m³"],
        ], [largeur * 0.55, largeur * 0.45], styles))
        for avertissement in chloration["avertissements"]:
            paragraphe(f"Attention : {avertissement}")

    # Suivi
    suivi = rapport["recommandations_suivi"]
    titre("8. Suivi et maintenance")
    paragraphe(f"Fréquence de contrôle : {suivi['frequence_controle']}")
    paragraphe(f"Paramètres clés : {', '.join(suivi['parametres_cles'])}")
    for action in suivi["maintenance_preventive"]:
        paragraphe(f"- {action}")

    h.append(Spacer(1, 16))
    paragraphe("Rapport généré par AquaDiag, application à usage pédagogique. Les doses sont indicatives "
               "et doivent être confirmées par des essais (jar-test, demande en chlore). "
               "Consulter un expert pour une décision réelle.", "petit")

    doc.build(h)
    return tampon.getvalue()
