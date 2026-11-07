"""Tests du moteur de diagnostic AquaDiag."""

import math

import pytest

from diagnostic import (
    NORMES_EAU_POTABLE,
    NORMES_REJET_EAU_USEE,
    DiagnosticEau,
    classer_biodegradabilite,
    pk2_carbonique,
    pks_calcite,
    ph_saturation,
)


def params(nc):
    return {n["parametre"] for n in nc}


# --------------------------------------------------------------- conformité

def test_toutes_les_cles_de_norme_sont_des_parametres_connus():
    from diagnostic import PARAMETRES
    for norme in NORMES_EAU_POTABLE.values():
        assert set(norme["parametres"]) <= set(PARAMETRES)
    assert set(NORMES_REJET_EAU_USEE["parametres"]) <= set(PARAMETRES)


def test_nitrates_eleves_detectes_eau_surface():
    d = DiagnosticEau("eau_surface", {"pH": 7.2, "nitrates": 80})
    assert params(d.analyser_conformite()) == {"nitrates"}


def test_eau_usee_brute_non_conforme_au_rejet():
    d = DiagnosticEau("eau_usee", {"pH": 7.5, "mes": 250, "dco": 500, "dbo5": 250,
                                   "ntk": 50, "phosphore_total": 12})
    assert params(d.analyser_conformite()) == {"mes", "dco", "dbo5", "ntk", "phosphore_total"}


def test_eau_conforme():
    d = DiagnosticEau("eau_souterraine", {"pH": 7.2, "nitrates": 10, "fer": 0.1, "manganese": 0.02})
    assert d.analyser_conformite() == []


def test_norme_benin_plus_stricte_sur_nitrates():
    valeurs = {"nitrates": 48}
    assert DiagnosticEau("eau_souterraine", valeurs, "OMS_2011").analyser_conformite() == []
    assert params(DiagnosticEau("eau_souterraine", valeurs, "BENIN_2001_094").analyser_conformite()) == {"nitrates"}


def test_ph_hors_plage_ecart_par_rapport_a_la_borne():
    nc = DiagnosticEau("eau_atmospherique", {"pH": 5.5}).analyser_conformite()
    assert nc[0]["parametre"] == "pH"
    assert nc[0]["ecart"] == pytest.approx(-1.0)


def test_nature_de_la_norme_indiquee():
    nc = DiagnosticEau("eau_souterraine", {"fer": 1.0, "nitrates": 60}).analyser_conformite()
    natures = {n["parametre"]: n["nature"] for n in nc}
    assert natures == {"fer": "acceptabilite", "nitrates": "sanitaire"}


# -------------------------------------------------- équilibre calcocarbonique

def test_constantes_a_25_degres():
    assert pk2_carbonique(25) == pytest.approx(10.33, abs=0.01)
    assert pks_calcite(25) == pytest.approx(8.48, abs=0.01)


def test_phs_coherent_avec_formule_simplifiee_de_carrier():
    """La formule pratique pHs = (9,3 + A + B) − (C + D) doit donner un résultat voisin."""
    ca, tac, t, tds = 150, 120, 25, 300
    a = (math.log10(tds) - 1) / 10
    b = -13.12 * math.log10(t + 273) + 34.55
    c = math.log10(ca) - 0.4
    d = math.log10(tac)
    phs_carrier = 9.3 + a + b - (c + d)
    assert ph_saturation(ca, tac, t, tds) == pytest.approx(phs_carrier, abs=0.25)


def test_langelier_ordre_de_grandeur_realiste():
    """Ancien bug : Is ≈ +6 pour toute eau. Une eau courante doit être proche de 0."""
    d = DiagnosticEau("eau_surface", {"pH": 7.2, "temperature": 25, "alcalinite": 120,
                                      "durete_totale": 150, "durete_calcique": 80,
                                      "conductivite": 300})
    assert -1.5 < d.calculer_indice_langelier() < 0.5


def test_langelier_signe():
    commun = {"temperature": 20, "alcalinite": 200, "durete_calcique": 200, "conductivite": 600}
    assert DiagnosticEau("eau_souterraine", {**commun, "pH": 6.5}).calculer_indice_langelier() < -0.5
    assert DiagnosticEau("eau_souterraine", {**commun, "pH": 8.2}).calculer_indice_langelier() > 0.5


def test_langelier_temperature_augmente_l_indice():
    base = {"pH": 7.5, "alcalinite": 150, "durete_calcique": 150, "conductivite": 500}
    froid = DiagnosticEau("eau_souterraine", {**base, "temperature": 10}).calculer_indice_langelier()
    chaud = DiagnosticEau("eau_souterraine", {**base, "temperature": 40}).calculer_indice_langelier()
    assert chaud > froid


def test_langelier_hypotheses_signalees():
    details = DiagnosticEau("eau_souterraine", {"pH": 7, "alcalinite": 100,
                                                "durete_totale": 150}).details_langelier()
    assert len(details["hypotheses"]) == 3  # TDS, calcium, température


def test_langelier_donnees_insuffisantes():
    assert DiagnosticEau("eau_atmospherique", {"pH": 6}).calculer_indice_langelier() is None


def test_dose_de_chaux_ramene_a_l_equilibre():
    valeurs = {"pH": 6.3, "temperature": 25, "conductivite": 150, "alcalinite": 40,
               "durete_calcique": 35}
    resultat = DiagnosticEau("eau_souterraine", valeurs).corriger_agressivite()
    # Contrôle indépendant : on applique la dose et on recalcule Is
    x = resultat["co2_neutralise_mgL"] / 44.01  # mmol/L
    eau_traitee = {**valeurs,
                   "alcalinite": valeurs["alcalinite"] + x * 50.04,
                   "durete_calcique": valeurs["durete_calcique"] + x / 2 * 100.09}
    assert 0 < resultat["co2_neutralise_mgL"] < resultat["co2_libre_mgL"]
    assert resultat["dose_chaux_mgL"] == pytest.approx(x / 2 * 74.09, abs=0.1)
    # pH après traitement calculé par l'équilibre CO₂/HCO₃⁻, Is ≈ 0
    from diagnostic import log_gamma_davies, pk1_carbonique
    g1 = 10 ** log_gamma_davies(1, 0.65 * 150)
    hco3 = eau_traitee["alcalinite"] / 50.04
    co2 = resultat["co2_libre_mgL"] / 44.01 - x
    eau_traitee["pH"] = pk1_carbonique(25) + math.log10(g1 * hco3 / co2)
    assert DiagnosticEau("eau_souterraine", eau_traitee).calculer_indice_langelier() == pytest.approx(0, abs=0.05)


def test_pas_de_chaux_pour_eau_incrustante():
    d = DiagnosticEau("eau_souterraine", {"pH": 8.2, "alcalinite": 200, "durete_calcique": 200})
    assert d.corriger_agressivite() is None


# --------------------------------------------------------------- traitements

def etapes(d):
    return [t["etape"] for t in d.determiner_traitements()]


def test_fer_et_manganese_traites_aussi_en_eau_de_surface():
    d = DiagnosticEau("eau_surface", {"pH": 7.2, "fer": 1.0, "manganese": 0.3})
    assert {"deferrisation", "demanganisation"} <= set(etapes(d))


def test_doses_stoechiometriques():
    assert DiagnosticEau("eau_souterraine", {"fer": 10}).traiter_fer()["dose_chlore_mgL"] == 6.3
    assert DiagnosticEau("eau_souterraine", {"manganese": 1}).traiter_manganese()["dose_kmno4_mgL"] == 1.92


def test_adoucissement_chaux_seule_et_chaux_soude():
    seule = DiagnosticEau("eau_souterraine", {"durete_totale": 250, "alcalinite": 200}).traiter_durete()
    assert seule["methode"] == "Chaux seule" and seule["dose_chaux_mgL"] == 74.0
    mixte = DiagnosticEau("eau_souterraine", {"durete_totale": 300, "alcalinite": 100}).traiter_durete()
    assert mixte["methode"] == "Chaux + Soude" and mixte["dose_soude_mgL"] == 212.0


@pytest.mark.parametrize("rapport, code", [(1.8, "facile"), (2.0, "moyenne"),
                                           (2.7, "moyenne"), (3.0, "faible"), (5, "faible")])
def test_classes_de_biodegradabilite(rapport, code):
    assert classer_biodegradabilite(rapport)[0] == code


def test_prescription_et_filiere_eau_usee_coherentes():
    """Ancien bug : seuils 2,5 dans la prescription et 3 dans l'affichage."""
    d = DiagnosticEau("eau_usee", {"dco": 700, "dbo5": 250, "ntk": 20, "phosphore_total": 5})
    assert etapes(d) == ["traitement_biologique"]
    assert any("Lits bactériens" in e for e in d.construire_filiere())


def test_eau_usee_peu_biodegradable():
    d = DiagnosticEau("eau_usee", {"dco": 1000, "dbo5": 200})
    assert etapes(d) == ["pretraitement_physico_chimique"]


def test_dbo5_nulle_sans_erreur():
    d = DiagnosticEau("eau_usee", {"dco": 100, "dbo5": 0})
    d.determiner_traitements()
    d.construire_filiere()


def test_filiere_surface_ordre_nitrates_avant_desinfection():
    filiere = DiagnosticEau("eau_surface", {"nitrates": 80}).construire_filiere()
    i_nitrates = next(i for i, e in enumerate(filiere) if "nitrates" in e)
    i_filtration = next(i for i, e in enumerate(filiere) if "Filtration sur sable" in e)
    assert i_filtration < i_nitrates < len(filiere) - 1
    assert "Désinfection" in filiere[-1]


def test_seuils_suivent_la_norme_choisie():
    valeurs = {"nitrates": 48}
    oms = DiagnosticEau("eau_souterraine", valeurs, "OMS_2011").construire_filiere()
    benin = DiagnosticEau("eau_souterraine", valeurs, "BENIN_2001_094").construire_filiere()
    assert not any("nitrates" in e for e in oms)
    # 48 > 45 (Bénin) mais l'élimination des nitrates suit le seuil sanitaire de la norme
    assert any("nitrates" in e for e in benin)


def test_type_eau_inconnu():
    with pytest.raises(ValueError):
        DiagnosticEau("eau_de_mer", {})


@pytest.mark.parametrize("type_eau", ["eau_surface", "eau_souterraine", "eau_atmospherique", "eau_usee"])
def test_rapport_complet_serialisable(type_eau):
    import json
    rapport = DiagnosticEau(type_eau, {"pH": 7, "dco": 100, "dbo5": 50}).generer_rapport_complet()
    json.dumps(rapport, ensure_ascii=False, default=str)
