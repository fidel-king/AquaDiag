"""
AquaDiag - Application de Diagnostic et Traitement des Eaux
Version 1.2
Basée sur les cours de Master Ecohydrologie (INE/UAC)

Interface Streamlit. Toute la logique de calcul est dans diagnostic.py,
le rapport PDF dans rapport_pdf.py.
"""

import copy
import json
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from diagnostic import (
    FACTEURS_CHICANAGE,
    NATURES,
    NORMES_EAU_POTABLE,
    NORMES_REJET_EAU_USEE,
    PARAMETRES,
    PARAMETRES_BACTERIO,
    DiagnosticEau,
    classer_biodegradabilite,
    dimensionner_chloration,
    libelle,
    libelle_etape,
    unite,
    valider_norme,
)
from rapport_pdf import generer_pdf

st.set_page_config(
    page_title="AquaDiag - Diagnostic Traitement Eau",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# CHAMPS DE SAISIE PAR TYPE D'EAU
# (paramètre, valeur par défaut, pas) regroupés par colonne
# ============================================================================

CHAMPS = {
    "eau_surface": [
        ("🌡️ Paramètres physiques", [("pH", 7.2, 0.1), ("temperature", 25.0, 1.0),
                                     ("turbidite", 15.0, 1.0), ("couleur", 20.0, 1.0),
                                     ("conductivite", 300.0, 10.0)]),
        ("🧪 Paramètres organiques", [("mes", 50.0, 1.0), ("dco", 40.0, 1.0),
                                      ("dbo5", 10.0, 1.0), ("nitrates", 25.0, 1.0)]),
        ("⚙️ Paramètres minéraux", [("alcalinite", 120.0, 5.0), ("durete_totale", 150.0, 5.0),
                                   ("durete_calcique", 80.0, 5.0), ("fer", 0.5, 0.05),
                                   ("manganese", 0.05, 0.01)]),
    ],
    "eau_souterraine": [
        ("🌡️ Paramètres physiques", [("pH", 7.0, 0.1), ("temperature", 22.0, 1.0),
                                     ("conductivite", 800.0, 10.0)]),
        ("🧪 Paramètres chimiques", [("durete_totale", 250.0, 5.0), ("durete_calcique", 180.0, 5.0),
                                     ("alcalinite", 180.0, 5.0), ("nitrates", 35.0, 1.0)]),
        ("⚙️ Métaux et fluorures", [("fer", 0.8, 0.05), ("manganese", 0.15, 0.01),
                                    ("fluorures", 0.8, 0.1)]),
    ],
    "eau_atmospherique": [
        ("🌡️ Paramètres physiques", [("pH", 6.0, 0.1), ("conductivite", 50.0, 5.0)]),
        ("🧪 Paramètres chimiques", [("nitrates", 5.0, 1.0), ("sulfates", 8.0, 1.0)]),
    ],
    "eau_usee": [
        ("🌡️ Paramètres physiques", [("pH", 7.5, 0.1), ("temperature", 25.0, 1.0),
                                     ("mes", 250.0, 5.0)]),
        ("🧪 Paramètres organiques", [("dco", 500.0, 10.0), ("dbo5", 250.0, 5.0)]),
        ("⚙️ Nutriments", [("ntk", 50.0, 1.0), ("phosphore_total", 12.0, 0.5)]),
    ],
}

LIBELLES_TYPES = {
    "eau_surface": "🌊 Eau de surface (rivière, lac, barrage)",
    "eau_souterraine": "⛲ Eau souterraine (puits, forage)",
    "eau_atmospherique": "☁️ Eau atmosphérique (pluie, condensation)",
    "eau_usee": "🏭 Eau usée (domestique, industrielle)",
}

PERSONNALISEE = "PERSONNALISEE"
CLE_PAR_LIBELLE = {info["libelle"]: cle for cle, info in PARAMETRES.items()}
LIBELLE_PAR_NATURE = {cle: texte.split(" (")[0] for cle, texte in NATURES.items()}
NATURE_PAR_LIBELLE = {texte: cle for cle, texte in LIBELLE_PAR_NATURE.items()}


def etiquette(param):
    u = unite(param)
    return f"{libelle(param)} ({u})" if u else libelle(param)


def famille(type_eau):
    return "rejet" if type_eau == "eau_usee" else "potable"


def norme_depart(type_eau):
    """Norme servant de modèle à la norme personnalisée."""
    return copy.deepcopy(NORMES_REJET_EAU_USEE if type_eau == "eau_usee" else NORMES_EAU_POTABLE["OMS_2011"])


def norme_vers_tableau(norme):
    tableau = pd.DataFrame([
        {
            "Paramètre": libelle(p),
            "Limite max": r.get("limite"),
            "Min": r.get("min"),
            "Max": r.get("max"),
            "Nature": LIBELLE_PAR_NATURE[r.get("nature", "reglementaire")],
        }
        for p, r in norme["parametres"].items()
    ])
    # Colonnes numériques : une case vide reste vide (NaN) au lieu d'afficher « None »
    colonnes = ["Limite max", "Min", "Max"]
    tableau[colonnes] = tableau[colonnes].astype(float)
    return tableau


def tableau_vers_norme(nom, tableau):
    parametres = {}
    for _, ligne in tableau.iterrows():
        if pd.isna(ligne["Paramètre"]) or not ligne["Paramètre"]:
            continue
        cle = CLE_PAR_LIBELLE[ligne["Paramètre"]]
        parametres[cle] = {
            "limite": None if pd.isna(ligne["Limite max"]) else ligne["Limite max"],
            "min": None if pd.isna(ligne["Min"]) else ligne["Min"],
            "max": None if pd.isna(ligne["Max"]) else ligne["Max"],
            "nature": NATURE_PAR_LIBELLE.get(ligne["Nature"], "reglementaire"),
        }
    return valider_norme({"nom": nom, "parametres": parametres})


# ============================================================================
# STYLE ET EN-TÊTE
# ============================================================================

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #0066cc, #0099ff);
        padding: 1.5rem; border-radius: 15px; color: white;
        text-align: center; margin-bottom: 2rem;
    }
    .main-header h1 { margin: 0; font-size: 2.5rem; }
    .main-header p { margin: 0.5rem 0 0 0; opacity: 0.9; }
    .diagnostic-card {
        background-color: rgba(128,128,128,0.10); padding: 1rem;
        border-radius: 10px; margin: 0.6rem 0;
    }
    .success { color: #28a745; font-weight: bold; }
    .danger { color: #dc3545; font-weight: bold; }
    .treatment-card {
        background-color: rgba(76,175,80,0.12); padding: 1rem; border-radius: 10px;
        border-left: 5px solid #4caf50; margin: 0.5rem 0;
    }
    .footer {
        text-align: center; color: #6c757d; font-size: 0.8rem;
        margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>💧 AquaDiag</h1>
    <p>Assistant de diagnostic et traitement des eaux</p>
    <p style="font-size: 0.9rem;">Master Ecohydrologie - INE/UAC</p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# BARRE LATÉRALE
# ============================================================================

with st.sidebar:
    st.markdown("## 📋 Configuration")
    type_eau = st.selectbox("Type d'eau à traiter", options=list(CHAMPS),
                            format_func=LIBELLES_TYPES.get)
    if type_eau == "eau_usee":
        options_normes = {"REJET": "📌 Normes de rejet par défaut"}
    else:
        options_normes = {cle: ("🌍 " if cle == "OMS_2011" else "🇧🇯 ") + n["nom"]
                          for cle, n in NORMES_EAU_POTABLE.items()}
    options_normes[PERSONNALISEE] = "✏️ Norme personnalisée"
    choix_norme = st.selectbox("Norme de référence", options=list(options_normes),
                               format_func=options_normes.get, key=f"norme_{famille(type_eau)}")
    st.markdown("---")
    st.caption("📚 Sources : Directives OMS 2011, Décret béninois 2001-094")
    st.caption("🎓 Cours de Master Ecohydrologie - INE/UAC")

# ============================================================================
# NORME PERSONNALISÉE
# ============================================================================

norme = choix_norme if choix_norme in NORMES_EAU_POTABLE else "OMS_2011"
if choix_norme == PERSONNALISEE:
    fam = famille(type_eau)
    # Base stable de l'éditeur : remplacée seulement lors d'un import
    if f"base_{fam}" not in st.session_state:
        base = norme_depart(type_eau)
        base["nom"] = "Norme personnalisée"
        st.session_state[f"base_{fam}"] = base
    with st.expander("✏️ Norme personnalisée", expanded=True):
        st.caption("Partez du modèle proposé, modifiez les valeurs, ajoutez ou supprimez des lignes. "
                   "Indiquez soit une limite maximale, soit un minimum et un maximum. "
                   "Exportez la norme en JSON pour la réutiliser (par exemple la norme guinéenne).")
        fichier = st.file_uploader("Importer une norme (JSON)", type="json", key=f"import_{fam}")
        if fichier is not None and st.session_state.get(f"fichier_importe_{fam}") != fichier.file_id:
            try:
                importee = valider_norme(json.load(fichier))
                st.session_state[f"base_{fam}"] = importee
                st.session_state[f"fichier_importe_{fam}"] = fichier.file_id
                st.session_state[f"version_{fam}"] = st.session_state.get(f"version_{fam}", 0) + 1
                st.success(f"Norme « {importee['nom']} » importée.")
            except (ValueError, json.JSONDecodeError) as err:
                st.error(f"Fichier non valide : {err}")
        base = st.session_state[f"base_{fam}"]
        version = st.session_state.get(f"version_{fam}", 0)
        nom_norme = st.text_input("Nom de la norme", value=base["nom"], key=f"nom_{fam}_{version}")
        tableau = st.data_editor(
            norme_vers_tableau(base),
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            key=f"editeur_{fam}_{version}",
            column_config={
                "Paramètre": st.column_config.SelectboxColumn(
                    options=sorted(CLE_PAR_LIBELLE), required=True),
                "Limite max": st.column_config.NumberColumn(min_value=0.0, format="%g"),
                "Min": st.column_config.NumberColumn(format="%g"),
                "Max": st.column_config.NumberColumn(format="%g"),
                "Nature": st.column_config.SelectboxColumn(
                    options=list(NATURE_PAR_LIBELLE), required=True),
            },
        )
        try:
            norme = tableau_vers_norme(nom_norme, tableau)
            st.download_button("💾 Exporter la norme (JSON)",
                               data=json.dumps(norme, indent=2, ensure_ascii=False),
                               file_name=f"norme_{nom_norme.strip().replace(' ', '_') or 'perso'}.json",
                               mime="application/json")
        except ValueError as err:
            st.error(f"Norme incomplète : {err}")
            norme = None

# ============================================================================
# SAISIE
# ============================================================================

st.markdown("## 📊 Saisie des paramètres de l'eau brute")

with st.expander("ℹ️ À propos des paramètres"):
    st.markdown("""
    | Paramètre | Description |
    |-----------|-------------|
    | **pH** | Potentiel hydrogène (acidité/alcalinité) |
    | **Turbidité** | Clarté de l'eau (NTU) |
    | **MES** | Matières en suspension |
    | **DCO / DBO5** | Demandes chimique et biochimique en oxygène |
    | **TAC** | Alcalinité (titre alcalimétrique complet) en mg/L CaCO₃ |
    | **TH / dureté calcique** | Dureté totale et part due au calcium, en mg/L CaCO₃ |
    | **Conductivité** | Sert à estimer la minéralisation (TDS ≈ 0,65 × conductivité) |
    | **E. coli, coliformes** | Indicateurs de contamination fécale (UFC par volume filtré) |
    """)

valeurs_saisies = {}
groupes = CHAMPS[type_eau]
for colonne, (titre, champs) in zip(st.columns(len(groupes)), groupes):
    with colonne:
        st.subheader(titre)
        for param, defaut, pas in champs:
            valeurs_saisies[param] = st.number_input(
                etiquette(param),
                min_value=0.0,
                max_value=14.0 if param == "pH" else None,
                value=float(defaut),
                step=pas,
                key=f"{type_eau}_{param}",
            )

# Bactériologie : saisie facultative (une valeur absente n'est pas une valeur nulle)
if norme is not None:
    referentiel = DiagnosticEau(type_eau, {}, norme).referentiel()["parametres"]
    params_bacterio = [p for p in PARAMETRES_BACTERIO if p in referentiel]
    if type_eau != "eau_usee" and "e_coli" not in params_bacterio:
        params_bacterio.insert(0, "e_coli")
    if type_eau == "eau_usee" and "coliformes_fecaux" not in params_bacterio:
        params_bacterio.append("coliformes_fecaux")
    st.subheader("🦠 Analyse bactériologique")
    if st.checkbox("Résultats bactériologiques disponibles", key=f"bacterio_{type_eau}"):
        for colonne, param in zip(st.columns(len(params_bacterio)), params_bacterio):
            with colonne:
                valeurs_saisies[param] = st.number_input(
                    etiquette(param), min_value=0.0, value=0.0, step=1.0, format="%.0f",
                    key=f"{type_eau}_{param}",
                )

st.markdown("---")
_, col_bouton, _ = st.columns([1, 2, 1])
with col_bouton:
    if st.button("🔍 DIAGNOSTIQUER ET PRESCRIRE LE TRAITEMENT", type="primary", width="stretch",
                 disabled=norme is None):
        # Le résultat est conservé : il ne disparaît plus lors d'un clic sur « Télécharger »
        st.session_state["dernier_diagnostic"] = {
            "type_eau": type_eau,
            "norme": copy.deepcopy(norme),
            "valeurs": dict(valeurs_saisies),
        }

# ============================================================================
# RÉSULTATS
# ============================================================================


def section_chloration(valeurs):
    """Saisie et calcul de la chloration ; retourne le résultat ou None."""
    st.subheader("🧴 Dimensionnement de la chloration")
    st.caption("pH et température repris de l'échantillon. La demande en chlore doit être "
               "mesurée par un essai (doses croissantes, chlore libre lu après 30 min).")
    c1, c2, c3 = st.columns(3)
    with c1:
        debit = st.number_input("Débit à traiter (m³/j)", min_value=1.0, value=500.0, step=50.0,
                                key="chl_debit")
        demande = st.number_input("Demande en chlore (mg/L)", min_value=0.0, value=1.0, step=0.1,
                                  key="chl_demande")
    with c2:
        residuel = st.number_input("Chlore libre résiduel visé (mg/L)", min_value=0.1, value=0.5,
                                   step=0.1, key="chl_residuel")
        chicanage = st.selectbox("Bassin de contact", options=list(FACTEURS_CHICANAGE), index=1,
                                 format_func=lambda f: f"{FACTEURS_CHICANAGE[f]} (T10/T = {f})",
                                 key="chl_chicanage")
    with c3:
        purete = st.number_input("Hypochlorite de calcium : chlore actif (%)", min_value=10.0,
                                 max_value=100.0, value=65.0, step=5.0, key="chl_hth")
        degre = st.number_input("Eau de Javel (degrés chlorométriques)", min_value=1.0, value=12.0,
                                step=1.0, key="chl_javel")
    try:
        chl = dimensionner_chloration(
            debit, demande, residuel, ph=valeurs.get("pH", 7.0),
            temperature=valeurs.get("temperature", 25.0), facteur_chicanage=chicanage,
            purete_hth=purete / 100, degre_javel=degre,
        )
    except ValueError as err:
        st.error(str(err))
        return None
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Dose de chlore", f"{chl['dose_mgL']} mg/L")
    m2.metric("Hypochlorite de calcium", f"{chl['hth_kg_j']} kg/j")
    m3.metric("Eau de Javel", f"{chl['javel_L_j']} L/j")
    m4.metric("Bassin de contact", f"{chl['volume_contact_m3']} m³")
    st.markdown(
        f"- Chlore actif consommé : **{chl['chlore_actif_kg_j']} kg/j**\n"
        f"- Part du chlore libre sous forme HOCl (désinfectant actif) : **{chl['fraction_hocl']:.0%}**\n"
        f"- CT requis {chl['ct_requis']:g} mg·min/L → T10 = **{chl['t10_min']} min**, "
        f"temps de séjour = **{chl['temps_sejour_min']} min**"
    )
    for avertissement in chl["avertissements"]:
        st.warning(avertissement)
    return chl


def afficher_resultats(type_eau, norme, valeurs):
    diagnostic = DiagnosticEau(type_eau, valeurs, norme)

    st.markdown("---")
    st.markdown("## 📋 RÉSULTATS DU DIAGNOSTIC")

    # 1. Synthèse
    with st.expander("📊 Synthèse des paramètres saisis", expanded=True):
        df_params = pd.DataFrame({
            "Paramètre": [libelle(p) for p in valeurs],
            "Valeur mesurée": list(valeurs.values()),
            "Unité": [unite(p) for p in valeurs],
        })
        st.dataframe(df_params, hide_index=True, width="stretch")

    # 2. Conformité
    non_conformites = diagnostic.analyser_conformite()
    st.subheader("✅ Analyse de conformité")
    st.caption(f"Référentiel : {diagnostic.referentiel()['nom']}")
    if non_conformites:
        st.markdown("##### ⚠️ Paramètres non conformes détectés")
        for nc in non_conformites:
            st.markdown(f"""
            <div class="diagnostic-card">
            <span class="danger">❌ <b>{nc['libelle'].upper()}</b></span><br>
            Valeur mesurée : <b>{nc['valeur']:g} {nc['unite']}</b><br>
            Norme : <b>{nc['norme']} {nc['unite']}</b> — <i>{NATURES[nc['nature']]}</i><br>
            Écart : <b>{nc['ecart']:+g} {nc['unite']}</b>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="diagnostic-card">
        <span class="success">✅ Tous les paramètres saisis sont conformes</span>
        </div>
        """, unsafe_allow_html=True)

    # 3. Bactériologie
    bacterio = diagnostic.analyse_bacteriologique()
    if bacterio and type_eau != "eau_usee":
        st.subheader("🦠 Qualité bactériologique")
        if "risque" in bacterio:
            affichage = {"conforme": st.success, "faible": st.info, "intermediaire": st.warning,
                         "eleve": st.error, "tres_eleve": st.error}[bacterio["classe_risque"]]
            affichage(f"Classe de risque OMS (E. coli = {bacterio['parametres']['e_coli']:g} UFC/100 mL) : "
                      f"**{bacterio['risque']}**")
        elif bacterio["contamination_fecale"]:
            st.error("Contamination fécale détectée")

    # 4. Équilibre calcocarbonique
    details = diagnostic.details_langelier() if type_eau in ("eau_surface", "eau_souterraine") else None
    if details:
        indice = details["indice"]
        st.subheader("⚖️ Équilibre calcocarbonique")
        c1, c2, c3 = st.columns(3)
        c1.metric("Indice de Langelier (Is)", f"{indice:+.2f}")
        c2.metric("pH de saturation (pHs)", f"{details['phs']:.2f}")
        with c3:
            if indice < -0.5:
                st.warning("⚠️ Eau agressive - Risque de corrosion des canalisations")
            elif indice > 0.5:
                st.warning("⚠️ Eau incrustante - Risque d'entartrage")
            else:
                st.success("✅ Eau proche de l'équilibre")
        for hypothese in details["hypotheses"]:
            st.caption(f"Hypothèse : {hypothese}")

    # 5. Traitements
    traitements = diagnostic.determiner_traitements()
    st.subheader("🔧 Traitements prescrits")
    if traitements:
        for traitement in traitements:
            st.markdown(f"""
            <div class="treatment-card">
            <strong>📌 {libelle_etape(traitement.get('etape', '')).upper()}</strong><br>
            {traitement.get('methode', '')}{' — ' if traitement.get('methode') else ''}{traitement.get('detail', '')}
            </div>
            """, unsafe_allow_html=True)
            if "co2_libre_mgL" in traitement:
                st.info(f"🫧 **CO₂ libre** : {traitement['co2_libre_mgL']} mg/L — "
                        f"CO₂ à neutraliser : {traitement['co2_neutralise_mgL']} mg/L")
            if "dose_chaux_mgL" in traitement:
                st.success(f"🧪 **Dose de chaux Ca(OH)₂** : {traitement['dose_chaux_mgL']} mg/L")
            if "dose_soude_mgL" in traitement:
                st.success(f"🧪 **Dose de carbonate de sodium** : {traitement['dose_soude_mgL']} mg/L")
            if "dose_chlore_mgL" in traitement:
                st.info(f"💊 **Dose de chlore** : {traitement['dose_chlore_mgL']} mg/L")
            if "dose_kmno4_mgL" in traitement:
                st.info(f"💊 **Dose de KMnO₄** : {traitement['dose_kmno4_mgL']} mg/L")
            if "dose_aluminium_mgL" in traitement:
                st.info(f"💊 **Aluminium (stœchiométrique)** : {traitement['dose_aluminium_mgL']} mg Al/L")
    else:
        st.success("✅ Aucun traitement spécifique nécessaire")

    # 6. Filière
    st.subheader("🏭 Filière de traitement recommandée")
    filiere = diagnostic.construire_filiere()
    st.markdown("\n".join(f"{i}. {etape}" for i, etape in enumerate(filiere, 1)))

    # 7. Biodégradabilité
    if type_eau == "eau_usee" and valeurs.get("dbo5", 0) > 0:
        rapport = valeurs["dco"] / valeurs["dbo5"]
        code, texte, filiere_bio = classer_biodegradabilite(rapport)
        st.subheader("📈 Biodégradabilité")
        c1, c2 = st.columns(2)
        c1.metric("Rapport DCO/DBO5", f"{rapport:.2f}")
        with c2:
            message = f"{texte} — {filiere_bio}"
            {"facile": st.success, "moyenne": st.info, "faible": st.warning}[code](message)

    # 8. Chloration (eaux destinées à la consommation)
    chloration = section_chloration(valeurs) if type_eau != "eau_usee" else None

    # 9. Graphique : chaque paramètre en % de sa limite (unités différentes)
    ref = diagnostic.referentiel()["parametres"]
    lignes = [
        (libelle(p), valeurs[p] / ref[p]["limite"] * 100)
        for p in valeurs
        if p in ref and ref[p].get("limite", 0) > 0
    ]
    if lignes:
        st.subheader("📊 Visualisation comparative")
        noms, pourcentages = zip(*lignes)
        couleurs = ["#dc3545" if v > 100 else "#0066cc" for v in pourcentages]
        fig = go.Figure(go.Bar(x=list(noms), y=list(pourcentages), marker_color=couleurs,
                               text=[f"{v:.0f} %" for v in pourcentages], textposition="outside"))
        fig.add_hline(y=100, line_dash="dash", line_color="#ff6600", annotation_text="Limite")
        fig.update_layout(yaxis_title="% de la valeur limite", showlegend=False)
        st.plotly_chart(fig, width="stretch")

    # 10. Suivi
    with st.expander("📋 Recommandations de suivi et maintenance"):
        suivis = diagnostic.recommandations_suivi()
        st.markdown(f"**📅 Fréquence de contrôle recommandée** : {suivis['frequence_controle']}")
        st.markdown(f"**🎯 Paramètres clés à surveiller** : {', '.join(suivis['parametres_cles'])}")
        if suivis["maintenance_preventive"]:
            st.markdown("**🔧 Maintenance préventive** :")
            for maint in suivis["maintenance_preventive"]:
                st.markdown(f"- {maint}")

    # 11. Export
    st.subheader("📄 Export du rapport")
    rapport_complet = diagnostic.generer_rapport_complet()
    if chloration:
        rapport_complet["chloration"] = chloration
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            label="📥 Rapport PDF",
            data=generer_pdf(rapport_complet, chloration, LIBELLES_TYPES[type_eau].split(" ", 1)[1]),
            file_name=f"rapport_{type_eau}_{horodatage}.pdf",
            mime="application/pdf",
            type="primary",
        )
    with c2:
        st.download_button(
            label="📥 Rapport texte (TXT)",
            data=rapport_texte(rapport_complet),
            file_name=f"rapport_{type_eau}_{horodatage}.txt",
            mime="text/plain",
        )
    with c3:
        st.download_button(
            label="📥 Données (JSON)",
            data=json.dumps(rapport_complet, indent=2, default=str, ensure_ascii=False),
            file_name=f"diagnostic_{type_eau}_{horodatage}.json",
            mime="application/json",
        )


def rapport_texte(rapport):
    lignes = [
        "AQUADIAG - RAPPORT DE DIAGNOSTIC",
        "=" * 40,
        f"Date : {rapport['date_diagnostic']}",
        f"Type d'eau : {LIBELLES_TYPES[rapport['type_eau']]}",
        f"Référentiel : {rapport['norme_reference']}",
        "",
        "PARAMÈTRES MESURÉS",
    ]
    lignes += [f"  - {libelle(p)} : {v:g} {unite(p)}" for p, v in rapport["parametres_saisis"].items()]
    lignes += ["", "NON-CONFORMITÉS"]
    lignes += [f"  - {nc['libelle']} : {nc['valeur']:g} {nc['unite']} (norme {nc['norme']})"
               for nc in rapport["non_conformites"]] or ["  Aucune"]
    if rapport.get("bacteriologie") and "risque" in rapport["bacteriologie"]:
        lignes += ["", f"BACTÉRIOLOGIE : {rapport['bacteriologie']['risque']}"]
    if rapport["equilibre_calcocarbonique"]:
        eq = rapport["equilibre_calcocarbonique"]
        lignes += ["", f"ÉQUILIBRE CALCOCARBONIQUE : Is = {eq['indice']:+.2f} ; pHs = {eq['phs']:.2f}"]
    lignes += ["", "TRAITEMENTS PROPOSÉS"]
    lignes += [f"  - {libelle_etape(t['etape'])} : {t.get('detail', '')}"
               for t in rapport["traitements_proposes"]] or ["  Aucun"]
    lignes += ["", "FILIÈRE DE TRAITEMENT"]
    lignes += [f"  {i}. {e}" for i, e in enumerate(rapport["filiere_traitement"], 1)]
    chl = rapport.get("chloration")
    if chl:
        lignes += ["", "CHLORATION",
                   f"  Dose : {chl['dose_mgL']} mg/L ; chlore actif : {chl['chlore_actif_kg_j']} kg/j",
                   f"  Hypochlorite de calcium : {chl['hth_kg_j']} kg/j ; eau de Javel : {chl['javel_L_j']} L/j",
                   f"  Bassin de contact : {chl['volume_contact_m3']} m3 (séjour {chl['temps_sejour_min']} min)"]
    lignes += ["", "Application à usage pédagogique - Consulter un expert pour une décision réelle"]
    return "\n".join(lignes)


diag = st.session_state.get("dernier_diagnostic")
if diag and diag["type_eau"] == type_eau:
    if diag["valeurs"] != valeurs_saisies or diag["norme"] != norme:
        st.warning("⚠️ Les paramètres ont changé depuis le dernier diagnostic. "
                   "Cliquez à nouveau sur « Diagnostiquer » pour mettre à jour les résultats.")
    afficher_resultats(diag["type_eau"], diag["norme"], diag["valeurs"])

st.markdown("""
<div class="footer">
    <p>AquaDiag v1.2 | Développé dans le cadre du Master Ecohydrologie - INE/UAC</p>
    <p>Sources : OMS (2011), Décret béninois 2001-094, Cours de traitement des eaux</p>
    <p>⚠️ Application à usage pédagogique - Consulter un expert pour une décision réelle</p>
</div>
""", unsafe_allow_html=True)
