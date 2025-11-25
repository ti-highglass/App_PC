# Sistema de Alocação de PC

## Descrição

Sistema web desenvolvido em Flask para gerenciamento completo de alocação de peças de PC (Policarbonato) automotivas da Opera. O sistema oferece controle total do fluxo desde a coleta de dados até o armazenamento final no estoque, com funcionalidades avançadas de otimização, rastreamento e relatórios.

## 🚀 Versão Atual: 2.2 SSO

**Principais atualizações:**
- ✅ **SSO (Single Sign-On)** - Integração com sistema de Acompanhamento de Corte
- ✅ **Dashboard de Produção** - Monitoramento em tempo real (porta 5002)
- ✅ **Sistema de Slots** - 169 slots organizados por tipo de peça
- ✅ **Gestão de Baixas** - Controle de peças com defeito/problemas
- ✅ **Arquivos de Corte** - Gerenciamento de arquivos PC por projeto/peça
- ✅ **Sistema de Etiquetas** - Geração de etiquetas com códigos de barras
- ✅ **Docker Support** - Containerização completa
- ✅ **Entrada Manual** - Adição manual de peças ao estoque
- ✅ **Integração com Plano de Controle** - Nova fonte de dados
- ✅ **Sistema de Lotes** - Controle por lotes VD/PC

## Funcionalidades Principais

### 🔐 Sistema de Autenticação
- ✅ Login seguro com hash de senhas (pbkdf2:sha256)
- ✅ Controle de acesso por setor (Produção, Administrativo, T.I)
- ✅ Gerenciamento de usuários (apenas T.I)
- ✅ Diferentes níveis de permissão
- ✅ **SSO Integration** - Login único com sistema de Corte PC
- ✅ **Session Management** - Sessões persistentes (365 dias)

### 📊 Coleta e Otimização de Dados
- ✅ Coleta automática de dados da tabela **plano_controle_corte_vidro2**
- ✅ Filtros por lote para coleta específica
- ✅ Algoritmo inteligente de sugestão de **SLOTS** (1-169)
- ✅ Workflow de otimização com validação de capacidade
- ✅ Prevenção de duplicatas no sistema
- ✅ **Importação Excel** - Upload de planilhas com peças
- ✅ **Entrada Manual** - Adição individual de peças

### 🏭 Gestão de Estoque
- ✅ Controle completo de inventário com **camadas L3/L3_B**
- ✅ Rastreamento de movimentações por usuário
- ✅ Histórico de saídas com auditoria completa
- ✅ **169 Slots** organizados por tipo de peça
- ✅ Operações em lote (seleção múltipla)
- ✅ Contador dinâmico de peças em estoque
- ✅ **Sistema de Baixas** - Controle de peças com problemas
- ✅ **Reprocessamento** - Retorno de baixas para produção

### 📍 Gerenciamento de Locais
- ✅ **Sistema de SLOTS** (SLOT 1 até SLOT 169)
- ✅ Algoritmo de alocação por tipo de peça:
  - **SLOTS 1-4**: Peças tamanho "GG" exclusivas
  - **SLOTS 4-40, 81-117**: TSP, TSA, TSC, TSB, PBS, VGA
  - **SLOTS 41-80, 118-157**: PDE, PDD, PTE, PTD, TME, TMD
  - **SLOTS 158-169**: QTE, QTD, QDD, QDE, FTE, FTD, FDD, FDE
- ✅ Monitoramento de ocupação em tempo real
- ✅ Validação de capacidade (limite configurável por slot)
- ✅ Visualização de peças armazenadas por local
- ✅ Contadores de peças por local com badges visuais

### 📈 Relatórios e Exportação
- ✅ **Geração de XMLs** com base em arquivos de corte
- ✅ **Salvamento automático** em pastas do SharePoint
- ✅ Exportação Excel de todos os módulos
- ✅ Relatórios de estoque, saídas, baixas e logs
- ✅ **Sistema de Etiquetas** - PDF com códigos de barras
- ✅ Filtros e busca avançada

### 🔍 Sistema de Logs e Auditoria
- ✅ Rastreamento completo de ações dos usuários
- ✅ Logs detalhados com timestamp
- ✅ Busca e filtros nos logs (apenas T.I)
- ✅ Exportação de relatórios de auditoria

### 🎨 Interface e Experiência
- ✅ Design responsivo e moderno
- ✅ **Dashboard de Produção** - Monitoramento em tempo real
- ✅ Tabelas com ordenação por colunas
- ✅ Paginação inteligente
- ✅ Modais para operações críticas
- ✅ Proteção contra inspeção de código
- ✅ Animações e transições suaves
- ✅ Contadores visuais dinâmicos
- ✅ **SSO Links** - Navegação integrada entre sistemas
- ✅ Badges coloridos para status e contagens

## Tecnologias Utilizadas

- **Backend**: Python 3.x + Flask 2.3.3 + Flask-Login 0.6.3
- **Frontend**: HTML5 + CSS3 + JavaScript (Vanilla)
- **Banco de Dados**: PostgreSQL (Supabase)
- **Autenticação**: Werkzeug Security + SSO (URLSafeTimedSerializer)
- **Exportação**: Pandas 2.0.3 + OpenPyXL 3.1.2
- **PDF/Etiquetas**: ReportLab 4.0.4 + python-barcode 0.15.1
- **Containerização**: Docker + Docker Compose
- **Ícones**: Font Awesome 6.0
- **Estilo**: CSS customizado com design system próprio

## Instalação e Execução

### Método 1: Docker (Recomendado)
```bash
# 1. Configurar variáveis de ambiente (.env)
DB_HOST=seu_host_postgresql
DB_USER=seu_usuario
DB_PSW=sua_senha
DB_PORT=5432
DB_NAME=nome_do_banco
SSO_SHARED_SECRET=chave_secreta_sso
ACOMP_CORTE_BASE_URL=http://url_sistema_corte
ACOMP_CORTE_SSO_LOGOUT_URL=http://url_logout_corte

# 2. Configurar pasta de rede para XMLs (Linux)
# Veja README_NETWORK_SETUP.md para detalhes
sudo mkdir -p /mnt/cnc-policarbonato
sudo mount -t cifs //10.150.16.39/cnc-policarbonato /mnt/cnc-policarbonato -o credentials=/etc/cifs-credentials

# 3. Executar com Docker
docker-compose up -d

# 4. Ou usar script
docker-start.bat
```

### Método 2: Execução Manual
```bash
# 1. Instalar dependências
pip install -r lixo/requirements.txt

# 2. Configurar pasta de rede (Linux)
# Veja README_NETWORK_SETUP.md para configuração completa
chmod +x mount_network.sh
sudo ./mount_network.sh

# 3. Executar aplicação principal
python app.py

# 4. Executar dashboard (opcional)
python dashboard_app.py

# 5. Ou usar script (Windows)
"Sistema de PC.bat"
```

### 3. Acessar no navegador
```
# Sistema Principal
http://localhost:5001

# Dashboard de Produção
http://localhost:5002
```

### 4. Login inicial
- Usuário padrão deve ser criado via T.I
- Setores disponíveis: Produção, Administrativo, T.I
- Funções: user, admin
- **SSO**: Integração automática com sistema de Corte PC

## Estrutura do Projeto

```
Sistema Alocação de PC.2_SSO/
│
├── app.py                    # Aplicação Flask principal (porta 5001)
├── dashboard_app.py          # Dashboard de produção (porta 5002)
├── docker-compose.yml        # Configuração Docker
├── Dockerfile               # Imagem Docker
├── README.md                # Documentação
├── .env                     # Variáveis de ambiente (não versionado)
├── "Sistema de PC.bat"      # Script de inicialização
├── docker-start.bat         # Script Docker
├── README_DOCKER.md         # Documentação Docker
├── README_INSTALACAO.txt    # Guia de instalação
│
├── templates/
│   ├── navbar.html          # Navegação com SSO links
│   ├── login.html           # Tela de login
│   ├── index.html           # Otimização de peças
│   ├── estoque.html         # Gestão de estoque
│   ├── locais.html          # Gerenciamento de slots
│   ├── otimizadas.html      # Peças em processo
│   ├── saidas.html          # Histórico de saídas
│   ├── arquivos.html        # Gestão de arquivos PC
│   ├── baixas.html          # Sistema de baixas
│   ├── register.html        # Gestão de usuários
│   ├── logs.html            # Sistema de logs
│   └── dashboard_standalone.html # Dashboard produção
│
├── static/
│   ├── css/
│   │   ├── style.css        # Estilos principais
│   │   ├── login.css        # Estilos do login
│   │   ├── dashboard.css    # Estilos do dashboard
│   │   └── etiquetas.css    # Estilos das etiquetas
│   ├── js/
│   │   ├── protection.js    # Proteção de código
│   │   ├── index.js         # Lógica da otimização
│   │   ├── estoque.js       # Lógica do estoque
│   │   ├── locais.js        # Lógica dos slots
│   │   ├── otimizadas.js    # Lógica das otimizadas
│   │   ├── saidas.js        # Lógica das saídas
│   │   ├── arquivos.js      # Lógica dos arquivos
│   │   ├── baixas.js        # Lógica das baixas
│   │   ├── register.js      # Lógica dos usuários
│   │   ├── logs.js          # Lógica dos logs
│   │   ├── dashboard_producao.js # Dashboard
│   │   ├── etiquetas.js     # Sistema de etiquetas
│   │   └── session.js       # Gerenciamento de sessão
│   └── img/
│       ├── opera.jpg        # Logo da empresa
│       ├── opera.png        # Logo PNG
│       └── logo_opera 2 (1).png # Logo alternativo
│
├── logs/                    # Diretório de logs
└── lixo/                    # Arquivos de desenvolvimento
    ├── requirements.txt     # Dependências Python
    └── [arquivos de migração e testes]
```

## Estrutura do Banco de Dados

### Tabelas Principais

#### pc_inventory (Estoque Final)
| Campo     | Tipo      | Descrição                 |
|-----------|-----------|---------------------------|
| id        | SERIAL    | Chave primária           |
| op        | TEXT      | Ordem de Produção        |
| peca      | TEXT      | Código da peça           |
| projeto   | TEXT      | Projeto da peça          |
| veiculo   | TEXT      | Modelo do veículo        |
| local     | TEXT      | Slot de armazenamento    |
| sensor    | TEXT      | Sensor da peça           |
| camada    | TEXT      | Camada (L3, L3_B)        |
| lote_vd   | TEXT      | Lote VD original         |
| lote_pc   | TEXT      | Lote PC convertido       |
| data      | TIMESTAMP | Data de entrada          |
| usuario   | TEXT      | Usuário responsável      |

#### pc_otimizadas (Processo Intermediário)
| Campo           | Tipo      | Descrição                 |
|-----------------|-----------|---------------------------|
| id              | SERIAL    | Chave primária           |
| op              | TEXT      | Ordem de Produção        |
| peca            | TEXT      | Código da peça           |
| projeto         | TEXT      | Projeto da peça          |
| veiculo         | TEXT      | Modelo do veículo        |
| local           | TEXT      | Slot sugerido            |
| sensor          | TEXT      | Sensor da peça           |
| camada          | TEXT      | Camada (L3, L3_B)        |
| lote_vd         | TEXT      | Lote VD original         |
| lote_pc         | TEXT      | Lote PC convertido       |
| cortada         | BOOLEAN   | Status de corte          |
| user_otimizacao | TEXT      | Usuário responsável      |
| data_otimizacao | TIMESTAMP | Data da otimização       |
| tipo            | TEXT      | Tipo (PC)                |

#### pc_locais (Gestão de Slots)
| Campo  | Tipo   | Descrição              |
|--------|--------|------------------------|
| id     | SERIAL | Chave primária        |
| local  | TEXT   | Código do slot        |
| status | TEXT   | Ativo ou Utilizando   |
| limite | TEXT   | Capacidade do slot    |

#### pc_exit (Histórico de Saídas)
| Campo   | Tipo      | Descrição              |
|---------|-----------|------------------------|
| id      | SERIAL    | Chave primária        |
| op      | TEXT      | Ordem de Produção     |
| peca    | TEXT      | Código da peça        |
| projeto | TEXT      | Projeto da peça       |
| veiculo | TEXT      | Modelo do veículo     |
| local   | TEXT      | Slot de origem        |
| sensor  | TEXT      | Sensor da peça        |
| lote_vd | TEXT      | Lote VD original      |
| lote_pc | TEXT      | Lote PC convertido    |
| usuario | TEXT      | Usuário responsável   |
| data    | TIMESTAMP | Data da saída         |
| motivo  | TEXT      | Motivo da saída       |

#### users (Controle de Usuários)
| Campo   | Tipo   | Descrição                    |
|---------|--------|------------------------------|
| id      | SERIAL | Chave primária              |
| usuario | TEXT   | Nome do usuário             |
| senha   | TEXT   | Hash da senha (pbkdf2)      |
| funcao  | TEXT   | user ou admin               |
| setor   | TEXT   | Produção/Administrativo/T.I |
| sistema | TEXT   | Sistema (PC)                |
| email   | TEXT   | Email do usuário            |

#### pc_logs (Sistema de Auditoria)
| Campo     | Tipo      | Descrição              |
|-----------|-----------|------------------------|
| id        | SERIAL    | Chave primária        |
| usuario   | TEXT      | Usuário da ação       |
| acao      | TEXT      | Tipo de ação          |
| detalhes  | TEXT      | Detalhes da ação      |
| data_acao | TIMESTAMP | Timestamp da ação     |

#### pc_baixas (Sistema de Baixas)
| Campo               | Tipo      | Descrição              |
|---------------------|-----------|------------------------|
| id                  | SERIAL    | Chave primária        |
| op                  | TEXT      | Ordem de Produção     |
| peca                | TEXT      | Código da peça        |
| projeto             | TEXT      | Projeto da peça       |
| veiculo             | TEXT      | Modelo do veículo     |
| sensor              | TEXT      | Sensor da peça        |
| motivo_baixa        | TEXT      | Motivo da baixa       |
| data_baixa          | DATE      | Data da baixa         |
| status              | TEXT      | Status (PENDENTE/PROCESSADO) |
| usuario_apontamento | TEXT      | Usuário que fez baixa |
| processado_por      | TEXT      | Usuário que processou |
| data_processamento  | TIMESTAMP | Data do processamento |
| data_criacao        | TIMESTAMP | Data de criação       |

#### arquivos_pc (Arquivos de Corte)
| Campo      | Tipo    | Descrição              |
|------------|---------|------------------------|
| id         | SERIAL  | Chave primária        |
| projeto    | TEXT    | Projeto da peça       |
| peca       | TEXT    | Código da peça        |
| nome_peca  | TEXT    | Nome do arquivo       |
| camada     | TEXT    | Camada (L3, L3_B)     |
| espessura  | DECIMAL | Espessura do material |
| quantidade | INTEGER | Quantidade            |
| sensor     | TEXT    | Sensor da peça        |

#### pc_camadas (Controle de Camadas)
| Campo   | Tipo | Descrição              |
|---------|------|------------------------|
| id      | SERIAL | Chave primária        |
| projeto | TEXT | Projeto da peça       |
| peca    | TEXT | Código da peça        |
| l3      | TEXT | Camada L3             |
| l3_b    | TEXT | Camada L3_B           |

### Tabelas de Origem (Somente Leitura)

#### plano_controle_corte_vidro2 (Principal)
| Campo              | Tipo | Descrição                    |
|--------------------|------|------------------------------|
| op                 | TEXT | Ordem de Produção           |
| peca               | TEXT | Código da peça              |
| projeto            | TEXT | Projeto                     |
| sensor             | TEXT | Sensor da peça              |
| id_lote            | TEXT | Lote VD                     |
| tipo_programacao   | TEXT | Tipo de programação         |
| etapa_baixa        | TEXT | Etapa de baixa              |
| pc_cortado         | TEXT | Status PC (PROGRAMADO/CORTADO) |
| data_geracao       | DATE | Data de geração             |
| data_programacao   | DATE | Data de programação         |
| turno_programacao  | TEXT | Turno programado            |

#### ficha_tecnica_veiculos (Lookup)
| Campo         | Tipo | Descrição              |
|---------------|------|------------------------|
| codigo_veiculo| TEXT | Código do projeto      |
| marca         | TEXT | Marca do veículo       |
| modelo        | TEXT | Modelo do veículo      |

#### dados_uso_geral.dados_op (Dashboard)
| Campo      | Tipo | Descrição              |
|------------|------|------------------------|
| op         | TEXT | Ordem de Produção      |
| item       | TEXT | Código da peça         |
| produto    | TEXT | Projeto                |
| etapa      | TEXT | Etapa atual            |
| prioridade | TEXT | Prioridade             |
| planta     | TEXT | Planta (Jarinu)        |

## API Endpoints

### Autenticação
- `GET /` - Página de login
- `POST /login` - Autenticação de usuário
- `GET /logout` - Logout do sistema
- `GET /corte/sso` - **SSO redirect para sistema de Corte PC**

### Páginas Principais
- `GET /index` - Tela de otimização (redireciona Produção para /otimizadas)
- `GET /estoque` - Gestão de estoque
- `GET /locais` - Gerenciamento de slots
- `GET /otimizadas` - Peças em processo
- `GET /saidas` - Histórico de saídas
- `GET /arquivos` - **Gestão de arquivos PC** (Administrativo/T.I)
- `GET /baixas` - **Sistema de baixas** (Administrativo/T.I)
- `GET /register` - Gestão de usuários (apenas T.I)
- `GET /logs` - Sistema de logs (apenas T.I admin)

### APIs de Dados
- `GET /api/dados` - **Coleta dados com filtros de lote**
- `GET /api/lotes` - **Lista lotes disponíveis**
- `GET /api/estoque` - Lista itens do estoque
- `GET /api/otimizadas` - Lista peças otimizadas
- `GET /api/locais` - Lista slots com status
- `GET /api/contagem-pecas-locais` - Contagem de peças por slot
- `GET /api/local-detalhes/<local>` - Detalhes das peças em um slot
- `GET /api/saidas` - Histórico paginado de saídas
- `GET /api/baixas` - **Lista baixas de peças**
- `GET /api/arquivos` - **Lista arquivos de corte PC**
- `GET /api/logs` - Logs paginados (apenas T.I)
- `GET /api/usuarios` - Lista usuários (apenas T.I)
- `GET /api/dashboard-producao` - **Dados do dashboard** (porta 5002)

### APIs de Operação
- `POST /api/otimizar-pecas` - **Envia peças para otimização (com camadas)**
- `POST /api/enviar-estoque` - Move peças otimizadas para estoque
- `POST /api/remover-estoque` - Remove peças do estoque
- `POST /api/adicionar-local` - Cadastra novo slot
- `POST /api/baixar-peca` - **Registra baixa de peça**
- `POST /api/reprocessar-baixa` - **Reprocessa baixa para produção**
- `POST /api/entrada-manual-estoque` - **Entrada manual no estoque**
- `POST /api/voltar-estoque` - **Retorna peça da saída para estoque**
- `POST /api/excluir-otimizadas` - **Exclui peças otimizadas com motivo**

### APIs de Usuários (T.I)
- `POST /api/cadastrar-usuario` - Cria novo usuário
- `PUT /api/editar-usuario/<id>` - Edita usuário
- `PUT /api/resetar-senha/<id>` - **Reseta senha (pbkdf2)**
- `DELETE /api/excluir-usuario/<id>` - Exclui usuário

### APIs de Arquivos PC (Administrativo/T.I)
- `POST /api/arquivos` - **Adiciona arquivo de corte**
- `PUT /api/arquivos/<id>` - **Edita arquivo de corte**
- `DELETE /api/arquivos/<id>` - **Exclui arquivo de corte**
- `GET /api/buscar-arquivo` - **Busca arquivo por projeto/peça/sensor**
- `GET /api/buscar-veiculo-local` - **Busca veículo e sugere local**

### APIs de Exportação
- `POST /api/gerar-xml` - **Gera XMLs com base em arquivos de corte**
- `POST /api/gerar-excel-otimizacao` - Excel das peças selecionadas
- `POST /api/gerar-excel-estoque` - Excel do estoque
- `POST /api/gerar-excel-saidas` - Excel das saídas
- `POST /api/gerar-excel-logs` - Excel dos logs (T.I)
- `POST /api/importar-etiquetas` - **Importa dados para etiquetas**
- `POST /api/gerar-etiquetas-pdf` - **Gera PDF de etiquetas**
- `POST /api/importar-excel-pecas` - **Importa peças via Excel**

## Fluxo de Trabalho

### 1. Coleta e Otimização
1. **Login** no sistema com credenciais apropriadas
2. **Acesse Otimização** (tela principal)
3. **Configure filtros** de data/hora se necessário
4. **Colete dados** do banco de origem
5. **Selecione peças** para otimização
6. **Gere XML** ou **Excel** conforme necessidade
7. **Otimize peças** selecionadas

### 2. Processamento (Tela Otimizadas)
1. **Visualize peças** em processo de otimização
2. **Selecione peças** processadas
3. **Envie para estoque** final

### 3. Gestão de Estoque
1. **Monitore inventário** completo
2. **Remova peças** quando necessário
3. **Exporte relatórios** em Excel
4. **Acompanhe movimentações**

### 4. Administração (T.I)
1. **Gerencie usuários** e permissões
2. **Monitore logs** do sistema
3. **Configure locais** de armazenamento
4. **Exporte relatórios** de auditoria

## Algoritmo de Alocação de Slots

### Sistema de 169 Slots Organizados

#### **SLOTS 1-4: Peças Tamanho "GG" (Exclusivas)**
- Verificação na tabela `arquivos_pc` por `tamanho_peca = 'GG'`
- Capacidade: 6 peças por slot (configurável)
- Prioridade máxima para peças grandes

#### **SLOTS 4-40 e 81-117: Peças Médias**
**Tipos**: TSP, TSA, TSC, TSB, PBS, VGA
- Total: 73 slots disponíveis
- Sequência: SLOT 4 → SLOT 40, depois SLOT 81 → SLOT 117
- Capacidade: 6 peças por slot

#### **SLOTS 41-80 e 118-157: Peças Específicas**
**Tipos**: PDE, PDD, PTE, PTD, TME, TMD
- Total: 80 slots disponíveis
- Sequência: SLOT 41 → SLOT 80, depois SLOT 118 → SLOT 157
- Capacidade: 6 peças por slot

#### **SLOTS 158-169: Peças Pequenas (Alta Capacidade)**
**Tipos**: QTE, QTD, QDD, QDE, FTE, FTD, FDD, FDE
- Total: 12 slots disponíveis
- Maior capacidade por slot
- Sequência: SLOT 158 → SLOT 169

### **Lógica de Alocação**
1. **Verificar tamanho "GG"** → SLOTS 1-4
2. **Identificar tipo de peça** → Faixa correspondente
3. **Buscar primeiro slot disponível** na sequência
4. **Verificar capacidade** (limite configurável)
5. **Alocar e atualizar contador temporário**

## Requisitos do Sistema

### Software
- **Python**: 3.7+
- **PostgreSQL**: 12+
- **Navegadores**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

### Dependências Python
```
# Core Framework
Flask==2.3.3
Werkzeug==2.3.7

# Authentication
Flask-Login==0.6.3
bcrypt==4.0.1

# Database
psycopg2-binary==2.9.7

# Data Processing
numpy==1.26.4
pandas==2.0.3
openpyxl==3.1.2

# Configuration
python-dotenv==1.0.0

# PDF and Barcode Generation
reportlab==4.0.4
python-barcode==0.15.1
Pillow==10.0.0
```

### Configuração de Rede
- **Sistema Principal**: Porta 5001
- **Dashboard Produção**: Porta 5002
- **Host**: 0.0.0.0 (acesso em rede local)
- **Protocolo**: HTTP
- **Docker**: Porta 5001 (mapeada)
- **SSO**: Integração com sistema de Corte PC

## Segurança

- ✅ **Autenticação robusta** com hash pbkdf2:sha256
- ✅ **SSO Integration** com chave secreta compartilhada
- ✅ **Controle de sessão** persistente (365 dias)
- ✅ **Validação de permissões** por setor e função
- ✅ **Proteção contra inspeção** de código
- ✅ **Logs de auditoria** completos com timestamp
- ✅ **Validação de entrada** de dados
- ✅ **CORS configurado** para APIs
- ✅ **Sanitização** de dados de entrada

## Performance

- ✅ **Consultas otimizadas** com índices PostgreSQL
- ✅ **Paginação inteligente** em tabelas grandes
- ✅ **Cache de slots ocupados** durante alocação
- ✅ **Operações em lote** para múltiplas peças
- ✅ **Compressão ZIP** para XMLs
- ✅ **Threading** para dashboard e aplicação principal
- ✅ **Connection pooling** para banco de dados
- ✅ **Lazy loading** de dados grandes

## Personalização

### Configurar Banco de Dados
Edite o arquivo `.env` com suas credenciais PostgreSQL

### Modificar Algoritmo de Armazenamento
Altere a função `sugerir_local_armazenamento()` em `app.py`

### Customizar Interface
- **Estilos**: Modifique `static/css/style.css`
- **Lógica**: Edite arquivos JavaScript em `static/js/`
- **Layout**: Altere templates HTML em `templates/`

### Adicionar Funcionalidades
1. **Backend**: Crie novas rotas em `app.py`
2. **Frontend**: Adicione JavaScript correspondente
3. **Interface**: Crie/modifique templates HTML

## Manutenção

### Backup Recomendado
- **Banco de dados**: Backup diário automático
- **Logs**: Rotação semanal
- **Arquivos**: Backup dos XMLs gerados

### Monitoramento
- **Logs de sistema**: Tabela `pc_logs`
- **Dashboard**: Monitoramento em tempo real (porta 5002)
- **Performance**: Monitorar consultas lentas
- **Espaço**: Verificar crescimento das tabelas
- **Docker**: Logs via `docker-compose logs`
- **SSO**: Monitorar integrações entre sistemas

## Suporte e Desenvolvimento

**Desenvolvido por**: Pedro Torres  
**GitHub**: pgtorres7  
**Versão**: 2.2 SSO  
**Data**: Dezembro de 2024  
**Empresa**: Opera - Carbon Cars  

### Contato
- **Suporte técnico**: Setor T.I Opera
- **Melhorias**: Solicitar via chamados no Jira
- **Bugs**: Reportar ao administrador do sistema
- **SSO Issues**: Verificar configuração de chaves compartilhadas

### Novidades da Versão 2.2 SSO
- 🔗 **Integração SSO** com sistema de Acompanhamento de Corte
- 📊 **Dashboard independente** para monitoramento de produção
- 🏗️ **Containerização Docker** para deploy simplificado
- 📦 **Sistema de Slots** mais organizado e eficiente
- 🔄 **Gestão de Baixas** com reprocessamento automático
- 📁 **Arquivos PC** centralizados por projeto/peça
- 🏷️ **Sistema de Etiquetas** com códigos de barras
- 📈 **Melhor integração** com plano de controle de corte

---

*Sistema em produção - Todas as operações são logadas e auditadas*  
*Integração SSO ativa com sistema de Corte PC*