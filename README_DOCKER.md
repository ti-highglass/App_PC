# Docker Setup - Sistema de Alocação de PC

## Pré-requisitos

### Windows com WSL2
1. **Docker Desktop** instalado e rodando
2. **WSL2** habilitado
3. **Git** instalado

### Verificar instalação
```bash
# Verificar Docker
docker --version
docker-compose --version

# Verificar WSL2
wsl --list --verbose
```

## Configuração

### 1. Arquivo .env
Crie o arquivo `.env` na raiz do projeto:
```env
DB_HOST=seu_host_postgresql
DB_USER=seu_usuario
DB_PSW=sua_senha
DB_PORT=5432
DB_NAME=nome_do_banco
```

### 2. Iniciar o sistema

#### No Windows:
```cmd
docker-start.bat
```

#### No WSL2/Linux:
```bash
chmod +x docker-start.sh
./docker-start.sh
```

#### Manual:
```bash
# Build da imagem
docker-compose build

# Iniciar containers
docker-compose up -d

# Ver logs
docker-compose logs -f
```

## Comandos Úteis

```bash
# Parar containers
docker-compose stop

# Parar e remover containers
docker-compose down

# Rebuild completo
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Acessar container
docker-compose exec app bash

# Ver logs em tempo real
docker-compose logs -f app
```

## Acesso

- **URL**: http://localhost:9990
- **Porta**: 9990 (mapeada do container)

## Estrutura Docker

```
├── Dockerfile              # Imagem da aplicação
├── docker-compose.yml      # Orquestração
├── .dockerignore           # Arquivos ignorados
├── docker-start.sh         # Script Linux/WSL
├── docker-start.bat        # Script Windows
└── README_DOCKER.md        # Esta documentação
```

## Troubleshooting

### Container não inicia
```bash
# Verificar logs
docker-compose logs app

# Verificar se a porta está livre
netstat -an | findstr :9990
```

### Problemas de conexão com banco
- Verificar variáveis no `.env`
- Confirmar conectividade com o PostgreSQL
- Verificar firewall/rede

### Rebuild necessário
```bash
# Após mudanças no código
docker-compose down
docker-compose build
docker-compose up -d
```