"""Tests de fumée de l'interface Streamlit (sans navigateur)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "application.py")


def lancer(type_eau=None):
    at = AppTest.from_file(APP, default_timeout=30).run()
    if type_eau:
        at.sidebar.selectbox[0].select(type_eau).run()
    return at


def textes(at):
    return " ".join(m.value for m in at.markdown) + " ".join(m.value for m in at.subheader)


@pytest.mark.parametrize("type_eau", ["eau_surface", "eau_souterraine", "eau_atmospherique", "eau_usee"])
def test_diagnostic_sans_erreur(type_eau):
    at = lancer(type_eau)
    at.button[0].click().run()
    assert not at.exception
    assert "RÉSULTATS DU DIAGNOSTIC" in textes(at)


def test_eau_usee_par_defaut_non_conforme():
    at = lancer("eau_usee")
    at.button[0].click().run()
    assert "Paramètres non conformes" in textes(at)


def test_resultats_conserves_apres_une_autre_interaction():
    """Ancien bug : un nouveau rerun (ex. clic sur Télécharger) effaçait les résultats."""
    at = lancer()
    at.button[0].click().run()
    at.run()  # rerun sans clic sur le bouton de diagnostic
    assert "RÉSULTATS DU DIAGNOSTIC" in textes(at)


def test_avertissement_si_parametres_modifies():
    at = lancer()
    at.button[0].click().run()
    at.number_input(key="eau_surface_nitrates").set_value(90).run()
    assert any("ont changé" in w.value for w in at.warning)


def test_bacteriologie_et_chloration():
    at = lancer("eau_souterraine")
    at.checkbox(key="bacterio_eau_souterraine").check().run()
    at.number_input(key="eau_souterraine_e_coli").set_value(250).run()
    at.button[0].click().run()
    assert not at.exception
    assert any("Risque élevé" in e.value for e in at.error)
    assert "Dimensionnement de la chloration" in textes(at)
    # La chloration se recalcule sans relancer le diagnostic
    at.number_input(key="chl_debit").set_value(2000).run()
    assert "RÉSULTATS DU DIAGNOSTIC" in textes(at)
    assert any(m.label == "Bassin de contact" for m in at.metric)


def test_norme_personnalisee_dans_l_interface():
    at = lancer("eau_souterraine")
    at.sidebar.selectbox(key="norme_potable").select("PERSONNALISEE").run()
    assert not at.exception
    assert not at.error  # le modèle (OMS) est une norme valide
    at.button[0].click().run()
    assert "Norme personnalisée" in " ".join(c.value for c in at.caption)


def test_colonne_unites_lisible():
    at = lancer()
    at.button[0].click().run()
    df = at.dataframe[0].value
    assert "NTU" in set(df["Unité"])
    assert not any("method" in str(u) for u in df["Unité"])
