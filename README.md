# 💧 AquaDiag

Assistant de diagnostic et de prescription de traitement des eaux, développé dans le cadre du Master Ecohydrologie (INE/UAC).

À partir des paramètres d'une eau brute, AquaDiag :

- compare les valeurs à une norme (OMS 2011, Décret béninois 2001-094, ou normes de rejet pour les eaux usées) en distinguant valeurs **sanitaires**, seuils d'**acceptabilité** et valeurs **réglementaires** ;
- calcule l'**équilibre calcocarbonique** (pH de saturation et indice de Langelier) et, pour une eau agressive, la **dose de chaux** qui la ramène à l'équilibre ;
- propose les traitements spécifiques (coagulation, déferrisation, démanganisation, adoucissement, défluoruration, traitement biologique, azote, phosphore…) avec les doses de réactifs ;
- construit la **filière de traitement** complète ;
- exporte un rapport (JSON ou texte).

Quatre types d'eau sont pris en charge : eau de surface, eau souterraine, eau atmosphérique et eau usée.

## Installation et lancement

Python 3.9 ou plus récent.

```bash
pip install -r requirements.txt
streamlit run application.py
```

Sous Windows, double-cliquer sur `run.bat` fait les deux étapes.

## Structure

| Fichier | Rôle |
|---|---|
| `diagnostic.py` | Moteur de calcul : normes, chimie des carbonates, prescription. Indépendant de Streamlit. |
| `application.py` | Interface Streamlit. |
| `tests/` | Tests du moteur et de l'interface. |

## Méthodes de calcul

**pH de saturation** — `pHs = pK2 − pKs + pCa + pHCO3`, avec pK2 et pKs fonction de la température (Harned et Scholes ; Plummer et Busenberg 1982) et coefficients d'activité de Davies. La force ionique est estimée par `I ≈ 2,5·10⁻⁵ × TDS`, et `TDS ≈ 0,65 × conductivité`. L'alcalinité est supposée bicarbonatée (pH < 8,3). Les hypothèses utilisées (TDS, calcium, température par défaut) sont affichées avec le résultat.

**Dose de chaux (eau agressive)** — le CO₂ libre est déduit du pH et du TAC (pK1 de Harned et Davis). On cherche la quantité de CO₂ à neutraliser par `Ca(OH)₂ + 2 CO₂ → Ca(HCO₃)₂` pour que le pH atteigne le nouveau pHs.

**Biodégradabilité** — rapport DCO/DBO5 : < 2 facilement biodégradable ; 2 à 3 biodégradable avec biomasse adaptée ; ≥ 3 peu biodégradable.

**Doses stœchiométriques** — 0,63 mg Cl₂/mg Fe ; 1,92 mg KMnO₄/mg Mn ; 0,74 mg Ca(OH)₂ et 1,06 mg Na₂CO₃ par mg CaCO₃ de dureté éliminée ; 0,87 mg Al/mg P.

La dose de coagulant est un ordre de grandeur selon la turbidité et doit être confirmée par jar-test.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Avertissement

Application à usage pédagogique. Les résultats ne remplacent pas l'avis d'un ingénieur ni les analyses de laboratoire et essais de traitabilité.
