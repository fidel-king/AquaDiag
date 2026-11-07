"""Tests : bactériologie, chloration, norme personnalisée, rapport PDF."""

import pytest

from diagnostic import (
    DiagnosticEau,
    classer_risque_ecoli,
    dimensionner_chloration,
    pka_hypochloreux,
    valider_norme,
)
from rapport_pdf import generer_pdf, texte_pdf

# ------------------------------------------------------------ bactériologie


@pytest.mark.parametrize("ufc, code", [(0, "conforme"), (1, "faible"), (10, "faible"),
                                       (11, "intermediaire"), (100, "intermediaire"),
                                       (101, "eleve"), (1000, "eleve"), (1001, "tres_eleve")])
def test_classes_de_risque_ecoli(ufc, code):
    assert classer_risque_ecoli(ufc)[0] == code


def test_sans_analyse_bacterio_pas_de_conclusion():
    d = DiagnosticEau("eau_souterraine", {"pH": 7.2})
    assert d.analyse_bacteriologique() is None
    assert "desinfection" not in [t["etape"] for t in d.determiner_traitements()]


def test_ecoli_non_conforme_et_desinfection_prescrite():
    d = DiagnosticEau("eau_souterraine", {"pH": 7.2, "e_coli": 25})
    assert "e_coli" in {nc["parametre"] for nc in d.analyser_conformite()}
    traitements = {t["etape"]: t for t in d.determiner_traitements()}
    assert "Risque intermédiaire" in traitements["desinfection"]["detail"]
    assert "forage" in traitements["desinfection"]["detail"]


def test_eau_saine_aucune_desinfection_specifique():
    d = DiagnosticEau("eau_souterraine", {"pH": 7.2, "e_coli": 0, "coliformes_totaux": 0})
    assert d.analyse_bacteriologique()["classe_risque"] == "conforme"
    assert d.determiner_traitements() == []


def test_coliformes_totaux_sans_indicateur_fecal():
    d = DiagnosticEau("eau_surface", {"e_coli": 0, "coliformes_totaux": 12})
    desinfection = [t for t in d.determiner_traitements() if t["etape"] == "desinfection"]
    assert "sans indicateur fécal" in desinfection[0]["detail"]


def test_turbidite_signalee_avant_desinfection():
    d = DiagnosticEau("eau_surface", {"e_coli": 5, "turbidite": 8})
    desinfection = [t for t in d.determiner_traitements() if t["etape"] == "desinfection"]
    assert "clarifier" in desinfection[0]["detail"]


def test_eau_usee_coliformes_fecaux():
    d = DiagnosticEau("eau_usee", {"dco": 120, "dbo5": 60, "coliformes_fecaux": 1e5})
    assert "desinfection_rejet" in [t["etape"] for t in d.determiner_traitements()]
    assert "obligatoire" in d.construire_filiere()[-1]


# --------------------------------------------------------------- chloration

def test_pka_hypochloreux():
    assert pka_hypochloreux(25) == pytest.approx(7.54, abs=0.01)
    assert pka_hypochloreux(20) > pka_hypochloreux(25)


def test_chloration_cas_de_reference():
    """1000 m³/j, demande 1 mg/L, résiduel 0,5 mg/L, chicanage 0,3."""
    r = dimensionner_chloration(1000, 1.0, 0.5, ph=7.0, temperature=25, facteur_chicanage=0.3)
    assert r["dose_mgL"] == 1.5
    assert r["chlore_actif_kg_j"] == 1.5
    assert r["hth_kg_j"] == pytest.approx(1.5 / 0.65, abs=0.001)
    assert r["javel_L_j"] == pytest.approx(1500 / (12 * 3.17), abs=0.1)
    assert r["t10_min"] == 30.0 and r["temps_sejour_min"] == 100.0
    assert r["volume_contact_m3"] == pytest.approx(1000 / 1440 * 100, abs=0.1)
    assert 0.7 < r["fraction_hocl"] < 0.85
    assert r["avertissements"] == []


def test_chloration_ph_eleve_et_residuel_faible():
    r = dimensionner_chloration(100, 0.5, 0.3, ph=8.5)
    assert r["fraction_hocl"] < 0.15
    assert len(r["avertissements"]) == 2


def test_meilleur_chicanage_reduit_le_bassin():
    mauvais = dimensionner_chloration(500, 1, 0.5, facteur_chicanage=0.1)
    bon = dimensionner_chloration(500, 1, 0.5, facteur_chicanage=0.7)
    assert bon["volume_contact_m3"] < mauvais["volume_contact_m3"]


@pytest.mark.parametrize("arguments", [(0, 1, 0.5), (100, 1, 0), (100, 1, 0.5, 7, 25, 1.5)])
def test_chloration_entrees_invalides(arguments):
    with pytest.raises(ValueError):
        dimensionner_chloration(*arguments)


# --------------------------------------------------------- norme personnalisée

NORME_TEST = {
    "nom": "Norme test",
    "parametres": {
        "nitrates": {"limite": 40, "nature": "sanitaire"},
        "pH": {"min": 6.0, "max": 9.0},
        "e_coli": {"limite": "0"},
    },
}


def test_valider_norme_normalise():
    norme = valider_norme(NORME_TEST)
    assert norme["parametres"]["e_coli"] == {"limite": 0.0, "nature": "reglementaire"}
    assert norme["parametres"]["pH"]["min"] == 6.0


@pytest.mark.parametrize("norme, message", [
    ({"parametres": {"inconnu": {"limite": 1}}}, "inconnu"),
    ({"parametres": {"fer": {"limite": "abc"}}}, "pas un nombre"),
    ({"parametres": {"pH": {"min": 9, "max": 6}}}, "minimum"),
    ({"parametres": {"fer": {}}}, "indiquer"),
    ({"parametres": {"fer": {"limite": 1, "nature": "autre"}}}, "nature"),
    ({"parametres": {}}, "aucun"),
    ({"nom": "x"}, "parametres"),
])
def test_valider_norme_erreurs(norme, message):
    with pytest.raises(ValueError, match=message):
        valider_norme(norme)


def test_diagnostic_avec_norme_personnalisee():
    d = DiagnosticEau("eau_souterraine", {"pH": 8.7, "nitrates": 45, "fer": 2}, NORME_TEST)
    assert d.referentiel()["nom"] == "Norme test"
    # pH 8,7 conforme ici (6-9), nitrates 45 > 40 ; le fer n'est pas dans cette norme
    assert {nc["parametre"] for nc in d.analyser_conformite()} == {"nitrates"}
    assert any("nitrates" in e for e in d.construire_filiere())


def test_norme_personnalisee_pour_eau_usee():
    norme = {"nom": "Rejet local", "parametres": {"dbo5": {"limite": 50}}}
    d = DiagnosticEau("eau_usee", {"dbo5": 40, "dco": 90}, norme)
    assert d.analyser_conformite() == []


# --------------------------------------------------------------------- PDF

def test_texte_pdf_nettoie_les_caracteres():
    assert texte_pdf("🧴 Ca(OH)₂ ≤ 5 m³ <b>") == "Ca(OH)2 &lt;= 5 m3 &lt;b&gt;"


@pytest.mark.parametrize("type_eau, valeurs", [
    ("eau_surface", {"pH": 6.4, "temperature": 25, "turbidite": 15, "alcalinite": 40,
                     "durete_calcique": 35, "fer": 0.5, "manganese": 0.3, "e_coli": 25}),
    ("eau_souterraine", {"pH": 7.0, "durete_totale": 300, "alcalinite": 100, "fluorures": 2}),
    ("eau_atmospherique", {"pH": 5.5}),
    ("eau_usee", {"dco": 500, "dbo5": 250, "ntk": 50, "phosphore_total": 12}),
])
def test_pdf_genere(type_eau, valeurs):
    rapport = DiagnosticEau(type_eau, valeurs).generer_rapport_complet()
    chloration = dimensionner_chloration(500, 1, 0.5) if type_eau != "eau_usee" else None
    pdf = generer_pdf(rapport, chloration, "Test")
    assert pdf.startswith(b"%PDF") and len(pdf) > 2000
