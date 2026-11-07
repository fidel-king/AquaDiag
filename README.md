# 💧 AquaDiag

Assistant de diagnostic et de prescription de traitement des eaux, développé dans le cadre du Master Ecohydrologie (INE/UAC).

À partir des paramètres d'une eau brute, AquaDiag :

- compare les valeurs à une norme (OMS 2011, Décret béninois 2001-094, normes de rejet pour les eaux usées, ou **norme personnalisée**) en distinguant valeurs **sanitaires**, seuils d'**acceptabilité** et valeurs **réglementaires** ;
- évalue la **qualité bactériologique** (classe de risque OMS selon E. coli) et prescrit la désinfection ;
- calcule l'**équilibre calcocarbonique** (pH de saturation et indice de Langelier) et, pour une eau agressive, la **dose de chaux** qui la ramène à l'équilibre ;
- propose les traitements spécifiques (coagulation, déferrisation, démanganisation, adoucissement, défluoruration, traitement biologique, azote, phosphore…) avec les doses de réactifs ;
- construit la **filière de traitement** complète ;
- **dimensionne la chloration** : dose, consommation d'hypochlorite de calcium et d'eau de Javel, part de HOCl, volume du bassin de contact ;
- exporte un rapport **PDF**, texte ou JSON.

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
| `rapport_pdf.py` | Rapport PDF (reportlab). |
| `tests/` | Tests du moteur et de l'interface. |

## Méthodes de calcul

**pH de saturation** — `pHs = pK2 − pKs + pCa + pHCO3`, avec pK2 et pKs fonction de la température (Harned et Scholes ; Plummer et Busenberg 1982) et coefficients d'activité de Davies. La force ionique est estimée par `I ≈ 2,5·10⁻⁵ × TDS`, et `TDS ≈ 0,65 × conductivité`. L'alcalinité est supposée bicarbonatée (pH < 8,3). Les hypothèses utilisées (TDS, calcium, température par défaut) sont affichées avec le résultat.

**Dose de chaux (eau agressive)** — le CO₂ libre est déduit du pH et du TAC (pK1 de Harned et Davis). On cherche la quantité de CO₂ à neutraliser par `Ca(OH)₂ + 2 CO₂ → Ca(HCO₃)₂` pour que le pH atteigne le nouveau pHs.

**Norme personnalisée** — choisir « Norme personnalisée » dans la barre latérale, modifier le tableau (limite maximale, ou minimum et maximum), puis l'exporter en JSON. Le fichier peut être réimporté plus tard : c'est ainsi qu'on enregistre une norme nationale (par exemple la norme guinéenne) une fois pour toutes. Format :

```json
{"nom": "Ma norme", "parametres": {"nitrates": {"limite": 50, "nature": "sanitaire"}, "pH": {"min": 6.5, "max": 8.5}}}
```

**Bactériologie** — classes de risque selon E. coli (UFC/100 mL) : 0 conforme ; 1-10 faible ; 11-100 intermédiaire ; 101-1000 élevé ; > 1000 très élevé.

**Chloration** — dose = demande en chlore (à mesurer) + résiduel visé. Le critère retenu est celui de l'OMS : chlore libre ≥ 0,5 mg/L après 30 min de contact à pH < 8, soit CT = 15 mg·min/L. Temps de séjour = CT / (résiduel × T10/T), avec T10/T le facteur de chicanage du bassin. La part de HOCl est calculée avec le pKa de Morris (7,54 à 25 °C). Eau de Javel : 1 degré chlorométrique = 3,17 g de chlore actif par litre.

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
