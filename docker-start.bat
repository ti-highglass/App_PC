@echo off
echo 🐳 Iniciando Sistema de Alocação de PC com Docker...

REM Verificar se o Docker está rodando
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker não está rodando. Inicie o Docker Desktop primeiro.
    pause
    exit /b 1
)

REM Verificar se o arquivo .env existe
if not exist .env (
    echo ❌ Arquivo .env não encontrado. Crie o arquivo com as variáveis de ambiente.
    pause
    exit /b 1
)

REM Build e start dos containers
echo 🔨 Construindo imagem...
docker-compose build

echo 🚀 Iniciando containers...
docker-compose up -d

echo ✅ Sistema iniciado com sucesso!
echo 🌐 Acesse: http://localhost:9990
echo.
echo 📋 Comandos úteis:
echo   docker-compose logs -f    # Ver logs em tempo real
echo   docker-compose stop       # Parar containers
echo   docker-compose down       # Parar e remover containers
pause