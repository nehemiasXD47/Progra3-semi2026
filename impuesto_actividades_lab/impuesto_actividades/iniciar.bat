@echo off
REM Instala el driver de MariaDB (solo la primera vez) y arranca el proyecto
pip install pymysql
python main.py
pause
