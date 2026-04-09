"""
AquaDiag - Application de Diagnostic et Traitement des Eaux
Version 1.0
Basée sur les cours de Master Ecohydrologie (INE/UAC)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import io
import base64

# Configuration de la page
st.set_page_config(
    page_title="AquaDiag - Diagnostic Traitement Eau",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# BASES DE DONNÉES DES NORMES
# ============================================================================

NORMES_EAU_POTABLE = {
    "OMS_2011": {
        "nom": "Organisation Mondiale de la Santé (2011)",
        "microbiologiques": {
            "Escherichia_Coli": {"unite": "UFC/100mL", "limite": 0},
            "Coliformes_fecaux": {"unite": "UFC/100mL", "limite": 0}
        },
        "chimiques": {
            "pH": {"unite": "", "min": 6.5, "max": 8.5, "valeur_guide": 7.0},
            "Fluorures": {"unite": "mg/L", "limite": 1.5, "valeur_guide": 1.0},
            "Nitrates": {"unite": "mg/L", "limite": 50, "valeur_guide": 25},
            "Arsenic": {"unite": "μg/L", "limite": 10, "valeur_guide": 5},
            "Cadmium": {"unite": "μg/L", "limite": 3, "valeur_guide": 1},
            "Mercure": {"unite": "μg/L", "limite": 6, "valeur_guide": 2},
            "Plomb": {"unite": "μg/L", "limite": 10, "valeur_guide": 5},
            "Fer": {"unite": "mg/L", "limite": 0.3, "valeur_guide": 0.1},
            "Manganese": {"unite": "mg/L", "limite": 0.1, "valeur_guide": 0.05},
            "Durete_totale": {"unite": "mg/L", "limite": 200, "valeur_guide": 100},
            "Sulfates": {"unite": "mg/L", "limite": 250, "valeur_guide": 100},
            "Chlorures": {"unite": "mg/L", "limite": 250, "valeur_guide": 100},
            "Turbidite": {"unite": "NTU", "limite": 5, "valeur_guide": 1}
        }
    },
    "BENIN_2001_094": {
        "nom": "République du Bénin - Décret 2001-094",
        "microbiologiques": {
            "Germes_banals": {"unite": "UFC/mL", "limite": 20},
            "Escherichia_Coli": {"unite": "UFC/100mL", "limite": 0},
            "Coliformes_totaux": {"unite": "UFC/100mL", "limite": 0},
            "Streptocoques_fecaux": {"unite": "UFC/100mL", "limite": 0},
            "Clostridium_perfringens": {"unite": "UFC/20mL", "limite": 0}
        },
        "chimiques": {
            "pH": {"unite": "", "min": 6.5, "max": 8.5},
            "Sulfates": {"unite": "mg/L", "limite": 500},
            "Durete_totale": {"unite": "mg/L", "limite": 200},
            "Fer": {"unite": "mg/L", "limite": 0.3},
            "Fluorures": {"unite": "mg/L", "limite": 1.5},
            "Manganese": {"unite": "mg/L", "limite": 0.1},
            "Nitrates": {"unite": "mg/L", "limite": 45},
            "Arsenic": {"unite": "μg/L", "limite": 50},
            "Cadmium": {"unite": "μg/L", "limite": 5},
            "Mercure": {"unite": "μg/L", "limite": 1}
        }
    }
}

NORMES_REJET_EAU_USEE = {
    "DBO5": {"unite": "mg/L", "limite": 30, "seuil_alerte": 25},
    "DCO": {"unite": "mg O2/L", "limite": 90, "seuil_alerte": 75},
    "MES": {"unite": "mg/L", "limite": 30, "seuil_alerte": 25},
    "NTK": {"unite": "mg/L", "limite": 40, "seuil_alerte": 30},
    "Phosphore_total": {"unite": "mg/L", "limite": 10, "seuil_alerte": 8},
    "pH": {"unite": "", "min": 5.5, "max": 8.5},
    "Coliformes_fecaux": {"unite": "UFC/100mL", "limite": 2000}
}

# ============================================================================
# CLASSE PRINCIPALE DE DIAGNOSTIC
# ============================================================================

class DiagnosticEau:
    """Classe principale pour le diagnostic et la prescription des traitements"""
    
    def __init__(self, type_eau, valeurs_parametres, norme="OMS_2011"):
        self.type_eau = type_eau
        self.valeurs = valeurs_parametres
        self.norme = norme
        
    def analyser_conformite(self):
        """Compare les valeurs avec les normes"""
        if self.type_eau == "eau_usee":
            normes = NORMES_REJET_EAU_USEE
            non_conformites = []
            for param, valeur in self.valeurs.items():
                if param in normes:
                    norme_param = normes[param]
                    if "limite" in norme_param:
                        if valeur > norme_param["limite"]:
                            non_conformites.append({
                                "parametre": param,
                                "valeur": valeur,
                                "limite": norme_param["limite"],
                                "ecart": valeur - norme_param["limite"]
                            })
                    elif "min" in norme_param and "max" in norme_param:
                        if valeur < norme_param["min"] or valeur > norme_param["max"]:
                            non_conformites.append({
                                "parametre": param,
                                "valeur": valeur,
                                "norme": f"{norme_param['min']} - {norme_param['max']}"
                            })
            return non_conformites
        else:
            normes = NORMES_EAU_POTABLE.get(self.norme, NORMES_EAU_POTABLE["OMS_2011"])
            non_conformites = []
            for param, valeur in self.valeurs.items():
                if param in normes["chimiques"]:
                    norme_param = normes["chimiques"][param]
                    if "limite" in norme_param:
                        if valeur > norme_param["limite"]:
                            non_conformites.append({
                                "parametre": param,
                                "valeur": valeur,
                                "limite": norme_param["limite"],
                                "ecart": valeur - norme_param["limite"]
                            })
                    elif "min" in norme_param and "max" in norme_param:
                        if valeur < norme_param["min"] or valeur > norme_param["max"]:
                            non_conformites.append({
                                "parametre": param,
                                "valeur": valeur,
                                "norme": f"{norme_param['min']} - {norme_param['max']}"
                            })
            return non_conformites
    
    def calculer_indice_langelier(self):
        """Calcule l'indice de saturation de Langelier"""
        pH = self.valeurs.get("pH", 7.0)
        tac = self.valeurs.get("alcalinite", 100)
        ca = self.valeurs.get("durete_calcique", self.valeurs.get("durete_totale", 80))
        temperature = self.valeurs.get("temperature", 20)
        
        # Constantes à 20°C
        pK2 = 10.33
        pKs = 8.34
        
        if tac > 0 and ca > 0:
            pHs = pK2 - pKs - np.log10(tac/50) - np.log10(ca/50)
            Is = pH - pHs
        else:
            Is = 0
        
        return Is
    
    def determiner_traitements(self):
        """Détermine les traitements nécessaires"""
        traitements = []
        
        # Traitements généraux selon type d'eau
        if self.type_eau == "eau_surface":
            traitements.append({
                "etape": "pretraitement",
                "operations": ["Dégrillage (grilles 10-30 mm)", "Tamisage (mailles 0.5-3 mm)", "Dessablage - Déshuilage"],
                "obligatoire": True
            })
            traitements.append({
                "etape": "clarification",
                "operations": ["Coagulation-Floculation", "Décantation lamellaire", "Filtration sur sable"],
                "obligatoire": True
            })
            
            if self.valeurs.get("turbidite", 0) > 5:
                traitements.append({
                    "etape": "coagulation_renforcee",
                    "detail": "Turbidité élevée - Augmentation de la dose de coagulant",
                    "dose_coagulant": self.calculer_dose_coagulant()
                })
        
        elif self.type_eau == "eau_souterraine":
            # Équilibre calco-carbonique
            is_langelier = self.calculer_indice_langelier()
            if is_langelier < -0.5:
                traitements.append({
                    "etape": "correction_agressivite",
                    "detail": f"Eau agressive (Is = {is_langelier:.2f}) - Risque de corrosion",
                    "dose_chaux": self.corriger_agressivite()
                })
            elif is_langelier > 0.5:
                traitements.append({
                    "etape": "correction_incrustation",
                    "detail": f"Eau incrustante (Is = {is_langelier:.2f}) - Risque d'entartrage",
                    "recommandation": "Injection de CO₂ ou adoucissement partiel"
                })
            
            # Fer
            if self.valeurs.get("fer", 0) > 0.3:
                traitements.append(self.traiter_fer())
            
            # Manganèse
            if self.valeurs.get("manganese", 0) > 0.1:
                traitements.append(self.traiter_manganese())
            
            # Dureté
            if self.valeurs.get("durete_totale", 0) > 200:
                traitements.append(self.traiter_durete())
        
        elif self.type_eau == "eau_usee":
            dco = self.valeurs.get("dco", 0)
            dbo5 = self.valeurs.get("dbo5", 0)
            if dbo5 > 0:
                rapport = dco / dbo5
                if rapport < 1.5:
                    traitements.append({
                        "etape": "traitement_biologique",
                        "type": "Boues activées",
                        "detail": "Eau très biodégradable - Traitement biologique adapté",
                        "charge": "forte" if dco > 500 else "moyenne"
                    })
                elif rapport < 2.5:
                    traitements.append({
                        "etape": "traitement_biologique",
                        "type": "Lits bactériens ou biofiltres",
                        "detail": "Biodégradabilité moyenne"
                    })
                else:
                    traitements.append({
                        "etape": "pretraitement_physico_chimique",
                        "detail": "Faible biodégradabilité - Coagulation-floculation préalable nécessaire"
                    })
            
            if self.valeurs.get("ntk", 0) > 40:
                traitements.append({
                    "etape": "traitement_azote",
                    "detail": "Teneur en azote élevée - Traitement tertiaire nécessaire",
                    "methode": "Nitrification-dénitrification"
                })
            
            if self.valeurs.get("phosphore_total", 0) > 10:
                traitements.append({
                    "etape": "traitement_phosphore",
                    "detail": "Teneur en phosphore élevée - Déphosphatation chimique",
                    "dose_aluminium": self.valeurs.get("phosphore_total", 0) * 0.9
                })
        
        return traitements
    
    def calculer_dose_coagulant(self):
        """Calcule la dose de coagulant selon la turbidité"""
        turbidite = self.valeurs.get("turbidite", 10)
        
        if turbidite < 10:
            dose = 10
        elif turbidite < 50:
            dose = 20
        elif turbidite < 100:
            dose = 35
        else:
            dose = 50 + (turbidite - 100) * 0.5
        
        return {
            "coagulant": "Sulfate d'aluminium Al₂(SO₄)₃",
            "dose_mgL": round(dose, 1),
            "ph_optimal": "6.0 - 7.5"
        }
    
    def corriger_agressivite(self):
        """Calcule la dose de chaux pour corriger l'agressivité"""
        # Estimation du CO₂ agressif
        tac = self.valeurs.get("alcalinite", 100)
        dose_chaux = 7.4 * (tac / 50)  # mg/L Ca(OH)₂
        return round(dose_chaux, 1)
    
    def traiter_fer(self):
        """Calcule le traitement de déferrisation"""
        fe_mgl = self.valeurs.get("fer", 0)
        
        if fe_mgl < 5:
            return {
                "etape": "deferrisation",
                "methode": "Aération + Filtration sur sable",
                "detail": f"Teneur en fer : {fe_mgl} mg/L - Traitement par oxydation à l'air",
                "temps_contact": "10-20 minutes"
            }
        else:
            dose_chlore = fe_mgl * 0.63
            return {
                "etape": "deferrisation",
                "methode": "Oxydation chimique",
                "detail": f"Teneur en fer : {fe_mgl} mg/L",
                "dose_chlore_mgL": round(dose_chlore, 2),
                "ph_optimal": 7.2
            }
    
    def traiter_manganese(self):
        """Calcule le traitement de démanganisation"""
        mn_mgl = self.valeurs.get("manganese", 0)
        dose_kmno4 = mn_mgl * 1.92
        
        return {
            "etape": "demanganisation",
            "methode": "Oxydation au permanganate de potassium",
            "dose_kmno4_mgL": round(dose_kmno4, 2),
            "ph_optimal": 7.2,
            "attention": "Éviter l'excès (teinte rose)"
        }
    
    def traiter_durete(self):
        """Calcule l'adoucissement nécessaire"""
        th = self.valeurs.get("durete_totale", 200)
        tac = self.valeurs.get("alcalinite", 150)
        reduction = th - 150
        
        if reduction > 0:
            if tac >= reduction:
                dose_chaux = 7.4 * (reduction / 10)
                return {
                    "etape": "adoucissement",
                    "methode": "Chaux seule",
                    "dose_chaux_mgL": round(dose_chaux, 1),
                    "reaction": "Ca(HCO₃)₂ + Ca(OH)₂ → 2CaCO₃↓ + 2H₂O"
                }
            else:
                durete_permanente = th - tac
                dose_chaux = 7.4 * (tac / 10)
                dose_soude = 10.6 * (durete_permanente / 10)
                return {
                    "etape": "adoucissement",
                    "methode": "Chaux + Soude",
                    "dose_chaux_mgL": round(dose_chaux, 1),
                    "dose_soude_mgL": round(dose_soude, 1),
                    "reaction": "Na₂CO₃ + CaSO₄ → CaCO₃↓ + Na₂SO₄"
                }
        
        return {"etape": "aucun", "detail": "Dureté conforme aux normes"}
    
    def construire_filiere(self):
        """Construit la filière de traitement complète"""
        filiere = []
        
        if self.type_eau == "eau_surface":
            filiere = [
                "1. 📋 Dégrillage (grilles 10-30 mm)",
                "2. 🔄 Tamisage (mailles 0.5-3 mm)",
                "3. 🏖️ Dessablage - Déshuilage",
                "4. 🧪 Coagulation - Floculation",
                "5. ⏳ Décantation lamellaire",
                "6. 🧹 Filtration sur sable",
                "7. 🧴 Désinfection (Chlore/Ozone/UV)",
                "8. 🎯 Affinage (CAG si nécessaire)"
            ]
            
            if self.valeurs.get("pesticides", 0) > 0.1:
                filiere.insert(7, "6b. ⚡ Adsorption sur charbon actif en grains")
            if self.valeurs.get("nitrates", 0) > 50:
                filiere.insert(6, "5b. 🌿 Dénitrification biologique")
                
        elif self.type_eau == "eau_souterraine":
            filiere = ["1. 💨 Aération (cascade ou injection d'air)"]
            
            if self.valeurs.get("fer", 0) > 0.3 or self.valeurs.get("manganese", 0) > 0.1:
                filiere.append("2. 🦠 Déferrisation/Démanganisation (filtration biologique)")
            
            is_langelier = self.calculer_indice_langelier()
            if is_langelier < -0.5:
                filiere.append("3. ⚗️ Correction de l'agressivité (filtration sur Neutralite ou injection chaux)")
            elif is_langelier > 0.5:
                filiere.append("3. 💧 Stabilisation (injection CO₂)")
            
            if self.valeurs.get("durete_totale", 0) > 200:
                filiere.append("4. 🧂 Adoucissement partiel")
            
            filiere.append("5. 🧴 Désinfection (Chlore ou UV)")
            
        elif self.type_eau == "eau_usee":
            dco = self.valeurs.get("dco", 0)
            dbo5 = self.valeurs.get("dbo5", 0)
            rapport = dco / dbo5 if dbo5 > 0 else 3
            
            filiere = [
                "1. 🗑️ Prétraitements (dégrillage, dessablage, déshuilage)",
                "2. 🪣 Traitement primaire (décantation)"
            ]
            
            if rapport < 2.5:
                filiere.append("3. 🧫 Traitement biologique secondaire")
                if rapport < 1.5:
                    filiere.append("   - Boues activées (aération prolongée)")
                else:
                    filiere.append("   - Lits bactériens ou biofiltres")
            else:
                filiere.append("3. 🧪 Traitement physico-chimique (coagulation-floculation)")
            
            if self.valeurs.get("ntk", 0) > 40 or self.valeurs.get("phosphore_total", 0) > 10:
                filiere.append("4. 🎯 Traitement tertiaire (dénitrification/déphosphatation)")
            
            filiere.append("5. 🧴 Désinfection (si rejet en zone sensible)")
        
        elif self.type_eau == "eau_atmospherique":
            filiere = [
                "1. 🧹 Filtration grossière",
                "2. ⚗️ Correction du pH (si pluie acide)",
                "3. 🧴 Désinfection (UV ou chlore)",
                "4. 💧 Stockage en cuve protégée"
            ]
        
        return filiere
    
    def recommandations_suivi(self):
        """Génère les recommandations de suivi"""
        recommandations = {
            "frequence_controle": "Trimestrielle",
            "parametres_cles": [],
            "maintenance_preventive": []
        }
        
        if self.type_eau == "eau_surface":
            recommandations["parametres_cles"] = ["turbidite", "pH", "chlore_residuel"]
            recommandations["seuils_alerte"] = {"turbidite": 1, "chlore_residuel": 0.2}
            recommandations["maintenance_preventive"] = [
                "Nettoyage des grilles de dégrillage (quotidien)",
                "Contrôle des doses de coagulant (jar-test mensuel)",
                "Lavage des filtres à sable (1-2 fois/semaine)"
            ]
        elif self.type_eau == "eau_souterraine":
            recommandations["parametres_cles"] = ["pH", "durete", "fer", "manganese"]
            recommandations["maintenance_preventive"] = [
                "Nettoyage des aérateurs tous les 6 mois",
                "Contrôle des filtres à sable",
                "Vérification de l'absence de colmatage"
            ]
        elif self.type_eau == "eau_usee":
            recommandations["parametres_cles"] = ["DBO5", "DCO", "MES", "NTK"]
            recommandations["maintenance_preventive"] = [
                "Extraction des boues quotidienne",
                "Contrôle de l'oxygène dissous (> 2 mg/L)",
                "Nettoyage des dégrilleurs hebdomadaire",
                "Surveillance des odeurs"
            ]
        
        return recommandations
    
    def generer_rapport_complet(self):
        """Génère le rapport complet"""
        return {
            "type_eau": self.type_eau,
            "norme_reference": self.norme,
            "date_diagnostic": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "parametres_saisis": self.valeurs,
            "indice_langelier": self.calculer_indice_langelier(),
            "non_conformites": self.analyser_conformite(),
            "traitements_proposes": self.determiner_traitements(),
            "filiere_traitement": self.construire_filiere(),
            "recommandations_suivi": self.recommandations_suivi()
        }


# ============================================================================
# INTERFACE UTILISATEUR
# ============================================================================

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #0066cc, #0099ff);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    .diagnostic-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .success {
        color: #28a745;
        font-weight: bold;
    }
    .warning {
        color: #ffc107;
        font-weight: bold;
    }
    .danger {
        color: #dc3545;
        font-weight: bold;
    }
    .info {
        color: #17a2b8;
        font-weight: bold;
    }
    .treatment-card {
        background-color: #e8f5e9;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #4caf50;
        margin: 0.5rem 0;
    }
    .footer {
        text-align: center;
        color: #6c757d;
        font-size: 0.8rem;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# En-tête
st.markdown("""
<div class="main-header">
    <h1>💧 AquaDiag</h1>
    <p>Assistant intelligent de diagnostic et traitement des eaux</p>
    <p style="font-size: 0.9rem;">Master Ecohydrologie - INE/UAC</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 📋 Configuration")
    
    type_eau = st.selectbox(
        "Type d'eau à traiter",
        options=["eau_surface", "eau_souterraine", "eau_atmospherique", "eau_usee"],
        format_func=lambda x: {
            "eau_surface": "🌊 Eau de surface (rivière, lac, barrage)",
            "eau_souterraine": "⛲ Eau souterraine (puits, forage)",
            "eau_atmospherique": "☁️ Eau atmosphérique (pluie, condensation)",
            "eau_usee": "🏭 Eau usée (domestique, industrielle)"
        }[x]
    )
    
    if type_eau != "eau_usee":
        norme = st.selectbox(
            "Norme de référence",
            options=["OMS_2011", "BENIN_2001_094"],
            format_func=lambda x: "🌍 " + NORMES_EAU_POTABLE[x]["nom"] if x == "OMS_2011" else "🇧🇯 " + NORMES_EAU_POTABLE[x]["nom"]
        )
    else:
        norme = "REJET"
        st.info("📌 Normes de rejet applicables aux eaux usées")
    
    st.markdown("---")
    st.caption("📚 Sources : Directives OMS 2011, Décret béninois 2001-094")
    st.caption("🎓 Cours de Master Ecohydrologie - INE/UAC")

# Définition des valeurs par défaut
VALEURS_PAR_DEFAUT = {
    "eau_surface": {
        "pH": 7.2, "temperature": 25, "turbidite": 15, "couleur": 20,
        "mes": 50, "dco": 40, "dbo5": 10, "nitrates": 25, "phosphates": 2,
        "alcalinite": 120, "durete_totale": 150, "durete_calcique": 80,
        "chlorures": 20, "sulfates": 30, "fer": 0.5, "manganese": 0.05
    },
    "eau_souterraine": {
        "pH": 7.0, "temperature": 22, "conductivite": 800, "durete_totale": 250,
        "alcalinite": 180, "nitrates": 35, "fer": 0.8, "manganese": 0.15,
        "fluorures": 0.8, "chlorures": 25, "sulfates": 40
    },
    "eau_atmospherique": {
        "pH": 6.0, "conductivite": 50, "nitrates": 5, "sulfates": 8, "ammonium": 2
    },
    "eau_usee": {
        "pH": 7.5, "temperature": 25, "mes": 250, "dco": 500, "dbo5": 250,
        "ntk": 50, "phosphore_total": 12, "conductivite": 1200
    }
}

# Interface de saisie
st.markdown("## 📊 Saisie des paramètres de l'eau brute")

with st.expander("ℹ️ À propos des paramètres - Cliquez pour plus d'informations"):
    st.markdown("""
    | Paramètre | Description | Valeur typique | Norme |
    |-----------|-------------|----------------|-------|
    | **pH** | Potentiel hydrogène (acidité/alcalinité) | 6.5-8.5 | 6.5-8.5 |
    | **Turbidité** | Mesure de la clarté de l'eau (NTU) | < 5 NTU | < 5 NTU |
    | **MES** | Matières en Suspension (mg/L) | < 30 mg/L | < 30 mg/L |
    | **DCO** | Demande Chimique en Oxygène (mg O₂/L) | < 90 mg/L | < 90 mg/L |
    | **DBO5** | Demande Biologique en Oxygène (mg O₂/L) | < 30 mg/L | < 30 mg/L |
    | **Fer** | Concentration en fer (mg/L) | < 0.3 mg/L | < 0.3 mg/L |
    | **Manganèse** | Concentration en manganèse (mg/L) | < 0.1 mg/L | < 0.1 mg/L |
    | **Nitrates** | Concentration en nitrates (mg/L) | < 50 mg/L | < 50 mg/L |
    | **Dureté** | Concentration en calcium et magnésium (mg/L CaCO₃) | < 200 mg/L | < 200 mg/L |
    """)

# Création dynamique des champs
valeurs_saisies = {}

if type_eau == "eau_surface":
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🌡️ Paramètres physiques")
        valeurs_saisies["pH"] = st.number_input("pH", min_value=0.0, max_value=14.0, value=7.2, step=0.1)
        valeurs_saisies["temperature"] = st.number_input("Température (°C)", min_value=0.0, max_value=50.0, value=25.0)
        valeurs_saisies["turbidite"] = st.number_input("Turbidité (NTU)", min_value=0.0, value=15.0)
        valeurs_saisies["couleur"] = st.number_input("Couleur (mg/L Pt)", min_value=0.0, value=20.0)
    
    with col2:
        st.subheader("🧪 Paramètres organiques")
        valeurs_saisies["mes"] = st.number_input("MES (mg/L)", min_value=0.0, value=50.0)
        valeurs_saisies["dco"] = st.number_input("DCO (mg O₂/L)", min_value=0.0, value=40.0)
        valeurs_saisies["dbo5"] = st.number_input("DBO5 (mg O₂/L)", min_value=0.0, value=10.0)
        valeurs_saisies["nitrates"] = st.number_input("Nitrates (mg/L)", min_value=0.0, value=25.0)
    
    with col3:
        st.subheader("⚙️ Paramètres minéraux")
        valeurs_saisies["alcalinite"] = st.number_input("Alcalinité TAC (mg/L CaCO₃)", min_value=0.0, value=120.0)
        valeurs_saisies["durete_totale"] = st.number_input("Dureté totale TH (mg/L CaCO₃)", min_value=0.0, value=150.0)
        valeurs_saisies["fer"] = st.number_input("Fer (mg/L)", min_value=0.0, value=0.5, step=0.05)
        valeurs_saisies["manganese"] = st.number_input("Manganèse (mg/L)", min_value=0.0, value=0.05, step=0.01)

elif type_eau == "eau_souterraine":
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🌡️ Paramètres physiques")
        valeurs_saisies["pH"] = st.number_input("pH", min_value=0.0, max_value=14.0, value=7.0, step=0.1)
        valeurs_saisies["temperature"] = st.number_input("Température (°C)", min_value=0.0, max_value=50.0, value=22.0)
        valeurs_saisies["conductivite"] = st.number_input("Conductivité (µS/cm)", min_value=0.0, value=800.0)
    
    with col2:
        st.subheader("🧪 Paramètres chimiques")
        valeurs_saisies["durete_totale"] = st.number_input("Dureté totale TH (mg/L CaCO₃)", min_value=0.0, value=250.0)
        valeurs_saisies["alcalinite"] = st.number_input("Alcalinité TAC (mg/L CaCO₃)", min_value=0.0, value=180.0)
        valeurs_saisies["nitrates"] = st.number_input("Nitrates (mg/L)", min_value=0.0, value=35.0)
    
    with col3:
        st.subheader("⚙️ Métaux")
        valeurs_saisies["fer"] = st.number_input("Fer (mg/L)", min_value=0.0, value=0.8, step=0.05)
        valeurs_saisies["manganese"] = st.number_input("Manganèse (mg/L)", min_value=0.0, value=0.15, step=0.01)
        valeurs_saisies["fluorures"] = st.number_input("Fluorures (mg/L)", min_value=0.0, value=0.8)

elif type_eau == "eau_atmospherique":
    col1, col2 = st.columns(2)
    
    with col1:
        valeurs_saisies["pH"] = st.number_input("pH", min_value=0.0, max_value=14.0, value=6.0, step=0.1)
        valeurs_saisies["conductivite"] = st.number_input("Conductivité (µS/cm)", min_value=0.0, value=50.0)
    
    with col2:
        valeurs_saisies["nitrates"] = st.number_input("Nitrates (mg/L)", min_value=0.0, value=5.0)
        valeurs_saisies["sulfates"] = st.number_input("Sulfates (mg/L)", min_value=0.0, value=8.0)

else:  # eau_usee
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🌡️ Paramètres physiques")
        valeurs_saisies["pH"] = st.number_input("pH", min_value=0.0, max_value=14.0, value=7.5, step=0.1)
        valeurs_saisies["temperature"] = st.number_input("Température (°C)", min_value=0.0, max_value=50.0, value=25.0)
        valeurs_saisies["mes"] = st.number_input("MES (mg/L)", min_value=0.0, value=250.0)
    
    with col2:
        st.subheader("🧪 Paramètres organiques")
        valeurs_saisies["dco"] = st.number_input("DCO (mg O₂/L)", min_value=0.0, value=500.0)
        valeurs_saisies["dbo5"] = st.number_input("DBO5 (mg O₂/L)", min_value=0.0, value=250.0)
    
    with col3:
        st.subheader("⚙️ Nutriments")
        valeurs_saisies["ntk"] = st.number_input("NTK - Azote total (mg/L)", min_value=0.0, value=50.0)
        valeurs_saisies["phosphore_total"] = st.number_input("Phosphore total (mg/L)", min_value=0.0, value=12.0)

# Bouton de diagnostic
st.markdown("---")
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    diagnostiquer = st.button("🔍 DIAGNOSTIQUER ET PRESCRIRE LE TRAITEMENT", type="primary", use_container_width=True)

# Exécution du diagnostic
if diagnostiquer:
    # Création de l'instance
    diagnostic = DiagnosticEau(type_eau, valeurs_saisies, norme if type_eau != "eau_usee" else "OMS_2011")
    
    # Résultats
    st.markdown("---")
    st.markdown("## 📋 RÉSULTATS DU DIAGNOSTIC")
    
    # 1. Synthèse des paramètres
    with st.expander("📊 Synthèse des paramètres saisis", expanded=True):
        df_params = pd.DataFrame([valeurs_saisies]).T
        df_params.columns = ["Valeur mesurée"]
        df_params["Unité"] = {
            "pH": "", "temperature": "°C", "turbidite": "NTU", "couleur": "mg/L Pt",
            "mes": "mg/L", "dco": "mg O₂/L", "dbo5": "mg O₂/L", "nitrates": "mg/L",
            "alcalinite": "mg/L CaCO₃", "durete_totale": "mg/L CaCO₃", "fer": "mg/L",
            "manganese": "mg/L", "conductivite": "µS/cm", "fluorures": "mg/L",
            "sulfates": "mg/L", "chlorures": "mg/L", "ntk": "mg/L", "phosphore_total": "mg/L"
        }.get
        st.dataframe(df_params, use_container_width=True)
    
    # 2. Analyse de conformité
    non_conformites = diagnostic.analyser_conformite()
    
    st.subheader("✅ Analyse de conformité")
    
    if non_conformites:
        st.markdown("##### ⚠️ Paramètres non conformes détectés")
        for nc in non_conformites:
            st.markdown(f"""
            <div class="diagnostic-card">
            <span class="danger">❌ <b>{nc['parametre'].replace('_', ' ').upper()}</b></span><br>
            Valeur mesurée : <b>{nc['valeur']}</b><br>
            Norme : <b>{nc.get('limite', nc.get('norme', 'N/A'))}</b><br>
            Écart : <b>{nc.get('ecart', 'Hors plage')}</b>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="diagnostic-card">
        <span class="success">✅ Tous les paramètres sont conformes aux normes</span><br>
        <span class="info">🌍 {NORMES_EAU_POTABLE[norme]['nom'] if type_eau != 'eau_usee' else 'Normes de rejet'}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # 3. Indice de Langelier (pour eaux naturelles)
    if type_eau != "eau_usee" and "alcalinite" in valeurs_saisies:
        is_langelier = diagnostic.calculer_indice_langelier()
        st.subheader("⚖️ Équilibre calco-carbonique")
        
        col_i1, col_i2, col_i3 = st.columns(3)
        with col_i1:
            st.metric("Indice de Langelier (Is)", f"{is_langelier:.2f}")
        with col_i2:
            if is_langelier < -0.5:
                st.warning("⚠️ Eau agressive - Risque de corrosion des canalisations")
            elif is_langelier > 0.5:
                st.warning("⚠️ Eau incrustante - Risque d'entartrage")
            else:
                st.success("✅ Eau à l'équilibre")
        with col_i3:
            if is_langelier < -0.5:
                st.info("💡 Traitement : Aération ou filtration sur Neutralite")
            elif is_langelier > 0.5:
                st.info("💡 Traitement : Injection de CO₂ ou adoucissement")
    
    # 4. Traitements proposés
    traitements = diagnostic.determiner_traitements()
    
    st.subheader("🔧 Traitements prescrits")
    
    if traitements:
        for traitement in traitements:
            st.markdown(f"""
            <div class="treatment-card">
            <strong>📌 {traitement.get('etape', '').replace('_', ' ').upper()}</strong><br>
            {traitement.get('detail', '')}
            </div>
            """, unsafe_allow_html=True)
            
            if "dose_chaux_mgL" in traitement:
                st.success(f"🧪 **Dose de chaux** : {traitement['dose_chaux_mgL']} mg/L")
            if "dose_soude_mgL" in traitement:
                st.success(f"🧪 **Dose de soude** : {traitement['dose_soude_mgL']} mg/L")
            if "dose_chlore_mgL" in traitement:
                st.info(f"💊 **Dose de chlore** : {traitement['dose_chlore_mgL']} mg/L")
            if "dose_kmno4_mgL" in traitement:
                st.info(f"💊 **Dose de KMnO₄** : {traitement['dose_kmno4_mgL']} mg/L")
    else:
        st.success("✅ Aucun traitement spécifique nécessaire - L'eau est conforme")
    
    # 5. Filière complète
    filiere = diagnostic.construire_filiere()
    
    st.subheader("🏭 Filière de traitement recommandée")
    
    for etape in filiere:
        st.markdown(f"- {etape}")
    
    # 6. Rapport DCO/DBO5 pour eaux usées
    if type_eau == "eau_usee" and "dbo5" in valeurs_saisies and valeurs_saisies["dbo5"] > 0:
        rapport = valeurs_saisies["dco"] / valeurs_saisies["dbo5"]
        st.subheader("📈 Biodégradabilité")
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.metric("Rapport DCO/DBO5", f"{rapport:.2f}")
        with col_r2:
            if rapport < 1.5:
                st.success("Très biodégradable - Traitement biologique adapté")
            elif rapport < 2.5:
                st.info("Biodégradabilité moyenne - Traitement biologique possible")
            elif rapport < 3:
                st.warning("Faiblement biodégradable - Prétraitement nécessaire")
            else:
                st.error("Non biodégradable - Traitement physico-chimique uniquement")
    
    # 7. Graphique comparatif
    if type_eau != "eau_usee":
        st.subheader("📊 Visualisation comparative")
        
        # Sélection des paramètres à comparer
        params_afficher = ["pH", "nitrates", "fer", "manganese", "durete_totale"]
        data_comp = []
        
        for param in params_afficher:
            if param in valeurs_saisies and param in NORMES_EAU_POTABLE[norme]["chimiques"]:
                norme_param = NORMES_EAU_POTABLE[norme]["chimiques"][param]
                limite = norme_param.get("limite", norme_param.get("max", 100))
                data_comp.append({
                    "Paramètre": param.replace("_", " ").title(),
                    "Valeur": valeurs_saisies[param],
                    "Norme": limite
                })
        
        if data_comp:
            df_comp = pd.DataFrame(data_comp)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_comp["Paramètre"], y=df_comp["Valeur"], name="Valeur mesurée", marker_color="#0066cc"))
            fig.add_trace(go.Bar(x=df_comp["Paramètre"], y=df_comp["Norme"], name="Norme", marker_color="#ff6600"))
            fig.update_layout(title="Comparaison avec les normes", yaxis_title="Concentration", barmode="group")
            st.plotly_chart(fig, use_container_width=True)
    
    # 8. Recommandations de suivi
    with st.expander("📋 Recommandations de suivi et maintenance"):
        suivis = diagnostic.recommandations_suivi()
        st.markdown(f"**📅 Fréquence de contrôle recommandée** : {suivis['frequence_controle']}")
        st.markdown(f"**🎯 Paramètres clés à surveiller** : {', '.join(suivis['parametres_cles']) if suivis['parametres_cles'] else 'Selon analyse précédente'}")
        if suivis['maintenance_preventive']:
            st.markdown("**🔧 Maintenance préventive** :")
            for maint in suivis['maintenance_preventive']:
                st.markdown(f"- {maint}")
    
    # 9. Export du rapport
    st.subheader("📄 Export du rapport")
    
    rapport_complet = diagnostic.generer_rapport_complet()
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        rapport_json = json.dumps(rapport_complet, indent=2, default=str, ensure_ascii=False)
        st.download_button(
            label="📥 Télécharger le rapport (JSON)",
            data=rapport_json,
            file_name=f"diagnostic_{type_eau}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    with col_e2:
        # Export PDF simplifié
        rapport_texte = f"""
        AQUADIAG - RAPPORT DE DIAGNOSTIC
        =================================
        Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        Type d'eau: {type_eau}
        Norme: {norme}
        
        PARAMÈTRES MESURÉS:
        {json.dumps(valeurs_saisies, indent=2, ensure_ascii=False)}
        
        TRAITEMENTS PROPOSÉS:
        {json.dumps(traitements, indent=2, ensure_ascii=False, default=str)}
        
        FILIÈRE DE TRAITEMENT:
        {chr(10).join(filiere)}
        """
        st.download_button(
            label="📥 Télécharger le rapport (TXT)",
            data=rapport_texte,
            file_name=f"rapport_{type_eau}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )

# Footer
st.markdown("""
<div class="footer">
    <p>AquaDiag v1.0 | Développé dans le cadre du Master Ecohydrologie - INE/UAC</p>
    <p>Sources: OMS (2011), Décret béninois 2001-094, Cours de traitement des eaux</p>
    <p>⚠️ Application à usage pédagogique - Consulter un expert pour une décision réelle</p>
</div>
""", unsafe_allow_html=True)