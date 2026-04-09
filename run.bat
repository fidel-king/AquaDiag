@echo off
echo ========================================
echo   AquaDiag - Diagnostic des Eaux
echo ========================================
echo.
echo Installation des dépendances...
pip install -r requirements.txt
echo.
echo Lancement de l'application...
streamlit run application.py
pause