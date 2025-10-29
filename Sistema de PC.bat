@echo off
echo Iniciando Sistema de Alocação de PC...
echo.

cd /d "%~dp0"

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python não encontrado!
    echo Instale Python 3.7+ antes de continuar.
    pause
    exit /b 1
)

REM Verificar se arquivo .env existe
if not exist ".env" (
    echo ERRO: Arquivo .env não encontrado!
    echo Configure as variáveis de ambiente do banco de dados.
    pause
    exit /b 1
)

REM Instalar dependências se requirements.txt existir
if exist "requirements.txt" (
    echo Verificando dependências...
    pip install -r requirements.txt --quiet
)

REM Configurar variáveis de ambiente
set FLASK_APP=app.py
set FLASK_ENV=production
set PYTHONPATH=%~dp0

echo Sistema iniciando na porta 5001...
echo Acesse: http://localhost:5001
echo.
echo Pressione Ctrl+C para parar o servidor
echo.

REM Iniciar aplicação
python app.py

echo.
echo Sistema encerrado.
pause