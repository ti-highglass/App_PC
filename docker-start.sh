#!/bin/bash

echo "🐳 Iniciando Sistema de Alocação de PC com Docker..."

# Verificar se o Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker não está rodando. Inicie o Docker Desktop primeiro."
    exit 1
fi

# Verificar se o arquivo .env existe
if [ ! -f .env ]; then
    echo "❌ Arquivo .env não encontrado. Crie o arquivo com as variáveis de ambiente."
    exit 1
fi

# Build e start dos containers
echo "🔨 Construindo imagem..."
docker-compose build

echo "🚀 Iniciando containers..."
docker-compose up -d

echo "✅ Sistema iniciado com sucesso!"
echo "🌐 Acesse: http://localhost:9990"
echo ""
echo "📋 Comandos úteis:"
echo "  docker-compose logs -f    # Ver logs em tempo real"
echo "  docker-compose stop       # Parar containers"
echo "  docker-compose down       # Parar e remover containers"