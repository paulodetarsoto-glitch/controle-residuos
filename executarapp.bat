@echo off
echo Instalando dependencias do projeto...
pip install -r requirements.txt
streamlit run app.py
pause