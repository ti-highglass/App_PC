from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, make_response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import psycopg2
import psycopg2.extras
import pandas as pd
import json
import io
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apontamentos_pplug_jarinu import atualizar_apontamentos

# Verificar se arquivo .env existe
if not os.path.exists('.env'):
    print("ERRO: Arquivo .env não encontrado!")
    print("Crie o arquivo .env com as credenciais do banco de dados.")
    exit(1)

load_dotenv()

app = Flask(__name__)
app.secret_key = 'opera_pu_system_2024'

# Configurações para servidor
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Configuração Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configuração do banco PostgreSQL
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PSW'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME')
}

# Verificar se todas as variáveis foram carregadas
if not all(DB_CONFIG.values()):
    print("ERRO: Variáveis de ambiente do banco não configuradas!")
    print(f"Valores carregados: {DB_CONFIG}")
    exit(1)

def enviar_email_credenciais(email_destino, usuario, senha):
    """Envia email com credenciais do usuário"""
    try:
        email_remetente = os.getenv('EMAIL_REMETENTE')
        senha_remetente = os.getenv('EMAIL_SENHA')
        
        if not email_remetente or not senha_remetente:
            print("ERRO: EMAIL_REMETENTE ou EMAIL_SENHA não configurados no .env")
            return
        
        print(f"Tentando enviar email de {email_remetente} para {email_destino}")
        
        # Configurar SMTP para Office 365
        smtp_server = "smtp.office365.com"
        smtp_port = 587
        
        msg = MIMEMultipart()
        msg['From'] = email_remetente
        msg['To'] = email_destino
        msg['Subject'] = "Credenciais de Acesso - Sistema Alocação PU"
        
        corpo_email = f"""Olá!

Suas credenciais de acesso ao Sistema de Alocação de PU foram criadas:

Usuário: {usuario}
Senha: {senha}

Acesse o sistema em: http://localhost:9995

Atenciosamente,
Equipe T.I Opera"""
        
        msg.attach(MIMEText(corpo_email, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(1)  # Debug SMTP
        server.starttls()
        server.login(email_remetente, senha_remetente)
        server.send_message(msg)
        server.quit()
        
        print(f"Email enviado com sucesso para {email_destino}")
        
    except Exception as e:
        print(f"Erro detalhado ao enviar email: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()



class User(UserMixin):
    def __init__(self, id, usuario, funcao, setor):
        self.id = id
        self.username = usuario
        self.role = funcao
        self.setor = setor

@login_manager.user_loader
def load_user(user_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM public.users_pu WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data['id'], user_data['usuario'], user_data['funcao'], user_data.get('setor', ''))
    return None

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM public.users_pu WHERE usuario = %s", (username,))
    user_data = cur.fetchone()
    conn.close()
    
    if user_data and check_password_hash(user_data['senha'], password):
        user = User(user_data['id'], user_data['usuario'], user_data['funcao'], user_data.get('setor', ''))
        login_user(user)
        return redirect(url_for('index'))
    
    flash('Usuário ou senha inválidos')
    return redirect(url_for('login'))

@app.route('/register')
@login_required
def register():
    if current_user.setor != 'T.I':
        flash('Acesso negado. Apenas o setor T.I pode cadastrar usuários.')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/api/usuarios')
@login_required
def api_usuarios():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("SELECT id, usuario, funcao, setor FROM public.users_pu ORDER BY id DESC")
        dados = cur.fetchall()
        conn.close()
        
        return jsonify([dict(row) for row in dados])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cadastrar-usuario', methods=['POST'])
@login_required
def cadastrar_usuario():
    if current_user.setor != 'T.I':
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        dados = request.get_json()
        username = dados.get('username', '').strip()
        password = dados.get('password', '').strip()
        role = dados.get('role', '').strip()
        setor = dados.get('setor', '').strip()
        email = dados.get('email', '').strip()
        
        if not all([username, password, role, setor, email]):
            return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios'})
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar se usuário já existe
        cur.execute("SELECT id FROM public.users_pu WHERE usuario = %s", (username,))
        if cur.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Usuário já existe'})
        
        # Criar usuário
        hashed_password = generate_password_hash(password)
        cur.execute(
            "INSERT INTO public.users_pu (usuario, senha, funcao, setor, email) VALUES (%s, %s, %s, %s, %s)",
            (username, hashed_password, role, setor, email)
        )
        conn.commit()
        conn.close()
        
        # Enviar email
        enviar_email_credenciais(email, username, password)
        
        return jsonify({'success': True, 'message': 'Usuário cadastrado e email enviado com sucesso!'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/resetar-senha/<int:user_id>', methods=['PUT'])
@login_required
def resetar_senha(user_id):
    if current_user.setor != 'T.I':
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        dados = request.get_json()
        nova_senha = dados.get('senha', '').strip()
        
        if not nova_senha:
            return jsonify({'success': False, 'message': 'Nova senha é obrigatória'})
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        hashed_password = generate_password_hash(nova_senha)
        cur.execute(
            "UPDATE public.users_pu SET senha = %s WHERE id = %s",
            (hashed_password, user_id)
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Senha resetada com sucesso!'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/editar-usuario/<int:user_id>', methods=['PUT'])
@login_required
def editar_usuario(user_id):
    if current_user.setor != 'T.I':
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        dados = request.get_json()
        usuario = dados.get('usuario', '').strip()
        funcao = dados.get('funcao', '').strip()
        setor = dados.get('setor', '').strip()
        
        if not all([usuario, funcao, setor]):
            return jsonify({'success': False, 'message': 'Usuário, função e setor são obrigatórios'})
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "UPDATE public.users_pu SET usuario = %s, funcao = %s, setor = %s WHERE id = %s",
            (usuario, funcao, setor, user_id)
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Usuário atualizado com sucesso!'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/excluir-usuario/<int:user_id>', methods=['DELETE'])
@login_required
def excluir_usuario(user_id):
    if current_user.setor != 'T.I':
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM public.users_pu WHERE id = %s", (user_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Usuário excluído com sucesso!'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/index')
@login_required
def index():
    if current_user.setor == 'Produção':
        return redirect(url_for('otimizadas'))
    if current_user.setor not in ['Administrativo', 'T.I']:
        flash('Acesso negado para este setor.')
        return redirect(url_for('otimizadas'))
    return render_template('index.html')

@app.route('/estoque')
@login_required
def estoque():
    if current_user.setor not in ['Produção', 'Administrativo', 'T.I']:
        flash('Acesso negado para este setor.')
        return redirect(url_for('index'))
    return render_template('estoque.html')

@app.route('/locais')
@login_required
def locais():
    if current_user.setor not in ['Produção', 'Administrativo', 'T.I']:
        flash('Acesso negado para este setor.')
        return redirect(url_for('index'))
    return render_template('locais.html')

@app.route('/otimizadas')
@login_required
def otimizadas():
    if current_user.setor not in ['Produção', 'Administrativo', 'T.I']:
        flash('Acesso negado para este setor.')
        return redirect(url_for('index'))
    return render_template('otimizadas.html')

@app.route('/saidas')
@login_required
def saidas():
    if current_user.setor not in ['Administrativo', 'T.I']:
        flash('Acesso negado para este setor.')
        return redirect(url_for('otimizadas'))
    return render_template('saidas.html')

@app.route('/arquivos')
@login_required
def arquivos():
    if current_user.setor not in ['Administrativo', 'T.I']:
        flash('Acesso negado para este setor.')
        return redirect(url_for('otimizadas'))
    return render_template('arquivos.html')



@app.route('/etiquetas')
@login_required
def etiquetas():
    if current_user.setor == 'Produção':
        flash('Acesso negado para este setor.')
        return redirect(url_for('otimizadas'))
    return render_template('etiquetas.html')

@app.route('/api/importar-etiquetas', methods=['POST', 'OPTIONS'])
@login_required
def importar_etiquetas():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
        
    try:
        if 'file' not in request.files:
            response = jsonify({'success': False, 'message': 'Nenhum arquivo enviado'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        
        file = request.files['file']
        if file.filename == '':
            response = jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        
        # Ler Excel com engine específico
        try:
            df = pd.read_excel(file, engine='openpyxl')
        except Exception as excel_error:
            response = jsonify({'success': False, 'message': f'Erro ao ler arquivo Excel: {str(excel_error)}'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        
        # Verificar se tem dados
        if df.empty:
            response = jsonify({'success': False, 'message': 'Arquivo vazio'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        
        # Processar apenas primeiras 3 linhas para teste
        dados_processados = []
        for i, row in df.head(3).iterrows():
            dados_processados.append({
                'id': str(row.get('ID', i)),
                'veiculo': str(row.get('Veiculo', 'Teste')),
                'op': str(row.get('OP', '123')),
                'peca': 'TSP',
                'descricao': str(row.get('Descrição', 'Teste')),
                'camada': 'L3',
                'quantidade_etiquetas': 1
            })
        
        return jsonify({'success': True, 'dados': dados_processados})
        
    except Exception as e:
        response = jsonify({'success': False, 'message': f'Erro: {str(e)}'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/api/gerar-etiquetas-pdf', methods=['POST'])
@login_required
def gerar_etiquetas_pdf():
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from datetime import datetime
        import tempfile
        import os
        
        dados = request.get_json().get('dados', [])
        
        if not dados:
            return jsonify({'success': False, 'message': 'Nenhum dado fornecido'})
        
        # Criar PDF em memória com tamanho personalizado para etiquetas
        buffer = io.BytesIO()
        etiqueta_width = 100*mm
        etiqueta_height = 50*mm
        
        # Usar tamanho da página igual ao da etiqueta
        c = canvas.Canvas(buffer, pagesize=(etiqueta_width, etiqueta_height))
        width, height = etiqueta_width, etiqueta_height
        
        x_pos = 0
        y_pos = 0
        
        primeira_etiqueta = True
        for item in dados:
            for i in range(item['quantidade_etiquetas']):
                # Nova página para cada etiqueta (exceto a primeira)
                if not primeira_etiqueta:
                    c.showPage()
                primeira_etiqueta = False
                
                # Desenhar etiqueta ocupando toda a página
                desenhar_etiqueta_simples(c, 0, 0, width, height, {
                    'OP': item['op'],
                    'Peca': item['peca'],
                    'Veiculo': item['veiculo'],
                    'Descricao': item.get('descricao', ''),
                    'ID': item['id']
                })
        
        c.save()
        buffer.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'etiquetas_{timestamp}.pdf'
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

def desenhar_etiqueta_simples(c, x, y, width, height, dados):
    from reportlab.lib.units import mm
    from datetime import datetime
    
    # Desenhar borda externa
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    c.rect(x + 1*mm, y + 1*mm, width - 2*mm, height - 2*mm)
    
    # Título PU no canto superior esquerdo
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x + 3*mm, y + height - 6*mm, "PU")
    
    # Data atual no canto superior direito
    data_atual = datetime.now().strftime("%d/%m/%Y")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + width - 25*mm, y + height - 6*mm, data_atual)
    
    # OP na linha principal (maior)
    y_pos = y + height - 15*mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x + 3*mm, y_pos, "OP:")
    c.setFont("Helvetica-Bold", 24)
    c.drawString(x + 15*mm, y_pos, f"{dados['OP']}")
    
    # CARRO (mais acima)
    y_pos -= 6*mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + 3*mm, y_pos, "CARRO:")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + 20*mm, y_pos, f"{dados['Veiculo']}")
    
    # ID na linha abaixo do carro (maior)
    y_pos -= 6*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x + 3*mm, y_pos, "ID:")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x + 15*mm, y_pos, f"{dados['ID']}")
    
    # DESCRIÇÃO abaixo da camada (grande)
    y_pos -= 8*mm
    c.setFont("Helvetica-Bold", 22)
    descricao = dados.get('Descricao', '')
    if len(descricao) > 30:
        descricao = descricao[:30] + '...'
    c.drawString(x + 3*mm, y_pos, descricao)
    
    # Código de barras Code128
    codigo_barras_texto = f"{dados['Peca']}{dados['OP']}"
    
    try:
        import barcode
        from barcode.writer import ImageWriter
        import tempfile
        import os
        
        # Configurar writer sem texto
        writer = ImageWriter()
        writer.quiet_zone = 3
        writer.font_size = 0
        writer.text_distance = 0
        writer.write_text = False
        
        # Gerar código de barras Code128 sem texto
        codigo_barras_obj = barcode.get('code128', codigo_barras_texto, writer=writer)
        codigo_barras_obj.default_writer_options['write_text'] = False
        
        # Salvar código de barras temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_barcode:
            img_barcode = codigo_barras_obj.render()
            img_barcode.save(tmp_barcode.name, 'PNG')
            tmp_barcode.close()
            
            # Inserir código de barras na parte inferior ocupando toda a largura
            c.drawImage(tmp_barcode.name, x + 2*mm, y + 1*mm, width=width-4*mm, height=10*mm)
            
            # Limpar arquivo temporário
            try:
                os.remove(tmp_barcode.name)
            except:
                pass
                
    except Exception as e:
        # Fallback: texto simples se código de barras falhar
        c.setFont("Courier", 8)
        c.drawString(x + 3*mm, y + 3*mm, codigo_barras_texto)

def sugerir_local_armazenamento(tipo_peca, locais_ocupados, conn):
    """Sugere local de armazenamento preenchendo horizontalmente E1, F1, G1..."""
    
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Buscar locais ocupados nas tabelas pu_inventory e pu_otimizadas
        cur.execute("""
            SELECT local FROM public.pu_inventory WHERE local IS NOT NULL
            UNION
            SELECT local FROM public.pu_otimizadas WHERE local IS NOT NULL AND tipo = 'PU'
        """)
        locais_ocupados_db = {row['local'] for row in cur.fetchall()}
        
        # Buscar locais ativos no banco
        cur.execute("SELECT local, nome FROM public.pu_locais WHERE status = 'Ativo' ORDER BY local")
        locais_ativos = cur.fetchall()
        
        if not locais_ativos:
            return 'E1', 'COLMEIA'
        
        # Criar mapeamento de locais por rack
        locais_por_rack = {}
        for local_info in locais_ativos:
            local = local_info['local']
            rack = local_info['nome']
            if rack not in locais_por_rack:
                locais_por_rack[rack] = []
            locais_por_rack[rack].append(local)
        
        # Ordenar locais por número para cada rack
        for rack in locais_por_rack:
            locais_por_rack[rack].sort(key=lambda x: (int(''.join(filter(str.isdigit, x))), x[0]))
        
        # Sequência de preenchimento horizontal: E1, F1, G1... depois E2, F2, G2...
        def gerar_sequencia_horizontal():
            sequencia = []
            
            # Determinar range de números para cada rack
            ranges_rack = {
                'RACK1': range(1, 29),
                'RACK2': range(29, 57), 
                'RACK3': range(57, 82)
            }
            
            # Para cada rack
            for rack_name in ['RACK1', 'RACK2', 'RACK3']:
                if rack_name not in locais_por_rack:
                    continue
                    
                num_range = ranges_rack[rack_name]
                
                # Primeiro preencher todas as colunas E até M
                for num in num_range:
                    for letra_code in range(ord('E'), ord('M') + 1):
                        letra = chr(letra_code)
                        local = f"{letra}{num}"
                        
                        if local in locais_por_rack[rack_name]:
                            sequencia.append((local, 'COLMEIA'))
                
                # Depois preencher D até A (só depois de terminar E-M)
                for num in num_range:
                    for letra_code in range(ord('D'), ord('A') - 1, -1):
                        letra = chr(letra_code)
                        local = f"{letra}{num}"
                        
                        if local in locais_por_rack[rack_name]:
                            sequencia.append((local, 'COLMEIA'))
            
            return sequencia
        
        sequencia_completa = gerar_sequencia_horizontal()
        
        # Combinar locais ocupados do banco com os já sugeridos nesta sessão
        todos_ocupados = locais_ocupados_db.union(locais_ocupados)
        
        # Buscar primeiro local disponível
        for local, rack in sequencia_completa:
            if local not in todos_ocupados:
                return local, rack
        
        # Se não encontrou nenhum disponível, retornar primeiro da sequência
        if sequencia_completa:
            return sequencia_completa[0][0], sequencia_completa[0][1]
        
        return 'E1', 'COLMEIA'
        
    except Exception as e:
        print(f"DEBUG: Erro na sugestão de local: {e}")
        return 'E1', 'COLMEIA'

@app.route('/api/adicionar-peca-manual', methods=['POST'])
def adicionar_peca_manual():
    dados = request.get_json()
    op = dados.get('op', '').strip()
    peca = dados.get('peca', '').strip()
    projeto = dados.get('projeto', '').strip()
    veiculo = dados.get('veiculo', '').strip()
    
    if not all([op, peca, projeto, veiculo]):
        return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios'})
    
    peca_data = {
        'op_pai': '0',
        'op': op,
        'peca': peca,
        'projeto': projeto,
        'veiculo': veiculo,
        'local': 'E1',
        'rack': 'COLMEIA'
    }
    
    return jsonify({'success': True, 'peca': peca_data})

@app.route('/api/atualizar-apontamentos', methods=['POST'])
@login_required
def api_atualizar_apontamentos():
    try:
        resultado = atualizar_apontamentos()
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao atualizar apontamentos: {str(e)}'}), 500

@app.route('/api/dados')
def api_dados():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    etapa = request.args.get('etapa', 'FILA')
    
    print(f"DEBUG: Buscando dados - etapa: {etapa}, data_inicio: {data_inicio}, data_fim: {data_fim}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Verificar se a tabela existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'apontamento_pplug_jarinu'
            )
        """)
        tabela_existe = cur.fetchone()[0]
        
        if not tabela_existe:
            print("DEBUG: Tabela apontamento_pplug_jarinu não existe")
            conn.close()
            return jsonify([])
        
        # Buscar peças já existentes no estoque e otimizadas
        cur.execute("SELECT op, peca FROM public.pu_inventory")
        pecas_estoque = cur.fetchall()
        
        cur.execute("SELECT op, peca FROM public.pu_otimizadas WHERE tipo = 'PU'")
        pecas_otimizadas = cur.fetchall()
        
        # Buscar locais ocupados
        cur.execute("SELECT local FROM public.pu_inventory UNION SELECT local FROM public.pu_otimizadas WHERE tipo = 'PU'")
        locais_ocupados = {row['local'] for row in cur.fetchall() if row['local']}
        
        # Criar set para busca rápida
        pecas_existentes = {f"{row['op']}_{row['peca']}" for row in pecas_estoque}
        pecas_existentes.update({f"{row['op']}_{row['peca']}" for row in pecas_otimizadas})
        
        # Construir query com filtros de data e etapa
        query = """
            SELECT op, item as peca, projeto, veiculo, data
            FROM public.apontamento_pplug_jarinu 
            WHERE UPPER(etapa) = UPPER(%s)
        """
        params = [etapa]
        
        if data_inicio:
            query += " AND data >= %s"
            params.append(data_inicio)
        
        if data_fim:
            query += " AND data <= %s"
            params.append(data_fim)
        
        query += " ORDER BY data DESC"
        
        print(f"DEBUG: Query: {query}")
        print(f"DEBUG: Params: {params}")
        
        cur.execute(query, params)
        dados_banco = cur.fetchall()
        
        print(f"DEBUG: Encontrados {len(dados_banco)} registros no banco")
        
        # Processar dados do banco
        dados_filtrados = []
        for row in dados_banco:
            try:
                chave_peca = f"{row['op']}_{row['peca']}"
                if chave_peca not in pecas_existentes:
                    # Aplicar lógica de sugestão
                    local_sugerido, rack_sugerido = sugerir_local_armazenamento(row['peca'], locais_ocupados, conn)
                    
                    # Verificar se existe arquivo de corte
                    cur.execute("""
                        SELECT COUNT(*) FROM public.arquivos_pu
                        WHERE projeto = %s AND peca = %s
                    """, (str(row['projeto']) if row['projeto'] else '', row['peca']))
                    
                    tem_arquivo = cur.fetchone()[0] > 0
                    arquivo_status = 'Arquivo encontrado' if tem_arquivo else 'Sem arquivo de corte'
                    
                    item = {
                        'op_pai': '0',
                        'op': str(row['op']) if row['op'] else '',
                        'peca': str(row['peca']) if row['peca'] else '',
                        'projeto': str(row['projeto']) if row['projeto'] else '',
                        'veiculo': str(row['veiculo']) if row['veiculo'] else '',
                        'local': local_sugerido or '',
                        'rack': rack_sugerido or '',
                        'data_criacao': row['data'].isoformat() if row['data'] else '',
                        'arquivo_status': arquivo_status
                    }
                    
                    # IMPORTANTE: Adicionar o local sugerido aos ocupados para próximas sugestões
                    if local_sugerido:
                        locais_ocupados.add(local_sugerido)
                    dados_filtrados.append(item)
            except Exception as row_error:
                print(f"DEBUG: Erro ao processar linha: {row_error}")
                continue
        
        conn.close()
        print(f"DEBUG: Retornando {len(dados_filtrados)} itens filtrados")
        return jsonify(dados_filtrados)
        
    except Exception as e:
        print(f"DEBUG: Erro na API dados: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro ao buscar dados: {str(e)}'}), 500

@app.route('/api/estoque')
def api_estoque():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Buscar todos os dados
        cur.execute("SELECT id, op_pai, op, peca, projeto, veiculo, local, rack FROM public.pu_inventory ORDER BY id DESC")
        dados = cur.fetchall()
        conn.close()
        
        resultado = []
        for row in dados:
            resultado.append({
                'id': row['id'],
                'op_pai': row['op_pai'] or '',
                'op': row['op'] or '',
                'peca': row['peca'] or '',
                'projeto': row['projeto'] or '',
                'veiculo': row['veiculo'] or '',
                'local': row['local'] or '',
                'rack': row['rack'] or ''
            })
        
        print(f"DEBUG: Retornando {len(resultado)} itens do estoque")
        return jsonify(resultado)
        
    except Exception as e:
        print(f"ERRO na API estoque: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/estoque-data')
def estoque_data():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, op_pai, op, peca, projeto, veiculo, local, rack FROM public.pu_inventory ORDER BY id DESC")
    dados = cur.fetchall()
    conn.close()
    return jsonify([dict(row) for row in dados])

@app.route('/api/otimizar-pecas', methods=['POST'])
@login_required
def otimizar_pecas():
    try:
        dados = request.get_json()
        pecas_selecionadas = dados.get('pecas', [])
        
        if not pecas_selecionadas:
            return jsonify({'success': False, 'message': 'Nenhuma peça selecionada'})
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Verificar duplicatas antes de inserir
        for peca in pecas_selecionadas:
            cur.execute("""
                SELECT COUNT(*) FROM public.pu_inventory 
                WHERE op = %s AND peca = %s
            """, (peca['op'], peca['peca']))
            
            if cur.fetchone()[0] > 0:
                conn.close()
                return jsonify({
                    'success': False, 
                    'message': f'Peça {peca["peca"]} OP {peca["op"]} já existe no estoque!'
                })
            
            cur.execute("""
                SELECT COUNT(*) FROM public.pu_otimizadas 
                WHERE op = %s AND peca = %s
            """, (peca['op'], peca['peca']))
            
            if cur.fetchone()[0] > 0:
                conn.close()
                return jsonify({
                    'success': False, 
                    'message': f'Peça {peca["peca"]} OP {peca["op"]} já existe nas otimizadas!'
                })
        
        # Verificar se há espaços disponíveis
        espacos_sem_local = [peca for peca in pecas_selecionadas if not peca.get('local') or peca.get('local') == '-' or peca.get('local') is None]
        
        if espacos_sem_local:
            conn.close()
            return jsonify({
                'success': False, 
                'message': f'Estoque cheio! Não há espaços disponíveis para {len(espacos_sem_local)} peça(s). Locais vazios: {[p.get("local") for p in espacos_sem_local]}'
            })
        
        # Criar tabelas se não existirem
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.pu_otimizadas (
                id SERIAL PRIMARY KEY,
                op_pai TEXT,
                op TEXT,
                peca TEXT,
                projeto TEXT,
                veiculo TEXT,
                local TEXT,
                rack TEXT,
                cortada BOOLEAN DEFAULT FALSE,
                user_otimizacao TEXT,
                data_otimizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tipo TEXT DEFAULT 'PU',
                camada TEXT
            )
        """)
        
        # Adicionar colunas se não existirem
        try:
            cur.execute("ALTER TABLE public.pu_otimizadas ADD COLUMN IF NOT EXISTS tipo TEXT DEFAULT 'PU'")
            cur.execute("ALTER TABLE public.pu_otimizadas ADD COLUMN IF NOT EXISTS camada TEXT")
        except:
            pass
        
        total_inseridas = 0
        
        # Inserir cada peça selecionada quebrada por camadas
        for peca in pecas_selecionadas:
            print(f"DEBUG: Processando peça {peca['peca']}")
            
            # Buscar camadas da peça na tabela camadas_pu
            cur.execute("""
                SELECT camada, qtde FROM public.camadas_pu 
                WHERE peca = %s
            """, (peca['peca'],))
            
            camadas = cur.fetchall()
            print(f"DEBUG: Encontradas {len(camadas)} camadas para peça {peca['peca']}")
            
            if camadas:
                # Se encontrou camadas, quebrar a peça
                for camada_info in camadas:
                    camada = camada_info['camada']
                    quantidade = int(camada_info['qtde'])
                    print(f"DEBUG: Camada {camada}, quantidade {quantidade}")
                    
                    # Inserir a quantidade de linhas para cada camada
                    for i in range(quantidade):
                        cur.execute("""
                            INSERT INTO public.pu_otimizadas (op_pai, op, peca, projeto, veiculo, local, rack, user_otimizacao, tipo, camada)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            peca.get('op_pai', ''),
                            peca['op'],
                            peca['peca'],
                            peca.get('projeto', ''),
                            peca['veiculo'],
                            peca['local'],
                            peca['rack'],
                            current_user.username,
                            'PU',
                            camada
                        ))
                        total_inseridas += 1
                        print(f"DEBUG: Inserida linha {i+1} da camada {camada}")
            else:
                print(f"DEBUG: Nenhuma camada encontrada para {peca['peca']}, inserindo sem camada")
                # Se não encontrou camadas, inserir como antes (sem camada)
                cur.execute("""
                    INSERT INTO public.pu_otimizadas (op_pai, op, peca, projeto, veiculo, local, rack, user_otimizacao, tipo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    peca.get('op_pai', ''),
                    peca['op'],
                    peca['peca'],
                    peca.get('projeto', ''),
                    peca['veiculo'],
                    peca['local'],
                    peca['rack'],
                    current_user.username,
                    'PU'
                ))
                total_inseridas += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'{len(pecas_selecionadas)} peça(s) processada(s), {total_inseridas} linha(s) inserida(s) na otimização!',
            'redirect': '/otimizadas'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/otimizadas')
@login_required
def api_otimizadas():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT id, op_pai, op, peca, projeto, veiculo, local, rack, cortada, user_otimizacao, data_otimizacao, camada 
            FROM public.pu_otimizadas 
            WHERE tipo = 'PU'
            ORDER BY id DESC
        """)
        dados = cur.fetchall()
        conn.close()
        
        resultado = []
        for row in dados:
            item = dict(row)
            if item['data_otimizacao']:
                item['data_otimizacao'] = item['data_otimizacao'].isoformat()
            resultado.append(item)
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/excluir-otimizadas', methods=['POST'])
@login_required
def excluir_otimizadas():
    try:
        dados = request.get_json()
        ids = dados.get('ids', [])
        motivo = dados.get('motivo', '').strip()
        
        if not ids:
            return jsonify({'success': False, 'message': 'Nenhuma peça selecionada'})
        
        if not motivo:
            return jsonify({'success': False, 'message': 'Motivo da exclusão é obrigatório'})
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Buscar peças antes de excluir
        placeholders = ','.join(['%s'] * len(ids))
        cur.execute(f"""
            SELECT * FROM public.pu_otimizadas 
            WHERE id IN ({placeholders}) AND tipo = 'PU'
        """, ids)
        pecas = cur.fetchall()
        
        # Inserir na tabela pu_exit com motivo
        for peca in pecas:
            cur.execute("""
                INSERT INTO public.pu_exit (op_pai, op, peca, projeto, veiculo, local, rack, usuario, data, motivo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                peca['op_pai'],
                peca['op'],
                peca['peca'],
                peca['projeto'],
                peca['veiculo'],
                peca['local'],
                peca['rack'],
                current_user.username,
                datetime.now(timezone(timedelta(hours=-3))),
                f'EXCLUSÃO: {motivo}'
            ))
        
        # Remover das otimizadas
        cur.execute(f"DELETE FROM public.pu_otimizadas WHERE id IN ({placeholders})", ids)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{len(pecas)} peça(s) excluída(s) com sucesso!'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/enviar-estoque', methods=['POST'])
@login_required
def enviar_estoque():
    try:
        dados = request.get_json()
        ids = dados.get('ids', [])
        
        if not ids:
            return jsonify({'success': False, 'message': 'Nenhuma peça selecionada'})
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Buscar peças selecionadas
        placeholders = ','.join(['%s'] * len(ids))
        cur.execute(f"""
            SELECT * FROM public.pu_otimizadas 
            WHERE id IN ({placeholders}) AND tipo = 'PU'
        """, ids)
        pecas = cur.fetchall()
        
        # Inserir no estoque
        for peca in pecas:
            cur.execute("""
                INSERT INTO public.pu_inventory (op_pai, op, peca, projeto, veiculo, local, rack, data, usuario)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
            """, (
                peca['op_pai'],
                peca['op'],
                peca['peca'],
                peca['projeto'],
                peca['veiculo'],
                peca['local'],
                peca['rack'],
                current_user.username
            ))
        
        # Log da ação
        cur.execute("""
            INSERT INTO public.pu_logs (usuario, acao, detalhes)
            VALUES (%s, %s, %s)
        """, (
            current_user.username,
            'ENVIAR_ESTOQUE',
            f'Enviou {len(pecas)} peça(s) para o estoque'
        ))
        
        # Remover da tabela de otimizadas
        placeholders = ','.join(['%s'] * len(ids))
        cur.execute(f"DELETE FROM public.pu_otimizadas WHERE id IN ({placeholders})", ids)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{len(pecas)} peça(s) enviada(s) para o estoque com sucesso!'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/remover-estoque', methods=['POST'])
def remover_estoque():
    dados = request.get_json()
    ids = dados.get('ids', [])
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    for id_item in ids:
        cur.execute("SELECT * FROM public.pu_inventory WHERE id = %s", (id_item,))
        peca = cur.fetchone()
        
        if peca:
            cur.execute("""
                INSERT INTO public.pu_exit (op_pai, op, peca, projeto, veiculo, local, rack, usuario, data, motivo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
            """, (
                peca.get('op_pai', ''),
                peca['op'],
                peca['peca'],
                peca.get('projeto', ''),
                peca.get('veiculo', ''),
                peca['local'],
                peca.get('rack', ''),
                'sistema',
                'SAÍDA DO ESTOQUE'
            ))
            
            cur.execute("DELETE FROM public.pu_inventory WHERE id = %s", (id_item,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'{len(ids)} peça(s) removida(s) do estoque!'})

@app.route('/api/arquivos')
@login_required
def api_arquivos():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Resetar sequência do ID para evitar duplicatas
        try:
            cur.execute("SELECT setval('arquivos_pu_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM public.arquivos_pu), false)")
            conn.commit()
        except:
            pass
        
        # Buscar dados
        cur.execute("SELECT * FROM public.arquivos_pu ORDER BY id DESC")
        dados = cur.fetchall()
        conn.close()
        
        return jsonify([dict(row) for row in dados])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/arquivos', methods=['POST', 'OPTIONS'])
@login_required
def adicionar_arquivo():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
        
    try:
        # Tentar diferentes formas de obter os dados
        dados = None
        if request.is_json:
            dados = request.get_json()
        else:
            dados = request.get_json(force=True)
            
        if not dados:
            response = jsonify({'success': False, 'message': 'Dados não recebidos'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        
        projeto = dados.get('projeto', '').strip()
        peca = dados.get('peca', '').strip()
        nome_peca = dados.get('nome_peca', '').strip()
        camada = dados.get('camada', '').strip()
        espessura = dados.get('espessura')
        quantidade = dados.get('quantidade')
        
        if not all([projeto, peca, nome_peca, camada]):
            response = jsonify({'success': False, 'message': 'Projeto, peça, nome da peça e camada são obrigatórios'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        
        # Converter valores numéricos
        try:
            espessura_val = float(espessura) if espessura else 0.5
        except:
            espessura_val = 0.5
            
        try:
            quantidade_val = int(quantidade) if quantidade else 1
        except:
            quantidade_val = 1
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO public.arquivos_pu (projeto, peca, nome_peca, camada, espessura, quantidade)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (projeto, peca, nome_peca, camada, espessura_val, quantidade_val))
        
        conn.commit()
        conn.close()
        
        response = jsonify({'success': True, 'message': 'Arquivo adicionado com sucesso!'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        response = jsonify({'success': False, 'message': f'Erro: {str(e)}'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/api/arquivos/<int:arquivo_id>', methods=['PUT', 'OPTIONS'])
@login_required
def editar_arquivo(arquivo_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'PUT')
        return response
        
    try:
        dados = request.get_json(force=True)
        projeto = dados.get('projeto', '').strip()
        peca = dados.get('peca', '').strip()
        nome_peca = dados.get('nome_peca', '').strip()
        camada = dados.get('camada', '').strip()
        espessura = dados.get('espessura') or 0.5
        quantidade = dados.get('quantidade') or 1
        
        if not all([projeto, peca, nome_peca, camada]):
            response = jsonify({'success': False, 'message': 'Projeto, peça, nome da peça e camada são obrigatórios'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE public.arquivos_pu 
            SET projeto = %s, peca = %s, nome_peca = %s, camada = %s, 
                espessura = %s, quantidade = %s
            WHERE id = %s
        """, (projeto, peca, nome_peca, camada, float(espessura), int(quantidade), arquivo_id))
        
        conn.commit()
        conn.close()
        
        response = jsonify({'success': True, 'message': 'Arquivo atualizado com sucesso!'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        response = jsonify({'success': False, 'message': f'Erro: {str(e)}'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/api/arquivos/<int:arquivo_id>', methods=['DELETE', 'OPTIONS'])
@login_required
def excluir_arquivo(arquivo_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'DELETE')
        return response
        
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM public.arquivos_pu WHERE id = %s", (arquivo_id,))
        
        conn.commit()
        conn.close()
        
        response = jsonify({'success': True, 'message': 'Arquivo excluído com sucesso!'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        response = jsonify({'success': False, 'message': f'Erro: {str(e)}'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/api/locais')
def api_locais():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT id, local, rack, nome, status FROM public.pu_locais ORDER BY id")
        dados = cur.fetchall()
        conn.close()
        return jsonify([dict(row) for row in dados])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contagem-pecas-locais')
@login_required
def api_contagem_pecas_locais():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("""
            SELECT local, COUNT(*) as total 
            FROM public.pu_inventory 
            WHERE local IS NOT NULL AND local != ''
            GROUP BY local
        """)
        dados = [dict(row) for row in cur.fetchall()]
        
        conn.close()
        return jsonify(dados)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/local-detalhes/<local>')
@login_required
def api_local_detalhes(local):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("SELECT op, peca, projeto, veiculo FROM public.pu_inventory WHERE local = %s", (local,))
        pecas = [dict(row) for row in cur.fetchall()]
        
        conn.close()
        
        return jsonify({
            'local': local,
            'pecas': pecas,
            'total': len(pecas)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Executar uma única vez para popular a tabela
def popular_locais_iniciais():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Criar tabelas se não existirem
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.pu_locais (
                id SERIAL PRIMARY KEY,
                local TEXT,
                rack TEXT,
                status TEXT DEFAULT 'Ativo',
                nome TEXT
            )
        """)
        
        # Adicionar coluna email na tabela users_pu se não existir
        try:
            cur.execute("ALTER TABLE public.users_pu ADD COLUMN IF NOT EXISTS email TEXT")
            conn.commit()
        except:
            pass
        

        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.pu_inventory (
                id SERIAL PRIMARY KEY,
                op_pai TEXT,
                op TEXT,
                peca TEXT,
                projeto TEXT,
                veiculo TEXT,
                local TEXT,
                rack TEXT,
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario TEXT
            )
        """)
        
        # Adicionar colunas se não existirem
        try:
            cur.execute("ALTER TABLE public.pu_inventory ADD COLUMN IF NOT EXISTS data TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            cur.execute("ALTER TABLE public.pu_inventory ADD COLUMN IF NOT EXISTS usuario TEXT")
            conn.commit()
        except:
            pass
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.pu_exit (
                id SERIAL PRIMARY KEY,
                op_pai TEXT,
                op TEXT,
                peca TEXT,
                projeto TEXT,
                veiculo TEXT,
                local TEXT,
                rack TEXT,
                usuario TEXT,
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                motivo TEXT
            )
        """)
        
        # Verificar se já existem locais
        cur.execute("SELECT COUNT(*) FROM public.pu_locais")
        count = cur.fetchone()[0]
        
        if count == 0:
            # RACK1: A-M, 1-28
            for letra_code in range(ord('A'), ord('M') + 1):
                letra = chr(letra_code)
                for num in range(1, 29):
                    local = f"{letra}{num}"
                    cur.execute("""
                        INSERT INTO public.pu_locais (local, rack, status, nome)
                        VALUES (%s, %s, %s, %s)
                    """, (local, 'COLMEIA', 'Ativo', 'RACK1'))
            
            # RACK2: A-M, 29-56
            for letra_code in range(ord('A'), ord('M') + 1):
                letra = chr(letra_code)
                for num in range(29, 57):
                    local = f"{letra}{num}"
                    cur.execute("""
                        INSERT INTO public.pu_locais (local, rack, status, nome)
                        VALUES (%s, %s, %s, %s)
                    """, (local, 'COLMEIA', 'Ativo', 'RACK2'))
            
            # RACK3: A-M, 57-81
            for letra_code in range(ord('A'), ord('M') + 1):
                letra = chr(letra_code)
                for num in range(57, 82):
                    local = f"{letra}{num}"
                    cur.execute("""
                        INSERT INTO public.pu_locais (local, rack, status, nome)
                        VALUES (%s, %s, %s, %s)
                    """, (local, 'COLMEIA', 'Ativo', 'RACK3'))
            
            conn.commit()
            print("Locais populados com sucesso: RACK1 (A1-M28), RACK2 (A29-M56), RACK3 (A57-M81)")
        
        conn.close()
        
    except Exception as e:
        print(f"Erro ao popular locais: {e}")

# Executar automaticamente na inicialização
try:
    popular_locais_iniciais()
    

except Exception as e:
    print(f"Erro na inicialização: {e}")

@app.route('/api/adicionar-local', methods=['POST'])
@login_required
def adicionar_local():
    try:
        data = request.get_json()
        local = data.get('local')
        nome = data.get('nome')

        if not local or not nome:
            return jsonify({'success': False, 'message': 'Preencha todos os campos.'})

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar se local já existe
        cur.execute("SELECT id FROM public.pu_locais WHERE local = %s", (local,))
        if cur.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Local já existe'})

        cur.execute("""
            INSERT INTO public.pu_locais (local, rack, status, nome)
            VALUES (%s, %s, %s, %s)
        """, (local, 'COLMEIA', 'Ativo', nome))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Local adicionado com sucesso!'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao adicionar local: {str(e)}'})

@app.route('/api/alterar-status-local', methods=['PUT'])
@login_required
def alterar_status_local():
    try:
        data = request.get_json()
        local = data.get('local')
        status = data.get('status')

        if not local or not status:
            return jsonify({'success': False, 'message': 'Dados incompletos'})

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE public.pu_locais 
            SET status = %s 
            WHERE local = %s
        """, (status, local))

        if cur.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'message': 'Local não encontrado'})

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': f'Status alterado para {status}!'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao alterar status: {str(e)}'})



@app.route('/api/saidas')
def api_saidas():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT id, op, peca, local, usuario, data FROM public.pu_exit ORDER BY id DESC LIMIT 50")
        dados = cur.fetchall()
        conn.close()
        
        resultado = []
        for row in dados:
            item = dict(row)
            if item.get('data'):
                item['data'] = item['data'].strftime('%d/%m/%Y')
            resultado.append(item)
        
        return jsonify({
            'dados': resultado,
            'pagination': {'current_page': 1, 'total_pages': 1, 'total_records': len(resultado), 'limit': 50}
        })
    except:
        return jsonify({'dados': [], 'pagination': {'current_page': 1, 'total_pages': 1, 'total_records': 0, 'limit': 50}})

@app.route('/api/gerar-xml', methods=['POST'])
@login_required
def gerar_xml():
    try:
        if request.is_json:
            dados = request.get_json()
            pecas_selecionadas = dados.get('pecas', [])
        else:
            pecas_json = request.form.get('pecas', '[]')
            pecas_selecionadas = json.loads(pecas_json)
        
        if not pecas_selecionadas:
            return jsonify({'success': False, 'message': 'Nenhuma peça selecionada'})
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        import zipfile
        import os
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        
        zip_buffer = io.BytesIO()
        xmls_gerados = []
        xmls_nao_gerados = []
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for peca_data in pecas_selecionadas:
                projeto = peca_data.get('projeto', '')
                peca_codigo = peca_data['peca']
                op = peca_data['op']
                
                # Buscar todas as camadas da peça usando projeto+peca
                cur.execute("""
                    SELECT * FROM public.arquivos_pu
                    WHERE projeto = %s AND peca = %s
                    ORDER BY camada
                """, (projeto, peca_codigo))
                
                arquivos = cur.fetchall()
                
                if not arquivos:
                    xmls_nao_gerados.append(f"{projeto} {peca_codigo}")
                    continue
                
                for arquivo_info in arquivos:
                    # Usar campos disponíveis ou valores padrão
                    nome_peca = arquivo_info.get('nome_peca', arquivo_info.get('caminho', peca_codigo))
                    espessura = arquivo_info.get('espessura', '1.0')
                    camada = arquivo_info.get('camada', '1')
                    quantidade = int(arquivo_info.get('quantidade', '1'))

                    # Gerar múltiplos XMLs baseado na quantidade
                    for i in range(quantidade):
                        # Criar XML
                        root = Element('RPOrderGenerator')
                        root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
                        root.set('xmlns:xsd', 'http://www.w3.org/2001/XMLSchema')

                        queued_item = SubElement(root, 'QueuedItem')

                        SubElement(queued_item, 'Driver').text = 'D006'
                        SubElement(queued_item, 'TransactionId').text = '000'
                        SubElement(queued_item, 'PartCode').text = nome_peca

                        # Adicionar os campos solicitados
                        SubElement(queued_item, 'CustomerCode').text = peca_data.get('veiculo', '')  # Nome do veículo
                        part_description = f"{peca_data.get('local', '')} | {projeto} | {peca_codigo} | {camada}"
                        SubElement(queued_item, 'CustomerDescription').text = part_description  # Concatenação como antes

                        SubElement(queued_item, 'Material').text = 'Acrílico-0'
                        SubElement(queued_item, 'Thickness').text = str(espessura)
                        # Adicionar letra no final da OP
                        letra_sequencia = chr(ord('A') + i)
                        SubElement(queued_item, 'Order').text = f"{peca_data['op']}-{letra_sequencia}"
                        SubElement(queued_item, 'QtyRequired').text = '1'  # Sempre 1 por XML
                        SubElement(queued_item, 'DeliveryDate').text = datetime.now().strftime('%d/%m/%Y')
                        SubElement(queued_item, 'FilePart').text = nome_peca

                        # Formatar XML
                        rough_string = tostring(root, 'utf-8')
                        reparsed = minidom.parseString(rough_string)
                        pretty_xml = reparsed.toprettyxml(indent='  ', encoding='utf-8')
                        
                        # Nome do arquivo XML: op+peca+projeto+camada+numero
                        xml_filename = f"{op}_{peca_codigo}_{projeto}_{camada}_{i+1:02d}.xml"
                        zip_file.writestr(xml_filename, pretty_xml)
                    
                    xmls_gerados.append(f"OP {op} - Peça {peca_codigo} - {quantidade} XML(s) {camada}")
        
        # Log da ação com detalhes
        if xmls_nao_gerados:
            detalhes_log = f"XMLs: {len(xmls_gerados)} gerados, {len(xmls_nao_gerados)} não encontrados - {'; '.join(xmls_nao_gerados[:5])}"
            if len(xmls_nao_gerados) > 5:
                detalhes_log += f" e mais {len(xmls_nao_gerados) - 5}"
        else:
            detalhes_log = f"Gerou {len(xmls_gerados)} XML(s) com sucesso"
        
        cur.execute("""
            INSERT INTO public.pu_logs (usuario, acao, detalhes)
            VALUES (%s, %s, %s)
        """, (current_user.username, 'GERAR_XML', detalhes_log))
        
        conn.commit()
        conn.close()
        
        # Se não gerou nenhum XML
        if not xmls_gerados:
            return jsonify({
                'success': False, 
                'message': f'Nenhum XML foi gerado. Peças não encontradas: {"; ".join(xmls_nao_gerados)}'
            })
        
        zip_buffer.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Preparar mensagem de retorno
        mensagem = f'{len(xmls_gerados)} XML(s) gerado(s) com sucesso!'
        if xmls_nao_gerados:
            mensagem += f'\n\nArquivos não encontrados ({len(xmls_nao_gerados)}):'
            for item in xmls_nao_gerados:
                mensagem += f'\n• {item}'
        
        # Salvar ZIP na pasta do SharePoint
        zip_saved_sharepoint = False
        sharepoint_paths = [
            os.path.expanduser(r"~\CARBON CARS\Programação e Controle de Produção - DocumentosPCP\AUTOMACAO LIBELLULA"),
            os.path.expanduser(r"~\OneDrive - CARBON CARS\Programação e Controle de Produção - DocumentosPCP\AUTOMACAO LIBELLULA"),
            os.path.expanduser(r"~\OneDrive\CARBON CARS\Programação e Controle de Produção - DocumentosPCP\AUTOMACAO LIBELLULA"),
            os.path.expanduser(r"~\Documents\XMLs")
        ]
        
        zip_filename = f'xmls_otimizacao_{timestamp}.zip'
        
        for sharepoint_path in sharepoint_paths:
            try:
                if os.path.exists(sharepoint_path):
                    zip_file_path = os.path.join(sharepoint_path, zip_filename)
                    with open(zip_file_path, 'wb') as f:
                        f.write(zip_buffer.getvalue())
                    zip_saved_sharepoint = True
                    mensagem += f"\n\nArquivo ZIP salvo em: {sharepoint_path}"
                    break
            except Exception:
                continue
        
        if not zip_saved_sharepoint:
            mensagem += "\n\nAVISO: Não foi possível salvar em pasta sincronizada."
        
        return jsonify({
            'success': True,
            'message': mensagem
        })
    except Exception as e:
        import traceback
        print("Erro ao gerar XML:", traceback.format_exc())  # Log detalhado no console
        return jsonify({'success': False, 'message': f'Erro ao gerar XMLs: {str(e)}'}), 500

@app.route('/download-xml/<filename>')
@login_required
def download_xml(filename):
    import tempfile
    import os
    
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, filename)
    
    if os.path.exists(file_path):
        def remove_file(response):
            try:
                os.remove(file_path)
            except:
                pass
            return response
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(file_path, as_attachment=True, download_name=f'xmls_otimizacao_{timestamp}.zip')
    else:
        return jsonify({'error': 'Arquivo não encontrado'}), 404

@app.route('/api/gerar-excel-otimizacao', methods=['POST'])
@login_required
def gerar_excel_otimizacao():
    try:
        dados_json = request.form.get('dados', '[]')
        dados = json.loads(dados_json)
        
        if not dados:
            return jsonify({'success': False, 'message': 'Nenhum dado encontrado'})
        
        df = pd.DataFrame(dados)
        df = df.rename(columns={
            'op_pai': 'OP-PAI',
            'op': 'OP',
            'peca': 'PEÇA',
            'projeto': 'PROJETO',
            'veiculo': 'VEÍCULO',
            'local': 'LOCAL',
            'rack': 'RACK'
        })
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'otimizacao_{timestamp}.xlsx'
        
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao gerar Excel: {str(e)}'}), 500

@app.route('/api/gerar-excel-estoque', methods=['POST'])
def gerar_excel_estoque():
    try:
        dados_json = request.form.get('dados', '[]')
        dados = json.loads(dados_json)
        
        if not dados:
            return jsonify({'success': False, 'message': 'Nenhum dado encontrado'})
        
        df = pd.DataFrame(dados)
        df = df.rename(columns={
            'op_pai': 'OP-PAI',
            'op': 'OP',
            'peca': 'PEÇA',
            'projeto': 'PROJETO',
            'veiculo': 'VEÍCULO',
            'local': 'LOCAL',
            'rack': 'RACK'
        })
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'estoque_{timestamp}.xlsx'
        
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao gerar Excel: {str(e)}'}), 500

@app.route('/api/gerar-excel-saidas', methods=['POST'])
@login_required
def gerar_excel_saidas():
    try:
        dados_json = request.form.get('dados', '[]')
        dados = json.loads(dados_json)
        
        if not dados:
            return jsonify({'success': False, 'message': 'Nenhum dado encontrado'})
        
        df = pd.DataFrame(dados)
        df = df.rename(columns={
            'op_pai': 'OP-PAI',
            'op': 'OP',
            'peca': 'PEÇA',
            'projeto': 'PROJETO',
            'veiculo': 'VEÍCULO',
            'local': 'LOCAL',
            'rack': 'RACK',
            'usuario': 'USUÁRIO',
            'data': 'DATA SAÍDA'
        })
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'saidas_{timestamp}.xlsx'
        
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao gerar Excel: {str(e)}'}), 500

@app.route('/api/gerar-excel-logs', methods=['POST'])
@login_required
def gerar_excel_logs():
    if current_user.setor != 'T.I' or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    try:
        dados_json = request.form.get('dados', '[]')
        dados = json.loads(dados_json)
        
        if not dados:
            return jsonify({'success': False, 'message': 'Nenhum dado encontrado'})
        
        df = pd.DataFrame(dados)
        df = df.rename(columns={
            'usuario': 'USUÁRIO',
            'acao': 'AÇÃO',
            'detalhes': 'DETALHES',
            'data_acao': 'DATA AÇÃO'
        })
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'logs_{timestamp}.xlsx'
        
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao gerar Excel: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9995, debug=True)