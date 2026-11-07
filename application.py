"""
AquaDiag - Application de Diagnostic et Traitement des Eaux
Version 1.1
Basée sur les cours de Master Ecohydrologie (INE/UAC)

Interface Streamlit. Toute la logique de calcul est dans diagnostic.py.
"""

import json
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from diagnostic import (
    NATURES,
    NORMES_EAU_POTABLE,
    DiagnosticEau,
    classer_biodegradabilite,
    libelle,
    unite,
)

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


def etiquette(param):
    u = unite(param)
    return f"{libelle(param)} ({u})" if u else libelle(param)


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
    .info { color: #17a2b8; font-weight: bold; }
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
    if type_eau != "eau_usee":
        norme = st.selectbox(
            "Norme de référence",
            options=list(NORMES_EAU_POTABLE),
            format_func=lambda x: ("🌍 " if x == "OMS_2011" else "🇧🇯 ") + NORMES_EAU_POTABLE[x]["nom"],
        )
    else:
        norme = "OMS_2011"  # sans effet : les normes de rejet s'appliquent
        st.info("📌 Normes de rejet applicables aux eaux usées")
    st.markdown("---")
    st.caption("📚 Sources : Directives OMS 2011, Décret béninois 2001-094")
    st.caption("🎓 Cours de Master Ecohydrologie - INE/UAC")

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

st.markdown("---")
_, col_bouton, _ = st.columns([1, 2, 1])
with col_bouton:
    if st.button("🔍 DIAGNOSTIQUER ET PRESCRIRE LE TRAITEMENT", type="primary", width="stretch"):
        # Le résultat est conservé : il ne disparaît plus lors d'un clic sur « Télécharger »
        st.session_state["dernier_diagnostic"] = {
            "type_eau": type_eau,
            "norme": norme,
            "valeurs": dict(valeurs_saisies),
        }

# ============================================================================
# RÉSULTATS
# ============================================================================


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
            Valeur mesurée : <b>{nc['valeur']} {nc['unite']}</b><br>
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

    # 3. Équilibre calcocarbonique
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

    # 4. Traitements
    traitements = diagnostic.determiner_traitements()
    st.subheader("🔧 Traitements prescrits")
    if traitements:
        for traitement in traitements:
            st.markdown(f"""
            <div class="treatment-card">
            <strong>📌 {traitement.get('etape', '').replace('_', ' ').upper()}</strong><br>
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

    # 5. Filière
    st.subheader("🏭 Filière de traitement recommandée")
    filiere = diagnostic.construire_filiere()
    st.markdown("\n".join(f"{i}. {etape}" for i, etape in enumerate(filiere, 1)))

    # 6. Biodégradabilité
    if type_eau == "eau_usee" and valeurs.get("dbo5", 0) > 0:
        rapport = valeurs["dco"] / valeurs["dbo5"]
        code, texte, filiere_bio = classer_biodegradabilite(rapport)
        st.subheader("📈 Biodégradabilité")
        c1, c2 = st.columns(2)
        c1.metric("Rapport DCO/DBO5", f"{rapport:.2f}")
        with c2:
            message = f"{texte} — {filiere_bio}"
            {"facile": st.success, "moyenne": st.info, "faible": st.warning}[code](message)

    # 7. Graphique : chaque paramètre en % de sa limite (unités différentes)
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

    # 8. Suivi
    with st.expander("📋 Recommandations de suivi et maintenance"):
        suivis = diagnostic.recommandations_suivi()
        st.markdown(f"**📅 Fréquence de contrôle recommandée** : {suivis['frequence_controle']}")
        st.markdown(f"**🎯 Paramètres clés à surveiller** : {', '.join(suivis['parametres_cles'])}")
        if suivis["maintenance_preventive"]:
            st.markdown("**🔧 Maintenance préventive** :")
            for maint in suivis["maintenance_preventive"]:
                st.markdown(f"- {maint}")

    # 9. Export
    st.subheader("📄 Export du rapport")
    rapport_complet = diagnostic.generer_rapport_complet()
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            label="📥 Télécharger le rapport (JSON)",
            data=json.dumps(rapport_complet, indent=2, default=str, ensure_ascii=False),
            file_name=f"diagnostic_{type_eau}_{horodatage}.json",
            mime="application/json",
        )
    with c2:
        st.download_button(
            label="📥 Télécharger le rapport (TXT)",
            data=rapport_texte(rapport_complet),
            file_name=f"rapport_{type_eau}_{horodatage}.txt",
            mime="text/plain",
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
    lignes += [f"  - {libelle(p)} : {v} {unite(p)}" for p, v in rapport["parametres_saisis"].items()]
    lignes += ["", "NON-CONFORMITÉS"]
    lignes += [f"  - {nc['libelle']} : {nc['valeur']} {nc['unite']} (norme {nc['norme']})"
               for nc in rapport["non_conformites"]] or ["  Aucune"]
    if rapport["equilibre_calcocarbonique"]:
        eq = rapport["equilibre_calcocarbonique"]
        lignes += ["", f"ÉQUILIBRE CALCOCARBONIQUE : Is = {eq['indice']:+.2f} ; pHs = {eq['phs']:.2f}"]
    lignes += ["", "TRAITEMENTS PROPOSÉS"]
    lignes += [f"  - {t['etape'].replace('_', ' ')} : {t.get('detail', '')}"
               for t in rapport["traitements_proposes"]] or ["  Aucun"]
    lignes += ["", "FILIÈRE DE TRAITEMENT"]
    lignes += [f"  {i}. {e}" for i, e in enumerate(rapport["filiere_traitement"], 1)]
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
    <p>AquaDiag v1.1 | Développé dans le cadre du Master Ecohydrologie - INE/UAC</p>
    <p>Sources : OMS (2011), Décret béninois 2001-094, Cours de traitement des eaux</p>
    <p>⚠️ Application à usage pédagogique - Consulter un expert pour une décision réelle</p>
</div>
""", unsafe_allow_html=True)
