# Fix: Dashboard não iniciava no Container Linux

## Problema Identificado
O dashboard_app.py não estava sendo iniciado automaticamente no container Linux porque:

1. O Dockerfile usava apenas Gunicorn para executar o `app.py`
2. A lógica de subprocess para iniciar o dashboard só funcionava em execução local
3. Não havia exposição da porta 5002 no container

## Solução Implementada

### 1. Script de Inicialização (`start.sh`)
- Criado script bash que inicia ambos os serviços
- Dashboard na porta 5002 em background
- App principal na porta 5001 com Gunicorn
- Gerenciamento adequado de processos e cleanup

### 2. Dockerfile Atualizado
- Exposição das portas 5001 e 5002
- Uso do script `start.sh` como CMD
- Permissões executáveis para o script

### 3. Docker Compose Atualizado
- Mapeamento de ambas as portas
- Variáveis de ambiente para Gunicorn
- Configuração adequada para produção

### 4. App.py Modificado
- Detecção de ambiente (container vs local)
- Lógica condicional para inicialização do dashboard
- Evita conflitos entre execução local e container

## Como Usar

### Build e Execução
```bash
# Build da imagem
docker-compose build

# Execução
docker-compose up -d

# Verificar logs
docker-compose logs -f
```

### Portas Expostas
- **5001**: Sistema principal
- **5002**: Dashboard de produção

### Verificação
```bash
# Verificar se ambos os serviços estão rodando
curl http://localhost:5001  # Sistema principal
curl http://localhost:5002  # Dashboard

# Verificar processos no container
docker exec app-pc ps aux
```

## Arquivos Modificados
- `start.sh` (novo)
- `Dockerfile`
- `docker-compose.yml`
- `app.py`
- `.dockerignore` (novo)

## Compatibilidade
- ✅ Execução local (Windows/Linux) - mantida
- ✅ Execução em container Linux - corrigida
- ✅ Dashboard independente - funcionando
- ✅ Variáveis de ambiente - configuradas