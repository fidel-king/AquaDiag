"""
AquaDiag - Moteur de diagnostic (sans interface).

Ce module contient les normes, les calculs physico-chimiques et la logique de
prescription. Il est indépendant de Streamlit afin de pouvoir être testé.

Convention : toutes les clés de paramètres sont les mêmes partout
(saisie, normes, calculs) — voir PARAMETRES.
"""

from datetime import datetime
import math

# ============================================================================
# PARAMÈTRES (clé unique -> libellé et unité)
# ============================================================================

PARAMETRES = {
    "pH": {"libelle": "pH", "unite": ""},
    "temperature": {"libelle": "Température", "unite": "°C"},
    "turbidite": {"libelle": "Turbidité", "unite": "NTU"},
    "couleur": {"libelle": "Couleur", "unite": "mg/L Pt"},
    "conductivite": {"libelle": "Conductivité", "unite": "µS/cm"},
    "mes": {"libelle": "MES", "unite": "mg/L"},
    "dco": {"libelle": "DCO", "unite": "mg O₂/L"},
    "dbo5": {"libelle": "DBO5", "unite": "mg O₂/L"},
    "ntk": {"libelle": "NTK", "unite": "mg N/L"},
    "phosphore_total": {"libelle": "Phosphore total", "unite": "mg P/L"},
    "nitrates": {"libelle": "Nitrates", "unite": "mg/L NO₃⁻"},
    "fluorures": {"libelle": "Fluorures", "unite": "mg/L"},
    "sulfates": {"libelle": "Sulfates", "unite": "mg/L"},
    "chlorures": {"libelle": "Chlorures", "unite": "mg/L"},
    "alcalinite": {"libelle": "Alcalinité TAC", "unite": "mg/L CaCO₃"},
    "durete_totale": {"libelle": "Dureté totale TH", "unite": "mg/L CaCO₃"},
    "durete_calcique": {"libelle": "Dureté calcique", "unite": "mg/L CaCO₃"},
    "fer": {"libelle": "Fer", "unite": "mg/L"},
    "manganese": {"libelle": "Manganèse", "unite": "mg/L"},
    "arsenic": {"libelle": "Arsenic", "unite": "µg/L"},
    "cadmium": {"libelle": "Cadmium", "unite": "µg/L"},
    "mercure": {"libelle": "Mercure", "unite": "µg/L"},
    "plomb": {"libelle": "Plomb", "unite": "µg/L"},
    "e_coli": {"libelle": "Escherichia coli", "unite": "UFC/100 mL"},
    "coliformes_fecaux": {"libelle": "Coliformes fécaux", "unite": "UFC/100 mL"},
    "coliformes_totaux": {"libelle": "Coliformes totaux", "unite": "UFC/100 mL"},
    "streptocoques_fecaux": {"libelle": "Streptocoques fécaux", "unite": "UFC/100 mL"},
    "clostridium_perfringens": {"libelle": "Clostridium perfringens", "unite": "UFC/20 mL"},
    "germes_banals": {"libelle": "Germes banals", "unite": "UFC/mL"},
}


def libelle(param):
    return PARAMETRES.get(param, {}).get("libelle", param.replace("_", " ").capitalize())


def unite(param):
    return PARAMETRES.get(param, {}).get("unite", "")


# ============================================================================
# NORMES
# nature : "sanitaire" (valeur guide liée à la santé),
#          "acceptabilite" (goût, couleur, dépôts, exploitation),
#          "reglementaire" (valeur fixée par un texte national)
# ============================================================================

NORMES_EAU_POTABLE = {
    "OMS_2011": {
        "nom": "Organisation Mondiale de la Santé (2011)",
        "parametres": {
            "e_coli": {"limite": 0, "nature": "sanitaire"},
            "coliformes_fecaux": {"limite": 0, "nature": "sanitaire"},
            "pH": {"min": 6.5, "max": 8.5, "nature": "acceptabilite"},
            "fluorures": {"limite": 1.5, "nature": "sanitaire"},
            "nitrates": {"limite": 50, "nature": "sanitaire"},
            "arsenic": {"limite": 10, "nature": "sanitaire"},
            "cadmium": {"limite": 3, "nature": "sanitaire"},
            "mercure": {"limite": 6, "nature": "sanitaire"},
            "plomb": {"limite": 10, "nature": "sanitaire"},
            "fer": {"limite": 0.3, "nature": "acceptabilite"},
            "manganese": {"limite": 0.1, "nature": "acceptabilite"},
            "durete_totale": {"limite": 200, "nature": "acceptabilite"},
            "sulfates": {"limite": 250, "nature": "acceptabilite"},
            "chlorures": {"limite": 250, "nature": "acceptabilite"},
            "turbidite": {"limite": 5, "nature": "acceptabilite"},
        },
    },
    "BENIN_2001_094": {
        "nom": "République du Bénin - Décret 2001-094",
        "parametres": {
            "germes_banals": {"limite": 20, "nature": "reglementaire"},
            "e_coli": {"limite": 0, "nature": "reglementaire"},
            "coliformes_totaux": {"limite": 0, "nature": "reglementaire"},
            "streptocoques_fecaux": {"limite": 0, "nature": "reglementaire"},
            "clostridium_perfringens": {"limite": 0, "nature": "reglementaire"},
            "pH": {"min": 6.5, "max": 8.5, "nature": "reglementaire"},
            "sulfates": {"limite": 500, "nature": "reglementaire"},
            "durete_totale": {"limite": 200, "nature": "reglementaire"},
            "fer": {"limite": 0.3, "nature": "reglementaire"},
            "fluorures": {"limite": 1.5, "nature": "reglementaire"},
            "manganese": {"limite": 0.1, "nature": "reglementaire"},
            "nitrates": {"limite": 45, "nature": "reglementaire"},
            "arsenic": {"limite": 50, "nature": "reglementaire"},
            "cadmium": {"limite": 5, "nature": "reglementaire"},
            "mercure": {"limite": 1, "nature": "reglementaire"},
        },
    },
}

NORMES_REJET_EAU_USEE = {
    "nom": "Normes de rejet des eaux usées",
    "parametres": {
        "dbo5": {"limite": 30, "nature": "reglementaire"},
        "dco": {"limite": 90, "nature": "reglementaire"},
        "mes": {"limite": 30, "nature": "reglementaire"},
        "ntk": {"limite": 40, "nature": "reglementaire"},
        "phosphore_total": {"limite": 10, "nature": "reglementaire"},
        "pH": {"min": 5.5, "max": 8.5, "nature": "reglementaire"},
        "coliformes_fecaux": {"limite": 2000, "nature": "reglementaire"},
    },
}

NATURES = {
    "sanitaire": "Valeur guide sanitaire",
    "acceptabilite": "Seuil d'acceptabilité (goût, aspect, exploitation)",
    "reglementaire": "Valeur réglementaire",
}

TYPES_EAU = ["eau_surface", "eau_souterraine", "eau_atmospherique", "eau_usee"]

# ============================================================================
# CHIMIE DES CARBONATES
# ============================================================================

M_CACO3 = 100.09  # g/mol
EQ_CACO3 = 50.04  # g/éq
M_CAOH2 = 74.09  # g/mol
M_CO2 = 44.01  # g/mol
TDS_PAR_DEFAUT = 250.0  # mg/L, utilisé si la conductivité n'est pas connue
FACTEUR_TDS_CONDUCTIVITE = 0.65  # TDS (mg/L) ≈ 0,65 × conductivité (µS/cm)


def pk1_carbonique(t_celsius):
    """pK1 de l'acide carbonique (Harned et Davis)."""
    T = t_celsius + 273.15
    return 3404.71 / T + 0.032786 * T - 14.8435


def pk2_carbonique(t_celsius):
    """pK2 de l'acide carbonique (Harned et Scholes)."""
    T = t_celsius + 273.15
    return 2902.39 / T + 0.02379 * T - 6.498


def pks_calcite(t_celsius):
    """pKs de la calcite (Plummer et Busenberg, 1982)."""
    T = t_celsius + 273.15
    return 171.9065 + 0.077993 * T - 2839.319 / T - 71.595 * math.log10(T)


def log_gamma_davies(charge, tds_mgL):
    """log10 du coefficient d'activité (équation de Davies), I ≈ 2,5e-5 × TDS."""
    force_ionique = 2.5e-5 * tds_mgL
    racine = math.sqrt(force_ionique)
    return -0.51 * charge**2 * (racine / (1 + racine) - 0.3 * force_ionique)


def ph_saturation(ca_caco3_mgL, tac_caco3_mgL, t_celsius, tds_mgL):
    """pH de saturation de la calcite (pHs).

    ca_caco3_mgL : dureté calcique en mg/L CaCO₃
    tac_caco3_mgL : alcalinité en mg/L CaCO₃ (supposée bicarbonatée, pH < 8,3)
    """
    ca_mol = ca_caco3_mgL / (M_CACO3 * 1000)
    hco3_mol = tac_caco3_mgL / (EQ_CACO3 * 1000)
    p_ca = -(math.log10(ca_mol) + log_gamma_davies(2, tds_mgL))
    p_hco3 = -(math.log10(hco3_mol) + log_gamma_davies(1, tds_mgL))
    return pk2_carbonique(t_celsius) - pks_calcite(t_celsius) + p_ca + p_hco3


def classer_biodegradabilite(rapport):
    """Classe un effluent selon le rapport DCO/DBO5.

    Retourne (code, libellé, filière biologique conseillée).
    """
    if rapport < 2:
        return ("facile", "Effluent facilement biodégradable",
                "Boues activées ou lagunage")
    if rapport < 3:
        return ("moyenne", "Biodégradable avec une biomasse adaptée",
                "Lits bactériens, biofiltres ou boues activées")
    return ("faible", "Peu biodégradable",
            "Prétraitement physico-chimique (coagulation-floculation) avant le biologique")


# ============================================================================
# CLASSE PRINCIPALE DE DIAGNOSTIC
# ============================================================================


class DiagnosticEau:
    """Diagnostic et prescription des traitements"""

    def __init__(self, type_eau, valeurs_parametres, norme="OMS_2011"):
        if type_eau not in TYPES_EAU:
            raise ValueError(f"Type d'eau inconnu : {type_eau}")
        self.type_eau = type_eau
        self.valeurs = dict(valeurs_parametres)
        self.norme = norme if norme in NORMES_EAU_POTABLE else "OMS_2011"

    # ---------------------------------------------------------------- normes
    def referentiel(self):
        if self.type_eau == "eau_usee":
            return NORMES_REJET_EAU_USEE
        return NORMES_EAU_POTABLE[self.norme]

    def limite(self, param, defaut=None):
        """Limite maximale du paramètre dans la norme retenue."""
        entree = self.referentiel()["parametres"].get(param, {})
        return entree.get("limite", entree.get("max", defaut))

    def analyser_conformite(self):
        """Compare chaque valeur saisie à la norme retenue."""
        non_conformites = []
        for param, norme_param in self.referentiel()["parametres"].items():
            if param not in self.valeurs or self.valeurs[param] is None:
                continue
            valeur = self.valeurs[param]
            base = {
                "parametre": param,
                "libelle": libelle(param),
                "valeur": valeur,
                "unite": unite(param),
                "nature": norme_param.get("nature", "reglementaire"),
            }
            if "limite" in norme_param:
                if valeur > norme_param["limite"]:
                    non_conformites.append({
                        **base,
                        "norme": f"≤ {norme_param['limite']}",
                        "limite": norme_param["limite"],
                        "ecart": round(valeur - norme_param["limite"], 4),
                    })
            elif valeur < norme_param["min"] or valeur > norme_param["max"]:
                borne = norme_param["min"] if valeur < norme_param["min"] else norme_param["max"]
                non_conformites.append({
                    **base,
                    "norme": f"{norme_param['min']} – {norme_param['max']}",
                    "ecart": round(valeur - borne, 4),
                })
        return non_conformites

    # ------------------------------------------------- équilibre calcocarbonique
    def _tds(self, hypotheses):
        if self.valeurs.get("conductivite"):
            return FACTEUR_TDS_CONDUCTIVITE * self.valeurs["conductivite"]
        hypotheses.append(f"Conductivité inconnue : TDS supposé égal à {TDS_PAR_DEFAUT:.0f} mg/L")
        return TDS_PAR_DEFAUT

    def _calcium(self, hypotheses):
        if self.valeurs.get("durete_calcique"):
            return self.valeurs["durete_calcique"]
        hypotheses.append("Dureté calcique inconnue : dureté totale utilisée (Is surestimé)")
        return self.valeurs.get("durete_totale")

    def details_langelier(self):
        """Indice de Langelier avec pHs et hypothèses retenues.

        Retourne None si les données sont insuffisantes.
        """
        hypotheses = []
        ph = self.valeurs.get("pH")
        tac = self.valeurs.get("alcalinite")
        ca = self._calcium(hypotheses)
        if ph is None or not tac or not ca:
            return None
        if "temperature" in self.valeurs:
            temperature = self.valeurs["temperature"]
        else:
            temperature = 25.0
            hypotheses.append("Température inconnue : 25 °C supposés")
        if ph >= 8.3:
            hypotheses.append("pH ≥ 8,3 : l'alcalinité n'est plus entièrement bicarbonatée")
        tds = self._tds(hypotheses)
        phs = ph_saturation(ca, tac, temperature, tds)
        return {
            "indice": ph - phs,
            "phs": phs,
            "tds": tds,
            "calcium": ca,
            "temperature": temperature,
            "hypotheses": hypotheses,
        }

    def calculer_indice_langelier(self):
        """Indice de saturation de Langelier Is = pH − pHs (None si données insuffisantes)."""
        details = self.details_langelier()
        return None if details is None else details["indice"]

    def corriger_agressivite(self):
        """Dose de chaux Ca(OH)₂ pour amener l'eau à l'équilibre calcocarbonique.

        Ca(OH)₂ + 2 CO₂ → Ca(HCO₃)₂ : on neutralise x mmol/L de CO₂ libre jusqu'à
        ce que pH = pHs. Résolution par dichotomie.
        """
        details = self.details_langelier()
        if details is None or details["indice"] >= 0:
            return None
        t = details["temperature"]
        tds = details["tds"]
        pk1 = pk1_carbonique(t)
        gamma1 = 10 ** log_gamma_davies(1, tds)
        hco3_0 = self.valeurs["alcalinite"] / EQ_CACO3  # mmol/L
        ca_0 = details["calcium"] / M_CACO3  # mmol/L
        co2_0 = gamma1 * hco3_0 * 10 ** (pk1 - self.valeurs["pH"])  # mmol/L

        def ecart(x):
            hco3 = hco3_0 + x
            co2 = co2_0 - x
            ca = ca_0 + x / 2
            ph = pk1 + math.log10(gamma1 * hco3 / co2)
            phs = ph_saturation(ca * M_CACO3, hco3 * EQ_CACO3, t, tds)
            return ph - phs

        bas, haut = 0.0, co2_0 * (1 - 1e-9)
        for _ in range(100):
            milieu = (bas + haut) / 2
            if ecart(milieu) < 0:
                bas = milieu
            else:
                haut = milieu
        x = (bas + haut) / 2
        return {
            "co2_libre_mgL": round(co2_0 * M_CO2, 1),
            "co2_neutralise_mgL": round(x * M_CO2, 1),
            "dose_chaux_mgL": round(x / 2 * M_CAOH2, 1),
        }

    # ----------------------------------------------------------- traitements
    def calculer_dose_coagulant(self):
        """Dose indicative de coagulant selon la turbidité (à confirmer par jar-test)."""
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
            "ph_optimal": "6.0 - 7.5",
        }

    def traiter_fer(self):
        """Déferrisation"""
        fe_mgl = self.valeurs.get("fer", 0)
        if fe_mgl < 5:
            return {
                "etape": "deferrisation",
                "methode": "Aération + Filtration sur sable",
                "detail": f"Teneur en fer : {fe_mgl} mg/L - Oxydation à l'air (10-20 min de contact)",
                "temps_contact": "10-20 minutes",
            }
        return {
            "etape": "deferrisation",
            "methode": "Oxydation chimique",
            "detail": f"Teneur en fer : {fe_mgl} mg/L - Oxydation au chlore puis filtration",
            "dose_chlore_mgL": round(fe_mgl * 0.63, 2),  # stœchiométrie : 0,63 mg Cl₂ / mg Fe
            "ph_optimal": 7.2,
        }

    def traiter_manganese(self):
        """Démanganisation"""
        mn_mgl = self.valeurs.get("manganese", 0)
        return {
            "etape": "demanganisation",
            "methode": "Oxydation au permanganate de potassium",
            "detail": f"Teneur en manganèse : {mn_mgl} mg/L - Éviter l'excès de KMnO₄ (teinte rose)",
            "dose_kmno4_mgL": round(mn_mgl * 1.92, 2),  # stœchiométrie : 1,92 mg KMnO₄ / mg Mn
            "ph_optimal": 7.2,
        }

    def traiter_durete(self):
        """Adoucissement partiel jusqu'à 150 mg/L CaCO₃"""
        th = self.valeurs.get("durete_totale", 200)
        tac = self.valeurs.get("alcalinite", 150)
        reduction = th - 150
        if reduction <= 0:
            return {"etape": "aucun", "detail": "Dureté conforme aux normes"}
        if tac >= reduction:
            return {
                "etape": "adoucissement",
                "methode": "Chaux seule",
                "detail": f"Réduction de la dureté de {reduction:.0f} mg/L CaCO₃ (décarbonatation)",
                "dose_chaux_mgL": round(0.74 * reduction, 1),
                "reaction": "Ca(HCO₃)₂ + Ca(OH)₂ → 2CaCO₃↓ + 2H₂O",
            }
        durete_permanente = th - tac
        return {
            "etape": "adoucissement",
            "methode": "Chaux + Soude",
            "detail": f"Dureté permanente de {durete_permanente:.0f} mg/L CaCO₃",
            "dose_chaux_mgL": round(0.74 * tac, 1),
            "dose_soude_mgL": round(1.06 * durete_permanente, 1),
            "reaction": "Na₂CO₃ + CaSO₄ → CaCO₃↓ + Na₂SO₄",
        }

    def _traitements_equilibre(self):
        traitements = []
        details = self.details_langelier()
        if details is None:
            return traitements
        indice = details["indice"]
        if indice < -0.5:
            traitements.append({
                "etape": "correction_agressivite",
                "detail": f"Eau agressive (Is = {indice:.2f}) - Risque de corrosion",
                **(self.corriger_agressivite() or {}),
            })
        elif indice > 0.5:
            traitements.append({
                "etape": "correction_incrustation",
                "detail": f"Eau incrustante (Is = {indice:.2f}) - Risque d'entartrage. "
                          "Injection de CO₂ ou adoucissement partiel",
            })
        return traitements

    def _depasse(self, param, defaut):
        return self.valeurs.get(param, 0) > self.limite(param, defaut)

    def determiner_traitements(self):
        """Traitements spécifiques prescrits"""
        traitements = []

        if self.type_eau == "eau_surface":
            traitements.append({
                "etape": "pretraitement",
                "detail": "Dégrillage (10-30 mm), tamisage (0,5-3 mm), dessablage-déshuilage",
            })
            traitements.append({
                "etape": "clarification",
                "detail": "Coagulation-floculation, décantation lamellaire, filtration sur sable",
            })
            if self._depasse("turbidite", 5):
                dose = self.calculer_dose_coagulant()
                traitements.append({
                    "etape": "coagulation_renforcee",
                    "detail": f"Turbidité élevée - {dose['coagulant']} ≈ {dose['dose_mgL']} mg/L "
                              f"(pH optimal {dose['ph_optimal']}), à confirmer par jar-test",
                    "dose_coagulant_mgL": dose["dose_mgL"],
                })
            if self._depasse("fer", 0.3):
                traitements.append(self.traiter_fer())
            if self._depasse("manganese", 0.1):
                traitements.append(self.traiter_manganese())
            traitements.extend(self._traitements_equilibre())

        elif self.type_eau == "eau_souterraine":
            traitements.extend(self._traitements_equilibre())
            if self._depasse("fer", 0.3):
                traitements.append(self.traiter_fer())
            if self._depasse("manganese", 0.1):
                traitements.append(self.traiter_manganese())
            if self._depasse("durete_totale", 200):
                traitements.append(self.traiter_durete())
            if self._depasse("fluorures", 1.5):
                traitements.append({
                    "etape": "defluoruration",
                    "detail": "Fluorures en excès - Adsorption sur alumine activée ou charbon d'os",
                })

        elif self.type_eau == "eau_atmospherique":
            if self.valeurs.get("pH", 7) < 6.5:
                traitements.append({
                    "etape": "correction_ph",
                    "detail": "Eau acide - Remontée du pH (filtration sur calcaire/Neutralite)",
                })

        elif self.type_eau == "eau_usee":
            dco = self.valeurs.get("dco", 0)
            dbo5 = self.valeurs.get("dbo5", 0)
            if dbo5 > 0:
                code, texte, filiere_bio = classer_biodegradabilite(dco / dbo5)
                traitements.append({
                    "etape": "traitement_biologique" if code != "faible"
                             else "pretraitement_physico_chimique",
                    "detail": f"{texte} (DCO/DBO5 = {dco / dbo5:.2f}) - {filiere_bio}",
                })
            if self._depasse("ntk", 40):
                traitements.append({
                    "etape": "traitement_azote",
                    "detail": "Teneur en azote élevée - Nitrification-dénitrification",
                })
            if self._depasse("phosphore_total", 10):
                p = self.valeurs["phosphore_total"]
                traitements.append({
                    "etape": "traitement_phosphore",
                    "detail": "Teneur en phosphore élevée - Déphosphatation chimique "
                              "(Al/P stœchiométrique 0,87 ; prévoir 1,5 à 2 fois en pratique)",
                    "dose_aluminium_mgL": round(p * 0.87, 1),
                })

        return traitements

    # ---------------------------------------------------------------- filière
    def construire_filiere(self):
        """Filière de traitement complète (étapes non numérotées, dans l'ordre)."""
        filiere = []

        if self.type_eau == "eau_surface":
            filiere = [
                "📋 Dégrillage (grilles 10-30 mm)",
                "🔄 Tamisage (mailles 0,5-3 mm)",
                "🏖️ Dessablage - Déshuilage",
            ]
            if self._depasse("fer", 0.3) or self._depasse("manganese", 0.1):
                filiere.append("⚗️ Préoxydation (fer / manganèse)")
            filiere += [
                "🧪 Coagulation - Floculation",
                "⏳ Décantation lamellaire",
                "🧹 Filtration sur sable",
            ]
            if self._depasse("nitrates", 50):
                filiere.append("🌿 Élimination des nitrates (échange d'ions ou dénitrification biologique)")
            filiere += [
                "🎯 Affinage (charbon actif en grains si nécessaire)",
                "🧴 Désinfection (chlore, ozone ou UV)",
            ]

        elif self.type_eau == "eau_souterraine":
            filiere = ["💨 Aération (cascade ou injection d'air)"]
            if self._depasse("fer", 0.3) or self._depasse("manganese", 0.1):
                filiere.append("🦠 Déferrisation / Démanganisation (oxydation + filtration)")
            indice = self.calculer_indice_langelier()
            if indice is not None and indice < -0.5:
                filiere.append("⚗️ Correction de l'agressivité (filtration sur Neutralite ou injection de chaux)")
            elif indice is not None and indice > 0.5:
                filiere.append("💧 Stabilisation (injection de CO₂)")
            if self._depasse("durete_totale", 200):
                filiere.append("🧂 Adoucissement partiel")
            if self._depasse("fluorures", 1.5):
                filiere.append("🦴 Défluoruration (alumine activée ou charbon d'os)")
            if self._depasse("nitrates", 50):
                filiere.append("🌿 Élimination des nitrates (échange d'ions)")
            filiere.append("🧴 Désinfection (chlore ou UV)")

        elif self.type_eau == "eau_usee":
            dco = self.valeurs.get("dco", 0)
            dbo5 = self.valeurs.get("dbo5", 0)
            filiere = [
                "🗑️ Prétraitements (dégrillage, dessablage, déshuilage)",
                "🪣 Traitement primaire (décantation)",
            ]
            if dbo5 > 0:
                code, _, filiere_bio = classer_biodegradabilite(dco / dbo5)
                if code == "faible":
                    filiere.append("🧪 Traitement physico-chimique (coagulation-floculation)")
                    filiere.append("🧫 Traitement biologique secondaire (après abattement de la DCO dure)")
                else:
                    filiere.append(f"🧫 Traitement biologique secondaire : {filiere_bio}")
            if self._depasse("ntk", 40) or self._depasse("phosphore_total", 10):
                filiere.append("🎯 Traitement tertiaire (dénitrification / déphosphatation)")
            filiere.append("🧴 Désinfection (si rejet en zone sensible)")

        elif self.type_eau == "eau_atmospherique":
            filiere = ["🧹 Filtration grossière (premières eaux écartées)"]
            if self.valeurs.get("pH", 7) < 6.5:
                filiere.append("⚗️ Correction du pH (pluie acide)")
            filiere += [
                "🧴 Désinfection (UV ou chlore)",
                "💧 Stockage en cuve protégée",
            ]

        return filiere

    # ------------------------------------------------------------------ suivi
    def recommandations_suivi(self):
        recommandations = {
            "frequence_controle": "Trimestrielle",
            "parametres_cles": [],
            "maintenance_preventive": [],
        }
        if self.type_eau == "eau_surface":
            recommandations["frequence_controle"] = "Quotidienne (turbidité, chlore) / mensuelle (complète)"
            recommandations["parametres_cles"] = ["Turbidité", "pH", "Chlore résiduel"]
            recommandations["seuils_alerte"] = {"turbidite": 1, "chlore_residuel": 0.2}
            recommandations["maintenance_preventive"] = [
                "Nettoyage des grilles de dégrillage (quotidien)",
                "Contrôle des doses de coagulant (jar-test mensuel)",
                "Lavage des filtres à sable (1-2 fois/semaine)",
            ]
        elif self.type_eau == "eau_souterraine":
            recommandations["parametres_cles"] = ["pH", "Dureté", "Fer", "Manganèse"]
            recommandations["maintenance_preventive"] = [
                "Nettoyage des aérateurs tous les 6 mois",
                "Contrôle des filtres à sable",
                "Vérification de l'absence de colmatage",
            ]
        elif self.type_eau == "eau_usee":
            recommandations["frequence_controle"] = "Mensuelle (bilan 24 h)"
            recommandations["parametres_cles"] = ["DBO5", "DCO", "MES", "NTK"]
            recommandations["maintenance_preventive"] = [
                "Extraction régulière des boues",
                "Contrôle de l'oxygène dissous (> 2 mg/L en bassin d'aération)",
                "Nettoyage hebdomadaire des dégrilleurs",
                "Surveillance des odeurs",
            ]
        elif self.type_eau == "eau_atmospherique":
            recommandations["parametres_cles"] = ["pH", "Turbidité", "Bactériologie"]
            recommandations["maintenance_preventive"] = [
                "Nettoyage des gouttières et de la toiture avant la saison des pluies",
                "Nettoyage et désinfection annuels de la cuve",
            ]
        return recommandations

    def generer_rapport_complet(self):
        return {
            "type_eau": self.type_eau,
            "norme_reference": self.referentiel()["nom"],
            "date_diagnostic": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "parametres_saisis": self.valeurs,
            "equilibre_calcocarbonique": self.details_langelier(),
            "non_conformites": self.analyser_conformite(),
            "traitements_proposes": self.determiner_traitements(),
            "filiere_traitement": self.construire_filiere(),
            "recommandations_suivi": self.recommandations_suivi(),
        }
