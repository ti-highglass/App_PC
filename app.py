from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, make_response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from itsdangerous import URLSafeTimedSerializer
import psycopg2
import psycopg2.extras
import pandas as pd
import json
import io
import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.error
import urllib.request
from urllib.parse import urlencode


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')

# Verificar se arquivo .env existe
if not os.path.exists(ENV_PATH):
    print("ERRO: Arquivo .env não encontrado!")
    print("Crie o arquivo .env com as credenciais do banco de dados.")
    exit(1)

load_dotenv(ENV_PATH)

app = Flask(__name__)
app.secret_key = 'opera_pc_system_2024'
app.permanent_session_lifetime = timedelta(days=365)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)
app.config['SESSION_PERMANENT'] = True

# Configurações para servidor
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

@app.before_request
def before_request():
    from flask import session
    if 'user_id' in session:
        session.permanent = True

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
login_manager.session_protection = None
login_manager.refresh_view = None

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

SSO_SHARED_SECRET = os.getenv('SSO_SHARED_SECRET')
SSO_SALT = os.getenv('SSO_SALT', 'app-pc-acomp-sso')
ACOMP_CORTE_BASE_URL = os.getenv('ACOMP_CORTE_BASE_URL')
ACOMP_CORTE_SSO_LOGOUT_URL = os.getenv('ACOMP_CORTE_SSO_LOGOUT_URL')
ETIQUETAS_BASE_URL = os.getenv('ETIQUETAS_BASE_URL')

def _sso_enabled():
    return bool(SSO_SHARED_SECRET and ACOMP_CORTE_BASE_URL)


def _sso_serializer():
    if not _sso_enabled():
        return None
    return URLSafeTimedSerializer(SSO_SHARED_SECRET)


def _build_sso_payload(user):
    now_ts = int(datetime.now(timezone.utc).timestamp())
    return {
        'id': user.id,
        'usuario': user.username,
        'setor': getattr(user, 'setor', ''),
        'funcao': getattr(user, 'role', ''),
        'iat': now_ts,
    }


def _generate_sso_token(user):
    serializer = _sso_serializer()
    if not serializer:
        return None
    payload = _build_sso_payload(user)
    return serializer.dumps(payload, salt=SSO_SALT)


def _trigger_remote_logout():
    if not (_sso_enabled() and ACOMP_CORTE_SSO_LOGOUT_URL):
        return

    def _call():
        try:
            urllib.request.urlopen(ACOMP_CORTE_SSO_LOGOUT_URL, timeout=2)
        except urllib.error.URLError:
            pass
        except Exception:
            pass

    threading.Thread(target=_call, daemon=True).start()


@app.context_processor
def inject_corte_links():
    return {
        'corte_sso_link': url_for('corte_sso_redirect'),
        'sso_corte_enabled': _sso_enabled(),
    }

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
        msg['Subject'] = "Credenciais de Acesso - Sistema Alocação PC"
        
        corpo_email = f"""Olá!

Suas credenciais de acesso ao Sistema de Alocação de PC foram criadas:

Usuário: {usuario}
Senha: {senha}

Acesse o sistema em: http://localhost:5001

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
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM public.users WHERE id = %s AND sistema = 'PC'", (user_id,))
        user_data = cur.fetchone()
        conn.close()
        
        if user_data:
            return User(user_data['id'], user_data['usuario'], user_data['funcao'], user_data.get('setor', ''))
    except:
        pass
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
    
    print(f"DEBUG: Tentativa de login - Usuário: {username}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM public.users WHERE usuario = %s AND sistema = 'PC'", (username,))
        user_data = cur.fetchone()
        conn.close()
        
        print(f"DEBUG: Usuário encontrado: {user_data is not None}")
        
        if user_data:
            senha_correta = False
            
            # Verificar se é hash (começa com pbkdf2:sha256:)
            if user_data['senha'].startswith('pbkdf2:sha256:'):
                print("DEBUG: Verificando senha com hash")
                senha_correta = check_password_hash(user_data['senha'], password)
            else:
                print("DEBUG: Verificando senha em texto plano")
                # Verificar como texto plano
                senha_correta = (user_data['senha'] == password)
            
            print(f"DEBUG: Senha correta: {senha_correta}")
            
            if senha_correta:
                user = User(user_data['id'], user_data['usuario'], user_data['funcao'], user_data.get('setor', ''))
                login_user(user, remember=True, duration=timedelta(days=365))
                from flask import session
                session.permanent = True
                return redirect(url_for('index'))
    
    except Exception as e:
        print(f"Erro no login: {e}")
    
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
        
        cur.execute("SELECT id, usuario, funcao, setor FROM public.users WHERE sistema = 'PC' ORDER BY id DESC")
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
        
        if not all([username, password, role, setor]):
            return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios'})
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar se usuário já existe
        cur.execute("SELECT id FROM public.users WHERE usuario = %s AND sistema = 'PC'", (username,))
        if cur.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Usuário já existe'})
        
        # Criar usuário
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        cur.execute(
            "INSERT INTO public.users (usuario, senha, funcao, setor, sistema) VALUES (%s, %s, %s, %s, %s)",
            (username, hashed_password, role, setor, 'PC')
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Usuário cadastrado com sucesso!'})
    
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
        
        # Gerar hash da nova senha
        hashed_password = generate_password_hash(nova_senha, method='pbkdf2:sha256')
        print(f"DEBUG: Hash gerado: {hashed_password[:50]}...")
        
        cur.execute(
            "UPDATE public.users SET senha = %s WHERE id = %s AND sistema = 'PC'",
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
            "UPDATE public.users SET usuario = %s, funcao = %s, setor = %s WHERE id = %s AND sistema = 'PC'",
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
        
        cur.execute("DELETE FROM public.users WHERE id = %s AND sistema = 'PC'", (user_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Usuário excluído com sucesso!'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500



@app.route('/logout')
@login_required
def logout():
    _trigger_remote_logout()
    logout_user()
    return redirect(url_for('login'))


def _safe_next_target(raw_value):
    if not raw_value:
        return None
    value = raw_value.strip()
    if not value.startswith('/'):
        return None
    return value


@app.route('/corte/sso')
@login_required
def corte_sso_redirect():
    if not _sso_enabled():
        flash('SSO com Corte PC não está configurado.')
        return redirect(url_for('otimizadas'))

    token = _generate_sso_token(current_user)
    if not token:
        flash('Não foi possível iniciar o SSO com Corte PC.')
        return redirect(url_for('otimizadas'))

    login_url = f"{ACOMP_CORTE_BASE_URL.rstrip('/')}/sso-login"
    params = {'token': token}
    next_target = _safe_next_target(request.args.get('next'))
    if next_target:
        params['next'] = next_target

    return redirect(f"{login_url}?{urlencode(params)}")

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

@app.route('/baixas')
@login_required
def baixas():
    if current_user.setor not in ['Administrativo', 'T.I']:
        flash('Acesso negado para este setor.')
        return redirect(url_for('otimizadas'))
    return render_template('baixas.html')



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

# Contador global para simular ocupação durante processamento
contador_slots_temp = {}

def sugerir_local_armazenamento(tipo_peca, locais_ocupados, conn):
    """Sugere slot baseado no tipo de peça e capacidade"""
    global contador_slots_temp
    
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Buscar slots com limites da tabela pc_locais
        cur.execute("SELECT local, limite FROM public.pc_locais WHERE status = 'Ativo' ORDER BY local")
        slots_info = {row['local']: int(row['limite']) if row['limite'] else 6 for row in cur.fetchall()}
        
        # Contar ocupação atual (estoque + otimizadas)
        cur.execute("""
            SELECT local, COUNT(*) as total 
            FROM (
                SELECT local FROM public.pc_inventory WHERE local IS NOT NULL AND local != ''
                UNION ALL
                SELECT local FROM public.pc_otimizadas WHERE local IS NOT NULL AND local != '' AND tipo = 'PC'
            ) as todos_locais
            GROUP BY local
        """)
        ocupacao_atual = {row['local']: row['total'] for row in cur.fetchall()}
        
        # Somar com contador temporário
        for slot, count in contador_slots_temp.items():
            ocupacao_atual[slot] = ocupacao_atual.get(slot, 0) + count
        
        # Verificar se o projeto+peça tem tamanho "GG" na tabela arquivos_pc
        # Buscar projeto da peça atual (assumindo que está disponível no contexto)
        projeto_atual = ''
        try:
            # Tentar buscar projeto da última peça processada
            cur.execute("""
                SELECT projeto FROM public.apontamento_pplug_jarinu 
                WHERE item = %s 
                ORDER BY data DESC LIMIT 1
            """, (tipo_peca,))
            projeto_result = cur.fetchone()
            if projeto_result:
                projeto_atual = projeto_result['projeto']
        except:
            pass
        
        cur.execute("""
            SELECT tamanho_peca FROM public.arquivos_pc 
            WHERE projeto = %s AND peca = %s AND tamanho_peca = 'GG'
            LIMIT 1
        """, (projeto_atual, tipo_peca))
        tem_tamanho_gg = cur.fetchone() is not None
        
        # Definir slots permitidos por tipo
        if tem_tamanho_gg:
            # Peças com tamanho "GG" são exclusivas para slots 1-3
            slots_permitidos = [f'SLOT {i}' for i in range(1, 4)]
        elif tipo_peca in ['TSP', 'TSA', 'TSC', 'TSB', 'PBS', 'VGA']:
            # Peças tamanho G: slots 4-40 e 81-117
            slots_permitidos = [f'SLOT {i}' for i in range(4, 41)] + [f'SLOT {i}' for i in range(81, 118)]
        elif tipo_peca in ['PDE', 'PDD', 'PTE', 'PTD', 'TME', 'TMD']:
            # Slots específicos: 41-80 e 118-157
            slots_permitidos = [f'SLOT {i}' for i in range(41, 81)] + [f'SLOT {i}' for i in range(118, 158)]
        elif tipo_peca in ['FTE', 'FTD', 'QTD', 'QTE', 'QDD', 'QDE', 'FDD', 'FDE', 'CBE', 'CBD']:
            # Slots 158-273
            slots_permitidos = [f'SLOT {i}' for i in range(158, 274)]
        else:
            # Peças não categorizadas - usar slots para peças tamanho G
            slots_permitidos = [f'SLOT {i}' for i in range(4, 41)] + [f'SLOT {i}' for i in range(81, 118)]
        
        # Regra especial para peças CBD e CBE (4 camadas)
        if tipo_peca in ['CBD', 'CBE']:
            print(f"DEBUG SLOT: Aplicando regra especial para peça {tipo_peca} (4 camadas)")
            
            # Primeiro, buscar slots vazios
            for slot in slots_permitidos:
                if slot in slots_info:
                    ocupado = ocupacao_atual.get(slot, 0)
                    
                    if ocupado == 0:  # Slot vazio
                        contador_slots_temp[slot] = contador_slots_temp.get(slot, 0) + 1
                        print(f"DEBUG SLOT: Peça {tipo_peca} alocada em slot vazio {slot}")
                        return slot, 'SLOT'
            
            # Se não encontrou slot vazio, buscar slots com apenas 1 peça
            for slot in slots_permitidos:
                if slot in slots_info:
                    ocupado = ocupacao_atual.get(slot, 0)
                    
                    if ocupado == 1:  # Slot com apenas 1 peça
                        contador_slots_temp[slot] = contador_slots_temp.get(slot, 0) + 1
                        print(f"DEBUG SLOT: Peça {tipo_peca} alocada em slot com 1 peça {slot} (ocupação após: 2)")
                        return slot, 'SLOT'
            
            # Se não encontrou slot vazio nem com 1 peça, não alocar
            print(f"DEBUG SLOT: Peça {tipo_peca} não pode ser alocada - não há slots vazios ou com apenas 1 peça")
            return None, None
        
        # Lógica normal para outras peças
        for slot in slots_permitidos:
            if slot in slots_info:
                limite = slots_info[slot]
                ocupado = ocupacao_atual.get(slot, 0)
                disponivel = limite - ocupado
                
                print(f"DEBUG SLOT: {slot} - Limite: {limite}, Ocupado: {ocupado}, Disponível: {disponivel}")
                
                if disponivel > 0:  # Tem espaço disponível
                    contador_slots_temp[slot] = contador_slots_temp.get(slot, 0) + 1
                    print(f"DEBUG SLOT: Selecionado {slot} (ocupação após: {ocupado + 1}/{limite})")
                    return slot, 'SLOT'
                else:
                    print(f"DEBUG SLOT: {slot} está cheio ({ocupado}/{limite})")
        
        # Se chegou aqui, todos os slots estão cheios
        print(f"DEBUG SLOT: Todos os slots para {tipo_peca} estão cheios!")
        return None, None
        
    except Exception as e:
        print(f"DEBUG: Erro na sugestão: {e}")
        import traceback
        traceback.print_exc()
        return None, None

@app.route('/api/adicionar-peca-manual', methods=['POST'])
def adicionar_peca_manual():
    global contador_slots_temp
    contador_slots_temp = {}  # Limpar contador no início de cada operação
    
    dados = request.get_json()
    op = dados.get('op', '').strip()
    peca = dados.get('peca', '').strip()
    projeto = dados.get('projeto', '').strip()
    veiculo = dados.get('veiculo', '').strip()
    sensor_input = dados.get('sensor', '').strip()
    # Para PBS, usar sensor informado; para outras peças, sempre '1'
    sensor = sensor_input if peca == 'PBS' and sensor_input else '1'
    
    if not all([op, peca, projeto, veiculo]):
        return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios'})
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Sugerir local com contador limpo
        local_sugerido, rack_sugerido = sugerir_local_armazenamento(peca, set(), conn)
        
        if local_sugerido is None:
            conn.close()
            return jsonify({'success': False, 'message': f'Não há slots disponíveis para a peça {peca}. Todos os slots estão cheios!'})
        
        # Usar o sensor informado pelo usuário diretamente
        sensor_busca = sensor if sensor and sensor not in ['nan', 'NaN', 'None', '', '1'] else '1'
        
        print(f"DEBUG MANUAL: Buscando arquivo para projeto='{projeto}', peca='{peca}', sensor_original='{sensor}', sensor_busca='{sensor_busca}'")
        
        # Buscar arquivo com sensor exato primeiro
        cur.execute("""
            SELECT nome_peca FROM public.arquivos_pc
            WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
            AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
            AND UPPER(TRIM(CAST(sensor AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
            ORDER BY id DESC
            LIMIT 1
        """, (str(projeto), str(peca), str(sensor_busca)))
        
        arquivo_result = cur.fetchone()
        print(f"DEBUG MANUAL: Busca por sensor exato '{sensor_busca}': {arquivo_result}")
        
        # Se não encontrou com sensor exato, buscar por nome_peca que contenha o sensor
        if not arquivo_result:
            cur.execute("""
                SELECT nome_peca FROM public.arquivos_pc
                WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
                AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
                AND nome_peca LIKE %s
                ORDER BY id DESC
                LIMIT 1
            """, (str(projeto), str(peca), f'%_{sensor_busca}'))
            arquivo_result = cur.fetchone()
            print(f"DEBUG MANUAL: Busca por nome com sensor '{sensor_busca}': {arquivo_result}")
        
        # Se ainda não encontrou, buscar qualquer arquivo da peça
        if not arquivo_result:
            cur.execute("""
                SELECT nome_peca FROM public.arquivos_pc
                WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
                AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
                ORDER BY id DESC
                LIMIT 1
            """, (str(projeto), str(peca)))
            arquivo_result = cur.fetchone()
            print(f"DEBUG MANUAL: Busca genérica: {arquivo_result}")
        
        print(f"DEBUG MANUAL: Resultado final: {arquivo_result}")
        arquivo_status = arquivo_result['nome_peca'] if arquivo_result else 'Sem arquivo de corte'
        
        conn.close()
        
        peca_data = {
            'op': op,
            'peca': peca,
            'projeto': projeto,
            'veiculo': veiculo,
            'local': local_sugerido,
            'sensor': sensor,
            'arquivo_status': arquivo_status
        }
        
        return jsonify({'success': True, 'peca': peca_data})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

@app.route('/api/importar-excel-pecas', methods=['POST'])
@login_required
def importar_excel_pecas():
    global contador_slots_temp
    contador_slots_temp = {}  # Limpar contador no início de cada importação
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'})
        
        # Ler Excel
        df = pd.read_excel(file, engine='openpyxl')
        
        if df.empty:
            return jsonify({'success': False, 'message': 'Arquivo vazio'})
        
        # Verificar colunas obrigatórias
        required_cols = ['OP', 'PECA', 'PROJETO', 'VEICULO']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return jsonify({'success': False, 'message': f'Colunas obrigatórias ausentes: {", ".join(missing_cols)}'})
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        pecas_processadas = []
        
        for _, row in df.iterrows():
            op = str(row['OP']).strip()
            peca = str(row['PECA']).strip()
            projeto = str(row['PROJETO']).strip()
            veiculo = str(row['VEICULO']).strip()
            sensor = str(row.get('SENSOR', '')).strip()
            
            # Tratar valores vazios/NaN do sensor
            if sensor in ['nan', 'NaN', 'None', '', '-','1']:
                sensor = '1'
            elif sensor.endswith('.0'):
                sensor = sensor[:-2]
            
            if not all([op, peca, projeto, veiculo]):
                continue
            
            # Verificar duplicatas
            cur.execute("SELECT COUNT(*) FROM public.pc_inventory WHERE op = %s AND peca = %s", (op, peca))
            if cur.fetchone()[0] > 0:
                continue
            
            cur.execute("SELECT COUNT(*) FROM public.pc_otimizadas WHERE op = %s AND peca = %s AND tipo = 'PC'", (op, peca))
            if cur.fetchone()[0] > 0:
                continue
            
            # Sugerir local com contador limpo
            local_sugerido, rack_sugerido = sugerir_local_armazenamento(peca, set(), conn)
            
            if local_sugerido is None:
                # Pular esta peça se não há slot disponível
                continue
            
            # Usar o sensor informado pelo usuário diretamente
            sensor_busca = sensor if sensor and sensor not in ['nan', 'NaN', 'None', '', '1'] else '1'
            
            print(f"DEBUG EXCEL: Buscando arquivo para projeto='{projeto}', peca='{peca}', sensor_original='{sensor}', sensor_busca='{sensor_busca}'")
            
            # Buscar arquivo com sensor exato primeiro
            cur.execute("""
                SELECT nome_peca FROM public.arquivos_pc
                WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
                AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
                AND UPPER(TRIM(CAST(sensor AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
                ORDER BY id DESC
                LIMIT 1
            """, (str(projeto), str(peca), str(sensor_busca)))
            
            arquivo_result = cur.fetchone()
            print(f"DEBUG EXCEL: Busca por sensor exato '{sensor_busca}': {arquivo_result}")
            
            # Se não encontrou com sensor exato, buscar por nome_peca que contenha o sensor
            if not arquivo_result:
                cur.execute("""
                    SELECT nome_peca FROM public.arquivos_pc
                    WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
                    AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
                    AND nome_peca LIKE %s
                    ORDER BY id DESC
                    LIMIT 1
                """, (str(projeto), str(peca), f'%_{sensor_busca}'))
                arquivo_result = cur.fetchone()
                print(f"DEBUG EXCEL: Busca por nome com sensor '{sensor_busca}': {arquivo_result}")
            
            # Se ainda não encontrou, buscar qualquer arquivo da peça
            if not arquivo_result:
                cur.execute("""
                    SELECT nome_peca FROM public.arquivos_pc
                    WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
                    AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
                    ORDER BY id DESC
                    LIMIT 1
                """, (str(projeto), str(peca)))
                arquivo_result = cur.fetchone()
                print(f"DEBUG EXCEL: Busca genérica: {arquivo_result}")
            print(f"DEBUG EXCEL: Resultado final: {arquivo_result}")
            arquivo_status = arquivo_result['nome_peca'] if arquivo_result else 'Sem arquivo de corte'
            
            peca_data = {
                'op': op,
                'peca': peca,
                'projeto': projeto,
                'veiculo': veiculo,
                'sensor': sensor,
                'local': local_sugerido,
                'rack': rack_sugerido,
                'arquivo_status': arquivo_status
            }
            
            pecas_processadas.append(peca_data)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'pecas': pecas_processadas,
            'total': len(pecas_processadas)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao processar Excel: {str(e)}'}), 500



@app.route('/api/dados')
def api_dados():
    global contador_slots_temp
    contador_slots_temp = {}  # Limpar contador no início de cada coleta
    
    lote = request.args.get('lote')
    
    print(f"DEBUG: Buscando dados - lote: {lote}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Buscar peças já existentes no estoque e otimizadas
        cur.execute("SELECT op, peca FROM public.pc_inventory")
        pecas_estoque = cur.fetchall()
        
        cur.execute("SELECT op, peca FROM public.pc_otimizadas WHERE tipo = 'PC'")
        pecas_otimizadas = cur.fetchall()
        
        # Buscar locais ocupados
        cur.execute("SELECT local FROM public.pc_inventory UNION SELECT local FROM public.pc_otimizadas WHERE tipo = 'PC'")
        locais_ocupados = {row['local'] for row in cur.fetchall() if row['local']}
        
        # Criar set para busca rápida
        pecas_existentes = {f"{row['op']}_{row['peca']}" for row in pecas_estoque}
        pecas_existentes.update({f"{row['op']}_{row['peca']}" for row in pecas_otimizadas})
        
        # Query com DISTINCT para evitar duplicatas e usar coluna veiculo diretamente
        query = """
            SELECT DISTINCT p.op, p.peca, p.projeto, p.sensor, p.id_lote, p.data_geracao,
                   COALESCE(p.veiculo, CONCAT(f.marca, ' ', f.modelo), p.tipo_programacao) as veiculo
            FROM public.plano_controle_corte_vidro2 p
            LEFT JOIN public.ficha_tecnica_veiculos f ON p.projeto = f.codigo_veiculo
            WHERE (p.pc_cortado IS NULL OR p.pc_cortado = '' OR p.pc_cortado != 'CORTADO')
            AND (p.etapa_baixa IS NULL OR p.etapa_baixa = '' OR p.etapa_baixa = 'INSPECAO FINAL' OR p.etapa_baixa = 'RT-RP')
        """
        params = []
        
        if lote:
            query += " AND p.id_lote = %s"
            params.append(lote)
        
        query += " ORDER BY p.data_geracao DESC"
        
        print(f"DEBUG: Query: {query}")
        print(f"DEBUG: Params: {params}")
        
        cur.execute(query, params)
        dados_banco = cur.fetchall()
        
        print(f"DEBUG: Encontrados {len(dados_banco)} registros no banco")
        
        # Não atualizar status na coleta - apenas quando otimizar
        
        # Processar dados do banco com verificação de duplicatas
        dados_filtrados = []
        pecas_processadas = set()  # Para evitar duplicatas no processamento
        
        for row in dados_banco:
            try:
                chave_peca = f"{row['op']}_{row['peca']}"
                
                # Verificar se já processamos esta peça
                if chave_peca in pecas_processadas:
                    continue
                    
                if chave_peca not in pecas_existentes:
                    pecas_processadas.add(chave_peca)  # Marcar como processada
                    # Aplicar lógica de sugestão
                    local_sugerido, rack_sugerido = sugerir_local_armazenamento(row['peca'], locais_ocupados, conn)
                    
                    # Se não há slot disponível, pular esta peça
                    if local_sugerido is None:
                        continue
                    
                    # Verificar se existe arquivo de corte e buscar nome com sensor correto
                    sensor_busca = str(row['sensor']) if row['sensor'] and str(row['sensor']).strip() != '-' else '1'
                    print(f"DEBUG ARQUIVO: Buscando arquivo para projeto='{row['projeto']}', peca='{row['peca']}', sensor='{sensor_busca}'")
                    
                    # Buscar arquivo com sensor exato na coluna sensor
                    cur.execute("""
                        SELECT nome_peca FROM public.arquivos_pc
                        WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
                        AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
                        AND UPPER(TRIM(CAST(sensor AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
                        ORDER BY id DESC
                        LIMIT 1
                    """, (str(row['projeto']) if row['projeto'] else '', str(row['peca']) if row['peca'] else '', sensor_busca))
                    
                    arquivo_result = cur.fetchone()
                    
                    # Se não encontrou com sensor exato, buscar qualquer arquivo da peça
                    if not arquivo_result:
                        cur.execute("""
                            SELECT nome_peca FROM public.arquivos_pc
                            WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
                            AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
                            ORDER BY id DESC
                            LIMIT 1
                        """, (str(row['projeto']) if row['projeto'] else '', str(row['peca']) if row['peca'] else ''))
                        arquivo_result = cur.fetchone()
                    
                    print(f"DEBUG ARQUIVO: Resultado encontrado: {arquivo_result}")
                    arquivo_status = arquivo_result['nome_peca'] if arquivo_result else 'Sem arquivo de corte'
                    
                    # Converter lote VD para PC
                    lote_vd = str(row['id_lote']) if row['id_lote'] else ''
                    lote_pc = lote_vd.replace('VD', 'PC') if lote_vd else ''
                    
                    item = {
                        'op': str(row['op']) if row['op'] else '',
                        'peca': str(row['peca']) if row['peca'] else '',
                        'projeto': str(row['projeto']) if row['projeto'] else '',
                        'veiculo': str(row['veiculo']) if row['veiculo'] else '',
                        'local': local_sugerido or '',
                        'rack': rack_sugerido or '',
                        'arquivo_status': arquivo_status,
                        'sensor': str(row['sensor']) if row['sensor'] else '',
                        'lote_vd': lote_vd,
                        'lote_pc': lote_pc
                    }
                    
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
        cur.execute("""
            SELECT id, op, peca, projeto, veiculo, local, sensor, camada
            FROM public.pc_inventory
            ORDER BY id DESC
        """)
        dados = cur.fetchall()
        conn.close()
        
        resultado = []
        for row in dados:
            resultado.append({
                'id': row['id'],
                'op': row['op'] or '',
                'peca': row['peca'] or '',
                'projeto': row['projeto'] or '',
                'veiculo': row['veiculo'] or '',
                'local': row['local'] or '',
                'sensor': row['sensor'] or '',
                'camada': row['camada'] or ''
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
    cur.execute("SELECT id, op, peca, projeto, veiculo, local FROM public.pc_inventory ORDER BY id DESC")
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
        
        # Não verificar duplicatas gerais aqui - será verificado por camada durante inserção
        
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
            CREATE TABLE IF NOT EXISTS public.pc_otimizadas (
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
                tipo TEXT DEFAULT 'PC',
                camada TEXT
            )
        """)
        
        # Adicionar colunas se não existirem
        try:
            cur.execute("ALTER TABLE public.pc_otimizadas ADD COLUMN IF NOT EXISTS tipo TEXT DEFAULT 'PC'")
            cur.execute("ALTER TABLE public.pc_otimizadas ADD COLUMN IF NOT EXISTS camada TEXT")
            cur.execute("ALTER TABLE public.pc_otimizadas ADD COLUMN IF NOT EXISTS sensor TEXT")
        except:
            pass
        
        total_inseridas = 0
        
        # Inserir cada peça selecionada quebrada por camadas
        for peca in pecas_selecionadas:
            print(f"DEBUG: Processando peça {peca['peca']}")
            
            # Buscar todas as camadas da peça na tabela pc_camadas
            cur.execute("""
                SELECT * FROM public.pc_camadas 
                WHERE projeto = %s AND peca = %s
            """, (peca.get('projeto', ''), peca['peca']))
            
            camadas_result = cur.fetchone()
            print(f"DEBUG: Resultado camadas para peça {peca['peca']}: {camadas_result}")
            
            if camadas_result:
                # Processar apenas colunas específicas de camadas conhecidas
                colunas_camadas_conhecidas = ['l3', 'l3_b', 'l4', 'l5', 'l6', 'l7', 'l8']
                colunas_encontradas = [col for col in camadas_result.keys() if col in colunas_camadas_conhecidas]
                
                for coluna in colunas_encontradas:
                    valor_camada = camadas_result[coluna]
                    # Processar apenas se existir e for diferente de "-" ou vazio
                    if valor_camada and str(valor_camada).strip() not in ['-', '', 'None', 'NULL', 'null']:
                        try:
                            quantidade_camada = int(float(str(valor_camada)))
                            if quantidade_camada <= 0:
                                continue
                        except (ValueError, TypeError):
                            quantidade_camada = 1
                        
                        # Inserir múltiplas linhas baseado na quantidade da camada
                        for i in range(quantidade_camada):
                            # Verificar duplicata antes de inserir (considerando índice da quantidade)
                            camada_id = f"{coluna.upper()}_{i+1:02d}" if quantidade_camada > 1 else coluna.upper()
                            
                            cur.execute("SELECT COUNT(*) FROM public.pc_inventory WHERE op = %s AND peca = %s AND camada = %s", (peca['op'], peca['peca'], camada_id))
                            if cur.fetchone()[0] > 0:
                                print(f"DEBUG: Peça {peca['peca']} OP {peca['op']} camada {camada_id} já existe no estoque, pulando")
                                continue
                            
                            cur.execute("SELECT COUNT(*) FROM public.pc_otimizadas WHERE op = %s AND peca = %s AND camada = %s AND tipo = 'PC'", (peca['op'], peca['peca'], camada_id))
                            if cur.fetchone()[0] > 0:
                                print(f"DEBUG: Peça {peca['peca']} OP {peca['op']} camada {camada_id} já existe nas otimizadas, pulando")
                                continue
                        
                            cur.execute("""
                                INSERT INTO public.pc_otimizadas (op, peca, projeto, veiculo, sensor, local, rack, user_otimizacao, tipo, camada, lote_vd, lote_pc, data_corte)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                peca['op'],
                                peca['peca'],
                                peca.get('projeto', ''),
                                peca['veiculo'],
                                peca.get('sensor', ''),
                                peca['local'],
                                peca['rack'],
                                current_user.username,
                                'PC',
                                camada_id,
                                peca.get('lote_vd', ''),
                                peca.get('lote_pc', ''),
                                peca.get('data_corte')
                            ))
                            total_inseridas += 1
                            print(f"DEBUG: Inserida linha {camada_id} ({i+1}/{quantidade_camada})")
            else:
                print(f"DEBUG: Nenhuma camada encontrada para {peca['peca']}, inserindo sem camada")
                # Se não encontrou camadas, inserir como antes (sem camada)
                # Verificar duplicata antes de inserir
                cur.execute("SELECT COUNT(*) FROM public.pc_inventory WHERE op = %s AND peca = %s AND (camada IS NULL OR camada = '')", (peca['op'], peca['peca']))
                if cur.fetchone()[0] > 0:
                    print(f"DEBUG: Peça {peca['peca']} OP {peca['op']} sem camada já existe no estoque, pulando")
                    continue
                
                cur.execute("SELECT COUNT(*) FROM public.pc_otimizadas WHERE op = %s AND peca = %s AND (camada IS NULL OR camada = '') AND tipo = 'PC'", (peca['op'], peca['peca']))
                if cur.fetchone()[0] > 0:
                    print(f"DEBUG: Peça {peca['peca']} OP {peca['op']} sem camada já existe nas otimizadas, pulando")
                    continue
                
                cur.execute("""
                    INSERT INTO public.pc_otimizadas (op, peca, projeto, veiculo, sensor, local, rack, user_otimizacao, tipo, lote_vd, lote_pc, data_corte)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    peca['op'],
                    peca['peca'],
                    peca.get('projeto', ''),
                    peca['veiculo'],
                    peca.get('sensor', ''),
                    peca['local'],
                    peca['rack'],
                    current_user.username,
                    'PC',
                    peca.get('lote_vd', ''),
                    peca.get('lote_pc', ''),
                    peca.get('data_corte')
                ))
                total_inseridas += 1
        
        # Atualizar status para PROGRAMADO na tabela plano_controle_corte_vidro2
        for peca in pecas_selecionadas:
            cur.execute("""
                UPDATE public.plano_controle_corte_vidro2 
                SET pc_cortado = 'PROGRAMADO' 
                WHERE op = %s AND peca = %s
            """, (peca['op'], peca['peca']))
        
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
            SELECT id, op, peca, projeto, veiculo, local, cortada, user_otimizacao, data_corte, sensor, camada
            FROM public.pc_otimizadas
            WHERE tipo = 'PC'
            ORDER BY id DESC
        """)
        dados = cur.fetchall()
        conn.close()
        
        resultado = []
        for row in dados:
            item = dict(row)
            if item.get('data_corte'):
                item['data_corte'] = item['data_corte'].strftime('%d/%m/%Y') if item['data_corte'] else ''
            item['sensor'] = item.get('sensor', '') or ''
            item['camada'] = item.get('camada', '') or ''
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
            SELECT * FROM public.pc_otimizadas 
            WHERE id IN ({placeholders}) AND tipo = 'PC'
        """, ids)
        pecas = cur.fetchall()
        
        # Inserir na tabela pc_exit com motivo
        for peca in pecas:
            cur.execute("""
                INSERT INTO public.pc_exit (op, peca, projeto, veiculo, sensor, local, usuario, data, motivo, lote_vd, lote_pc)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                peca['op'],
                peca['peca'],
                peca['projeto'],
                peca['veiculo'],
                peca.get('sensor', ''),
                peca['local'],
                current_user.username,
datetime.now(),
                f'EXCLUSÃO: {motivo}',
                peca.get('lote_vd', ''),
                peca.get('lote_pc', '')
            ))
        
        # Remover das otimizadas
        cur.execute(f"DELETE FROM public.pc_otimizadas WHERE id IN ({placeholders})", ids)
        
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
            SELECT * FROM public.pc_otimizadas 
            WHERE id IN ({placeholders}) AND tipo = 'PC'
        """, ids)
        pecas = cur.fetchall()
        
        # Verificar duplicatas e inserir no estoque
        for peca in pecas:
            # Verificar se já existe no estoque (considerando camada se existir)
            if peca.get('camada'):
                cur.execute("SELECT COUNT(*) FROM public.pc_inventory WHERE op = %s AND peca = %s AND camada = %s", (peca['op'], peca['peca'], peca['camada']))
                if cur.fetchone()[0] > 0:
                    # Se já existe, permitir entrada mesmo assim (forçar entrada)
                    print(f"DEBUG: Peça {peca['peca']} OP {peca['op']} camada {peca['camada']} já existe, mas forçando entrada")
            else:
                cur.execute("SELECT COUNT(*) FROM public.pc_inventory WHERE op = %s AND peca = %s AND (camada IS NULL OR camada = '')", (peca['op'], peca['peca']))
                if cur.fetchone()[0] > 0:
                    print(f"DEBUG: Peça {peca['peca']} OP {peca['op']} sem camada já existe, mas forçando entrada")
            
            cur.execute("""
                INSERT INTO public.pc_inventory (op, peca, projeto, veiculo, sensor, local, data, usuario, lote_vd, lote_pc, camada)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s, %s)
            """, (
                peca['op'],
                peca['peca'],
                peca['projeto'],
                peca['veiculo'],
                peca.get('sensor', ''),
                peca['local'],
                current_user.username,
                peca.get('lote_vd', ''),
                peca.get('lote_pc', ''),
                peca.get('camada', '')
            ))
        
        # Verificar se todas as peças do lote estão no estoque e atualizar status
        lotes_processados = set()
        for peca in pecas:
            lote_vd = peca.get('lote_vd', '')
            if lote_vd and lote_vd not in lotes_processados:
                lotes_processados.add(lote_vd)
                
                # Contar total de peças do lote na tabela origem
                cur.execute("""
                    SELECT COUNT(*) FROM public.plano_controle_corte_vidro2 
                    WHERE id_lote = %s
                """, (lote_vd,))
                total_lote = cur.fetchone()[0]
                
                # Contar peças do lote no estoque
                cur.execute("""
                    SELECT COUNT(*) FROM public.pc_inventory 
                    WHERE lote_vd = %s
                """, (lote_vd,))
                total_estoque = cur.fetchone()[0]
                
                # Se todas as peças do lote estão no estoque, marcar como CORTADO
                if total_estoque >= total_lote:
                    cur.execute("""
                        UPDATE public.plano_controle_corte_vidro2 
                        SET pc_cortado = 'CORTADO' 
                        WHERE id_lote = %s
                    """, (lote_vd,))
        
        # Log da ação
        cur.execute("""
            INSERT INTO public.pc_logs (usuario, acao, detalhes)
            VALUES (%s, %s, %s)
        """, (
            current_user.username,
            'ENVIAR_ESTOQUE',
            f'Enviou {len(pecas)} peça(s) para o estoque'
        ))
        
        # Remover da tabela de otimizadas
        placeholders = ','.join(['%s'] * len(ids))
        cur.execute(f"DELETE FROM public.pc_otimizadas WHERE id IN ({placeholders})", ids)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{len(pecas)} peça(s) enviada(s) para o estoque com sucesso!'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/remover-estoque', methods=['POST'])
@login_required
def remover_estoque():
    dados = request.get_json()
    ids = dados.get('ids', [])
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    for id_item in ids:
        cur.execute("SELECT * FROM public.pc_inventory WHERE id = %s", (id_item,))
        peca = cur.fetchone()
        
        if peca:
            cur.execute("""
                INSERT INTO public.pc_exit (op, peca, projeto, veiculo, sensor, local, usuario, data, motivo, lote_vd, lote_pc)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s)
            """, (
                peca['op'],
                peca['peca'],
                peca.get('projeto', ''),
                peca.get('veiculo', ''),
                peca.get('sensor', ''),
                peca['local'],
                current_user.username,
                'SAÍDA DO ESTOQUE',
                peca.get('lote_vd', ''),
                peca.get('lote_pc', '')
            ))
            
            cur.execute("DELETE FROM public.pc_inventory WHERE id = %s", (id_item,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'{len(ids)} peça(s) removida(s) do estoque!'})

@app.route('/api/arquivos')
@login_required
def api_arquivos():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Adicionar coluna sensor se não existir
        try:
            cur.execute("ALTER TABLE public.arquivos_pc ADD COLUMN IF NOT EXISTS sensor TEXT")
            conn.commit()
        except:
            pass
        
        # Buscar dados
        cur.execute("SELECT * FROM public.arquivos_pc ORDER BY id DESC")
        dados = cur.fetchall()
        conn.close()
        
        # Processar dados para garantir que sensor seja extraído do nome se não existir
        resultado = []
        for row in dados:
            item = dict(row)
            if not item.get('sensor') and item.get('nome_peca'):
                # Extrair sensor do nome do arquivo se não estiver preenchido
                nome_peca = item['nome_peca']
                if '_' in nome_peca:
                    item['sensor'] = nome_peca.split('_')[-1]
                else:
                    item['sensor'] = 'A'
            resultado.append(item)
        
        return jsonify(resultado)
        
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
        sensor = dados.get('sensor', '').strip()
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
        
        # Adicionar coluna sensor se não existir
        try:
            cur.execute("ALTER TABLE public.arquivos_pc ADD COLUMN IF NOT EXISTS sensor TEXT")
            conn.commit()
        except:
            pass
        
        cur.execute("""
            INSERT INTO public.arquivos_pc (projeto, peca, nome_peca, camada, espessura, quantidade, sensor)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (projeto, peca, nome_peca, camada, espessura_val, quantidade_val, sensor))
        
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
        sensor = dados.get('sensor', '').strip()
        espessura = dados.get('espessura') or 0.5
        quantidade = dados.get('quantidade') or 1
        
        if not all([projeto, peca, nome_peca, camada]):
            response = jsonify({'success': False, 'message': 'Projeto, peça, nome da peça e camada são obrigatórios'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Adicionar coluna sensor se não existir
        try:
            cur.execute("ALTER TABLE public.arquivos_pc ADD COLUMN IF NOT EXISTS sensor TEXT")
            conn.commit()
        except:
            pass
        
        cur.execute("""
            UPDATE public.arquivos_pc 
            SET projeto = %s, peca = %s, nome_peca = %s, camada = %s, 
                espessura = %s, quantidade = %s, sensor = %s
            WHERE id = %s
        """, (projeto, peca, nome_peca, camada, float(espessura), int(quantidade), sensor, arquivo_id))
        
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
        
        cur.execute("DELETE FROM public.arquivos_pc WHERE id = %s", (arquivo_id,))
        
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
        cur.execute("SELECT id, local, status, limite FROM public.pc_locais ORDER BY id")
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
            FROM (
                SELECT local FROM public.pc_inventory WHERE local IS NOT NULL AND local != ''
                UNION ALL
                SELECT local FROM public.pc_otimizadas WHERE local IS NOT NULL AND local != '' AND tipo = 'PC'
            ) as todos_locais
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
        
        cur.execute("""
            SELECT op, peca, projeto, veiculo, 'Estoque' as origem FROM public.pc_inventory WHERE local = %s
            UNION ALL
            SELECT op, peca, projeto, veiculo, 'Otimizadas' as origem FROM public.pc_otimizadas WHERE local = %s AND tipo = 'PC'
            ORDER BY origem, op
        """, (local, local))
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
            CREATE TABLE IF NOT EXISTS public.pc_locais (
                id SERIAL PRIMARY KEY,
                local TEXT,
                status TEXT DEFAULT 'Ativo',
                limite TEXT
            )
        """)
        
        # Adicionar coluna email na tabela users_pc se não existir
        try:
            cur.execute("ALTER TABLE public.users_pc ADD COLUMN IF NOT EXISTS email TEXT")
            conn.commit()
        except:
            pass
        

        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.pc_inventory (
                id SERIAL PRIMARY KEY,
                op_pai TEXT,
                op TEXT,
                peca TEXT,
                projeto TEXT,
                veiculo TEXT,
                local TEXT,
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario TEXT
            )
        """)
        
        # Adicionar colunas se não existirem
        try:
            cur.execute("ALTER TABLE public.pc_inventory ADD COLUMN IF NOT EXISTS data TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            cur.execute("ALTER TABLE public.pc_inventory ADD COLUMN IF NOT EXISTS usuario TEXT")
            cur.execute("ALTER TABLE public.pc_inventory ADD COLUMN IF NOT EXISTS sensor TEXT")
            cur.execute("ALTER TABLE public.pc_inventory ADD COLUMN IF NOT EXISTS camada TEXT")
            cur.execute("ALTER TABLE public.pc_inventory ADD COLUMN IF NOT EXISTS lote_vd TEXT")
            cur.execute("ALTER TABLE public.pc_inventory ADD COLUMN IF NOT EXISTS lote_pc TEXT")
            conn.commit()
        except:
            pass
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.pc_exit (
                id SERIAL PRIMARY KEY,
                op_pai TEXT,
                op TEXT,
                peca TEXT,
                projeto TEXT,
                veiculo TEXT,
                local TEXT,
                usuario TEXT,
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                motivo TEXT
            )
        """)
        
        # Criar tabela pc_baixas se não existir
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.pc_baixas (
                id SERIAL PRIMARY KEY,
                op TEXT,
                peca TEXT,
                projeto TEXT,
                veiculo TEXT,
                sensor TEXT,
                motivo_baixa TEXT,
                data_baixa DATE,
                status TEXT DEFAULT 'PENDENTE',
                usuario_apontamento TEXT,
                processado_por TEXT,
                data_processamento TIMESTAMP,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Adicionar colunas se não existirem na tabela pc_baixas
        try:
            cur.execute("ALTER TABLE public.pc_baixas ADD COLUMN IF NOT EXISTS veiculo TEXT")
            cur.execute("ALTER TABLE public.pc_baixas ADD COLUMN IF NOT EXISTS sensor TEXT")
            cur.execute("ALTER TABLE public.pc_baixas ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'PENDENTE'")
            cur.execute("ALTER TABLE public.pc_baixas ADD COLUMN IF NOT EXISTS processado_por TEXT")
            cur.execute("ALTER TABLE public.pc_baixas ADD COLUMN IF NOT EXISTS data_processamento TIMESTAMP")
            cur.execute("ALTER TABLE public.pc_baixas ADD COLUMN IF NOT EXISTS data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            conn.commit()
        except:
            pass
        
        # Verificar se já existem slots
        cur.execute("SELECT COUNT(*) FROM public.pc_locais WHERE local LIKE 'SLOT%'")
        count = cur.fetchone()[0]
        
        if count == 0:
            # Criar slots de 1 a 169
            for i in range(1, 170):
                local = f"SLOT {i}"
                cur.execute("""
                    INSERT INTO public.pc_locais (local, status, limite)
                    VALUES (%s, %s, %s)
                """, (local, 'Ativo', '6'))

            conn.commit()
            print("Slots populados com sucesso: SLOT 1 até SLOT 169")
        
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
        cur.execute("SELECT id FROM public.pc_locais WHERE local = %s", (local,))
        if cur.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Local já existe'})

        cur.execute("""
            INSERT INTO public.pc_locais (local, status, limite)
            VALUES (%s, %s, %s)
        """, (local, 'Ativo', nome))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Local adicionado com sucesso!'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao adicionar local: {str(e)}'})

@app.route('/api/editar-local', methods=['PUT'])
@login_required
def editar_local():
    try:
        data = request.get_json()
        local = data.get('local')
        limite = data.get('limite')

        if not local or not limite:
            return jsonify({'success': False, 'message': 'Local e limite são obrigatórios'})

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE public.pc_locais 
            SET limite = %s 
            WHERE local = %s
        """, (str(limite), local))

        if cur.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'message': 'Local não encontrado'})

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': f'Limite do local {local} alterado para {limite}!'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao editar local: {str(e)}'})

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
            UPDATE public.pc_locais 
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
        cur.execute("SELECT id, op, peca, projeto, veiculo, local, usuario, data FROM public.pc_exit ORDER BY id DESC LIMIT 100")
        dados = cur.fetchall()
        conn.close()
        
        resultado = []
        for row in dados:
            item = dict(row)
            if item.get('data'):
                item['data'] = item['data'].strftime('%d/%m/%Y %H:%M')
            resultado.append(item)
        
        return jsonify(resultado)
    except Exception as e:
        print(f"Erro na API saidas: {e}")
        return jsonify([])

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
        contador_xml = {}  # Controlar contador por OP+PROJETO+PEÇA
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for peca_data in pecas_selecionadas:
                projeto = peca_data.get('projeto', '')
                peca_codigo = peca_data['peca']
                op = peca_data['op']
                sensor = peca_data.get('sensor', '')
                
                # Buscar todas as camadas da peça na tabela pc_camadas
                cur.execute("""
                    SELECT * FROM public.pc_camadas 
                    WHERE projeto = %s AND peca = %s
                """, (projeto, peca_codigo))
                
                camadas_result = cur.fetchone()
                print(f"DEBUG XML: Camadas encontradas para {projeto} {peca_codigo}: {dict(camadas_result) if camadas_result else 'Nenhuma'}")
                
                # Verificar se há peças especiais definidas
                pecas_para_gerar = [peca_codigo]  # Sempre incluir a peça original
                if camadas_result and camadas_result.get('pecas_especiais'):
                    pecas_especiais_str = camadas_result['pecas_especiais'].strip()
                    if pecas_especiais_str and pecas_especiais_str != '-':
                        # Parse do formato "TSA - TSB" -> ['TSA', 'TSB']
                        pecas_especiais = [p.strip() for p in pecas_especiais_str.split('-') if p.strip()]
                        pecas_para_gerar = pecas_especiais  # Usar as peças especiais ao invés da original
                        print(f"DEBUG XML: Peças especiais encontradas: {pecas_especiais}")
                
                print(f"DEBUG XML: Peças que serão processadas: {pecas_para_gerar}")
                
                # Processar cada peça (original ou especiais)
                for peca_atual in pecas_para_gerar:
                    print(f"DEBUG XML: Processando peça: {peca_atual}")
                    
                    # Lista para armazenar as camadas válidas desta peça
                    camadas_para_processar = []
                    
                    if camadas_result:
                        # Processar apenas colunas específicas de camadas conhecidas
                        colunas_camadas_conhecidas = ['l3', 'l3_b', 'l4', 'l5', 'l6', 'l7', 'l8']
                        colunas_encontradas = [col for col in camadas_result.keys() if col in colunas_camadas_conhecidas]
                        print(f"DEBUG XML: Colunas de camadas válidas encontradas: {colunas_encontradas}")
                        
                        for coluna in colunas_encontradas:
                            valor_camada = camadas_result[coluna]
                            print(f"DEBUG XML: Coluna {coluna} = '{valor_camada}' (tipo: {type(valor_camada)})")
                            # Processar apenas se existir e for diferente de "-" ou vazio
                            if valor_camada and str(valor_camada).strip() not in ['-', '', 'None', 'NULL', 'null']:
                                try:
                                    quantidade = int(float(str(valor_camada)))
                                    if quantidade > 0:
                                        # Gerar apenas 1 XML por camada, independente da quantidade
                                        camadas_para_processar.append((coluna.upper(), '01', 1, quantidade))
                                        print(f"DEBUG XML: Camada {coluna.upper()} adicionada (quantidade: {quantidade})")
                                except (ValueError, TypeError):
                                    # Se não conseguir converter para número, tratar como 1
                                    camadas_para_processar.append((coluna.upper(), '01', 1, 1))
                            else:
                                print(f"DEBUG XML: Camada {coluna} ignorada (valor inválido)")
                        
                        print(f"DEBUG XML: Total de camadas para processar: {len(camadas_para_processar)}")
                
                    # Se não encontrou camadas válidas, tentar buscar arquivo genérico
                    if not camadas_para_processar:
                        print(f"DEBUG XML: Nenhuma camada válida encontrada para {projeto} {peca_atual}, buscando arquivo genérico")
                        # Buscar qualquer arquivo do projeto/peça
                        cur.execute("""
                            SELECT nome_peca, espessura FROM public.arquivos_pc
                            WHERE projeto = %s AND peca = %s
                            ORDER BY id DESC LIMIT 1
                        """, (projeto, peca_atual))
                        
                        arquivo_generico = cur.fetchone()
                        
                        if arquivo_generico:
                            # Adicionar como camada genérica com 4 valores
                            camadas_para_processar.append(('GENERICO', '01', 1, 1))
                            print(f"DEBUG XML: Arquivo genérico encontrado, adicionado como GENERICO")
                        else:
                            if camadas_result:
                                # Mostrar todas as camadas encontradas no log
                                colunas_camadas = ['l3', 'l3_b']
                                camadas_info = ', '.join([f"{col}: {camadas_result.get(col, 'N/A')}" for col in colunas_camadas])
                                xmls_nao_gerados.append(f"{projeto} {peca_atual} - Sem camadas válidas ({camadas_info})")
                            else:
                                xmls_nao_gerados.append(f"{projeto} {peca_atual} - Não encontrado na tabela pc_camadas nem arquivos_pc")
                            continue
                
                    # Buscar todos os arquivos disponíveis para a peça atual
                    sensor_peca = peca_data.get('sensor', '') or ''
                    
                    # Tratar sensor '-' ou inválido
                    if sensor_peca in ['-', '', 'None', 'NULL', 'null']:
                        # Buscar sensor do PBS da mesma OP
                        cur.execute("""
                            SELECT sensor FROM public.plano_controle_corte_vidro2
                            WHERE op = %s AND peca = 'PBS' AND sensor IS NOT NULL AND sensor != '' AND sensor != '-'
                            LIMIT 1
                        """, (op,))
                        pbs_sensor = cur.fetchone()
                        sensor_peca = pbs_sensor['sensor'] if pbs_sensor else '1'
                    
                    # Buscar arquivos com sensor exato primeiro
                    print(f"DEBUG XML: Buscando arquivos para projeto={projeto}, peca={peca_atual}, sensor={sensor_peca}")
                    
                    cur.execute("""
                        SELECT nome_peca, espessura FROM public.arquivos_pc
                        WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
                        AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
                        AND UPPER(TRIM(CAST(sensor AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
                        ORDER BY id DESC
                    """, (str(projeto), str(peca_atual), str(sensor_peca)))
                    
                    arquivos_disponiveis = cur.fetchall()
                    
                    # Se não encontrou com sensor exato, buscar por nome_peca que contenha o sensor
                    if not arquivos_disponiveis:
                        cur.execute("""
                            SELECT nome_peca, espessura FROM public.arquivos_pc
                            WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
                            AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
                            AND nome_peca LIKE %s
                            ORDER BY id DESC
                        """, (str(projeto), str(peca_atual), f'%_{sensor_peca}'))
                        arquivos_disponiveis = cur.fetchall()
                    
                    print(f"DEBUG XML: Encontrados {len(arquivos_disponiveis)} arquivos para {projeto} {peca_atual}")
                    
                    if not arquivos_disponiveis:
                        xmls_nao_gerados.append(f"{projeto} {peca_atual} - Nenhum arquivo encontrado na tabela arquivos_pc")
                        continue
                
                    # Gerar XML para cada camada válida usando arquivos correspondentes
                    for idx, camada_info in enumerate(camadas_para_processar):
                        camada_nome, numero_sequencia, item_num, total_items = camada_info
                        
                        # Selecionar arquivo baseado na camada
                        if camada_nome == 'L3':
                            # Para L3, usar arquivo _A
                            arquivo_selecionado = None
                            for arq in arquivos_disponiveis:
                                if '_A' in arq['nome_peca'] or arq['nome_peca'].endswith('_A'):
                                    arquivo_selecionado = arq
                                    break
                            if not arquivo_selecionado:
                                arquivo_selecionado = arquivos_disponiveis[0]  # Fallback
                        elif camada_nome == 'L3_B':
                            # Para L3_B, usar arquivo _B
                            arquivo_selecionado = None
                            for arq in arquivos_disponiveis:
                                if '_B' in arq['nome_peca'] or arq['nome_peca'].endswith('_B'):
                                    arquivo_selecionado = arq
                                    break
                            if not arquivo_selecionado:
                                # Se não encontrou _B, usar o segundo arquivo se existir
                                arquivo_selecionado = arquivos_disponiveis[1] if len(arquivos_disponiveis) > 1 else arquivos_disponiveis[0]
                        else:
                            # Para outras camadas, usar arquivo baseado no índice
                            if idx < len(arquivos_disponiveis):
                                arquivo_selecionado = arquivos_disponiveis[idx]
                            else:
                                arquivo_selecionado = arquivos_disponiveis[0]  # Fallback
                        
                        nome_peca = arquivo_selecionado['nome_peca']
                        espessura = arquivo_selecionado.get('espessura', '1.0')
                        
                        print(f"DEBUG XML: Peça {peca_atual} - Camada {camada_nome} usando arquivo: {nome_peca}")
                        
                        # Gerar OP diferenciada para cada peça e camada
                        peca_index = pecas_para_gerar.index(peca_atual)
                        op_diferenciada = f"{op}-{chr(65 + (peca_index * 10) + idx)}"
                        
                        # Criar XML
                        root = Element('RPOrderGenerator')
                        root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
                        root.set('xmlns:xsd', 'http://www.w3.org/2001/XMLSchema')

                        queued_item = SubElement(root, 'QueuedItem')

                        SubElement(queued_item, 'Driver').text = 'D006'
                        SubElement(queued_item, 'TransactionId').text = '000'
                        
                        # PartCode e FilePart devem ser o nome completo do arquivo
                        SubElement(queued_item, 'PartCode').text = nome_peca
                        SubElement(queued_item, 'CustomerCode').text = peca_data.get('veiculo', '')
                        part_description = f"{peca_data.get('local', '')} | {projeto} | {peca_atual} | {camada_nome}"
                        SubElement(queued_item, 'CustomerDescription').text = part_description
                        SubElement(queued_item, 'Material').text = 'Acrílico-0'
                        SubElement(queued_item, 'Thickness').text = str(espessura)
                        SubElement(queued_item, 'Order').text = op_diferenciada
                        SubElement(queued_item, 'QtyRequired').text = str(total_items)
                        SubElement(queued_item, 'DeliveryDate').text = datetime.now().strftime('%d/%m/%Y')
                        
                        # FilePart deve ser o caminho relativo do arquivo
                        file_part = f"{nome_peca}"
                        SubElement(queued_item, 'FilePart').text = file_part

                        # Formatar XML
                        rough_string = tostring(root, 'utf-8')
                        reparsed = minidom.parseString(rough_string)
                        pretty_xml = reparsed.toprettyxml(indent='  ', encoding='utf-8')
                        
                        # Nome do arquivo XML - incluir peça atual
                        xml_filename = f"{op}_{projeto}_{peca_atual}_{camada_nome}.xml"
                        
                        zip_file.writestr(xml_filename, pretty_xml)
                        
                        xmls_gerados.append(f"OP {op_diferenciada} - Peça {peca_atual} - {camada_nome} (Qtd: {total_items}) - {nome_peca}")
                        
                        print(f"DEBUG XML: XML gerado: {xml_filename} com OP {op_diferenciada} (Qtd: {total_items}) usando arquivo {nome_peca}")
        
        # Log da ação com detalhes
        if xmls_nao_gerados:
            detalhes_log = f"XMLs: {len(xmls_gerados)} gerados, {len(xmls_nao_gerados)} não encontrados - {'; '.join(xmls_nao_gerados[:5])}"
            if len(xmls_nao_gerados) > 5:
                detalhes_log += f" e mais {len(xmls_nao_gerados) - 5}"
        else:
            detalhes_log = f"Gerou {len(xmls_gerados)} XML(s) com sucesso"
        
        cur.execute("""
            INSERT INTO public.pc_logs (usuario, acao, detalhes)
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
            os.path.expanduser(r"~\CARBON CARS\Programação e Controle de Produção - DocumentosPCP\AUTOMACAO LIBELLULA - PC"),
            os.path.expanduser(r"~\OneDrive - CARBON CARS\Programação e Controle de Produção - DocumentosPCP\AUTOMACAO LIBELLULA - PC"),
            os.path.expanduser(r"~\OneDrive\CARBON CARS\Programação e Controle de Produção - DocumentosPCP\AUTOMACAO LIBELLULA - PC"),
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
        
        # Buscar tipo_programacao e etapa_baixa para cada peça
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        for item in dados:
            cur.execute("""
                SELECT tipo_programacao, etapa_baixa FROM public.plano_controle_corte_vidro2
                WHERE op = %s AND peca = %s
                LIMIT 1
            """, (item.get('op', ''), item.get('peca', '')))
            
            result = cur.fetchone()
            if result:
                tipo_prog = result['tipo_programacao'] or ''
                etapa_baixa = result['etapa_baixa'] or ''
                
                if tipo_prog == 'BAIXAS' and etapa_baixa:
                    item['tipo_programacao'] = f"BAIXAS - {etapa_baixa}"
                else:
                    item['tipo_programacao'] = tipo_prog
            else:
                item['tipo_programacao'] = ''
        
        conn.close()
        
        df = pd.DataFrame(dados)
        df = df.rename(columns={
            'op': 'OP',
            'peca': 'PEÇA',
            'projeto': 'PROJETO',
            'veiculo': 'VEÍCULO',
            'local': 'LOCAL',
            'rack': 'RACK',
            'tipo_programacao': 'TIPO PROGRAMAÇÃO'
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

@app.route('/api/baixar-peca', methods=['POST'])
@login_required
def baixar_peca():
    try:
        dados = request.get_json()
        peca_id = dados.get('id')
        motivo_baixa = dados.get('motivo_baixa', '').strip()
        origem = dados.get('origem')  # 'estoque' ou 'otimizadas'
        
        if not peca_id or not motivo_baixa or not origem:
            return jsonify({'success': False, 'message': 'Dados incompletos'})
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Buscar peça na origem
        if origem == 'estoque':
            cur.execute("SELECT * FROM public.pc_inventory WHERE id = %s", (peca_id,))
        else:
            cur.execute("SELECT * FROM public.pc_otimizadas WHERE id = %s", (peca_id,))
        
        peca = cur.fetchone()
        if not peca:
            conn.close()
            return jsonify({'success': False, 'message': 'Peça não encontrada'})
        
        # Inserir na tabela pc_baixas com veiculo, sensor e lotes
        cur.execute("""
            INSERT INTO public.pc_baixas (op, peca, projeto, veiculo, sensor, motivo_baixa, data_baixa, usuario_apontamento, lote_vd, lote_pc)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE, %s, %s, %s)
        """, (
            peca['op'],
            peca['peca'],
            peca.get('projeto', ''),
            peca.get('veiculo', ''),
            peca.get('sensor', ''),
            motivo_baixa,
            current_user.username,
            peca.get('lote_vd', ''),
            peca.get('lote_pc', '')
        ))
        
        # Remover da origem
        if origem == 'estoque':
            cur.execute("DELETE FROM public.pc_inventory WHERE id = %s", (peca_id,))
        else:
            cur.execute("DELETE FROM public.pc_otimizadas WHERE id = %s", (peca_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Peça baixada com sucesso!'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/baixas')
@login_required
def api_baixas():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("""
            SELECT id, op, peca, projeto, veiculo, sensor, motivo_baixa, data_baixa, status, 
                   usuario_apontamento, data_criacao
            FROM public.pc_baixas 
            ORDER BY data_criacao DESC
        """)
        dados = cur.fetchall()
        conn.close()
        
        resultado = []
        for row in dados:
            item = dict(row)
            if item.get('data_baixa'):
                item['data_baixa'] = item['data_baixa'].strftime('%d/%m/%Y')
            if item.get('data_criacao'):
                item['data_criacao'] = item['data_criacao'].strftime('%d/%m/%Y %H:%M')
            item['veiculo'] = item.get('veiculo', '') or ''
            item['sensor'] = item.get('sensor', '') or ''
            resultado.append(item)
        
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reprocessar-baixa', methods=['POST'])
@login_required
def reprocessar_baixa():
    try:
        dados = request.get_json()
        baixa_id = dados.get('id')
        
        if not baixa_id:
            return jsonify({'success': False, 'message': 'ID da baixa não informado'})
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Buscar baixa
        cur.execute("SELECT * FROM public.pc_baixas WHERE id = %s", (baixa_id,))
        baixa = cur.fetchone()
        
        if not baixa:
            conn.close()
            return jsonify({'success': False, 'message': 'Baixa não encontrada'})
        
        # Verificar se já existe no estoque ou otimizadas
        cur.execute("SELECT COUNT(*) FROM public.pc_inventory WHERE op = %s AND peca = %s", (baixa['op'], baixa['peca']))
        if cur.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'message': f'Peça {baixa["peca"]} OP {baixa["op"]} já existe no estoque!'})
        
        cur.execute("SELECT COUNT(*) FROM public.pc_otimizadas WHERE op = %s AND peca = %s AND tipo = 'PC'", (baixa['op'], baixa['peca']))
        if cur.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'message': f'Peça {baixa["peca"]} OP {baixa["op"]} já existe nas otimizadas!'})
        
        # Buscar dados completos na tabela plano_controle_corte_vidro2 com JOIN para veículo
        cur.execute("""
            SELECT p.op, p.peca, p.projeto, p.sensor,
                   COALESCE(CONCAT(f.marca, ' ', f.modelo), p.tipo_programacao) as veiculo
            FROM public.plano_controle_corte_vidro2 p
            LEFT JOIN public.ficha_tecnica_veiculos f ON p.projeto = f.codigo_veiculo
            WHERE p.op = %s AND p.peca = %s
            ORDER BY p.data_geracao DESC LIMIT 1
        """, (baixa['op'], baixa['peca']))
        
        dados_completos = cur.fetchone()
        
        if dados_completos:
            veiculo = dados_completos['veiculo'] or baixa.get('veiculo', '')
            sensor = dados_completos['sensor'] or baixa.get('sensor', '')
        else:
            veiculo = baixa.get('veiculo', '')
            sensor = baixa.get('sensor', '')
        
        # Buscar locais ocupados para sugestão
        cur.execute("SELECT local FROM public.pc_inventory UNION SELECT local FROM public.pc_otimizadas WHERE tipo = 'PC'")
        locais_ocupados = {row['local'] for row in cur.fetchall() if row['local']}
        
        # Sugerir local usando a mesma lógica do index
        local_sugerido, rack_sugerido = sugerir_local_armazenamento(baixa['peca'], locais_ocupados, conn)
        
        if local_sugerido is None:
            conn.close()
            return jsonify({'success': False, 'message': f'Não há slots disponíveis para a peça {baixa["peca"]}. Todos os slots estão cheios!'})
        
        # Inserir na tabela pc_otimizadas com dados completos
        cur.execute("""
            INSERT INTO public.pc_otimizadas (op, peca, projeto, veiculo, sensor, local, rack, 
                                            user_otimizacao, tipo, cortada, lote_vd, lote_pc)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            baixa['op'],
            baixa['peca'],
            baixa['projeto'],
            veiculo,
            sensor,
            local_sugerido,
            rack_sugerido,
            current_user.username,
            'PC',
            False,
            baixa.get('lote_vd', ''),
            baixa.get('lote_pc', '')
        ))
        
        # Gerar XMLs usando a mesma lógica da função gerar_xml
        try:
            import zipfile
            import os
            from xml.etree.ElementTree import Element, SubElement, tostring
            from xml.dom import minidom
            
            xmls_gerados = []
            contador_xml = {}
            
            # Buscar todas as camadas da peça na tabela pc_camadas
            cur.execute("""
                SELECT * FROM public.pc_camadas 
                WHERE projeto = %s AND peca = %s
            """, (baixa['projeto'], baixa['peca']))
            
            camadas_result = cur.fetchone()
            print(f"DEBUG BAIXAS: Camadas encontradas para {baixa['projeto']} {baixa['peca']}: {dict(camadas_result) if camadas_result else 'Nenhuma'}")
            
            # Lista para armazenar as camadas válidas
            camadas_para_processar = []
            
            if camadas_result:
                # Processar apenas colunas específicas de camadas conhecidas
                colunas_camadas_conhecidas = ['l3', 'l3_b', 'l4', 'l5', 'l6', 'l7', 'l8']
                colunas_encontradas = [col for col in camadas_result.keys() if col in colunas_camadas_conhecidas]
                print(f"DEBUG BAIXAS: Colunas de camadas válidas encontradas: {colunas_encontradas}")
                
                contador_sequencia = 1
                for coluna in colunas_encontradas:
                    valor_camada = camadas_result[coluna]
                    print(f"DEBUG BAIXAS: Coluna {coluna} = '{valor_camada}' (tipo: {type(valor_camada)})")
                    # Processar apenas se existir e for diferente de "-" ou vazio
                    if valor_camada and str(valor_camada).strip() not in ['-', '', 'None', 'NULL', 'null']:
                        try:
                            quantidade = int(float(str(valor_camada)))
                            if quantidade > 0:
                                # Gerar múltiplos XMLs se quantidade > 1
                                for i in range(quantidade):
                                    numero_sequencia = f"{contador_sequencia:02d}"
                                    camadas_para_processar.append((coluna.upper(), numero_sequencia, i + 1, quantidade))
                                    print(f"DEBUG BAIXAS: Camada {coluna.upper()} #{i+1}/{quantidade} adicionada (seq: {numero_sequencia})")
                                    contador_sequencia += 1
                        except (ValueError, TypeError):
                            # Se não conseguir converter para número, tratar como 1
                            numero_sequencia = f"{contador_sequencia:02d}"
                            camadas_para_processar.append((coluna.upper(), numero_sequencia, 1, 1))
                            contador_sequencia += 1
                    else:
                        print(f"DEBUG BAIXAS: Camada {coluna} ignorada (valor inválido)")
                
                print(f"DEBUG BAIXAS: Total de camadas para processar: {len(camadas_para_processar)}")
            
            # Se não encontrou camadas válidas, tentar buscar arquivo genérico
            if not camadas_para_processar:
                print(f"DEBUG BAIXAS: Nenhuma camada válida encontrada, buscando arquivo genérico")
                cur.execute("""
                    SELECT nome_peca, espessura FROM public.arquivos_pc
                    WHERE projeto = %s AND peca = %s
                    ORDER BY id DESC LIMIT 1
                """, (baixa['projeto'], baixa['peca']))
                
                arquivo_generico = cur.fetchone()
                
                if arquivo_generico:
                    camadas_para_processar.append(('GENERICO', '01', 1, 1))
                    print(f"DEBUG BAIXAS: Arquivo genérico encontrado, adicionado como GENERICO")
            
            # Gerar XML para cada camada válida
            for idx, camada_info in enumerate(camadas_para_processar):
                camada_nome, numero_sequencia, item_num, total_items = camada_info
                # Buscar arquivo de corte específico para a camada e sensor
                sensor_peca = baixa.get('sensor', '') or ''
                
                # Tratar sensor '-' ou inválido
                if sensor_peca in ['-', '', 'None', 'NULL', 'null']:
                    # Buscar sensor do PBS da mesma OP
                    cur.execute("""
                        SELECT sensor FROM public.plano_controle_corte_vidro2
                        WHERE op = %s AND peca = 'PBS' AND sensor IS NOT NULL AND sensor != '' AND sensor != '-'
                        LIMIT 1
                    """, (baixa['op'],))
                    pbs_sensor = cur.fetchone()
                    sensor_peca = pbs_sensor['sensor'] if pbs_sensor else '1'
                
                # Buscar por sensor específico
                if sensor_peca and sensor_peca not in ['-', '', 'None', 'NULL', 'null']:
                    cur.execute("""
                        SELECT nome_peca, espessura FROM public.arquivos_pc
                        WHERE projeto = %s AND peca = %s AND (sensor = %s OR nome_peca LIKE %s)
                        ORDER BY 
                            CASE WHEN sensor = %s THEN 1 ELSE 2 END,
                            CASE WHEN nome_peca LIKE %s THEN 1 ELSE 2 END,
                            id DESC
                    """, (baixa['projeto'], baixa['peca'], sensor_peca, f'%_{sensor_peca}', sensor_peca, f'%_{sensor_peca}'))
                else:
                    cur.execute("""
                        SELECT nome_peca, espessura FROM public.arquivos_pc
                        WHERE projeto = %s AND peca = %s
                        ORDER BY id DESC
                    """, (baixa['projeto'], baixa['peca']))
                
                arquivos_encontrados = cur.fetchall()
                
                if not arquivos_encontrados:
                    # Debug: tentar busca sem filtro de sensor
                    cur.execute("""
                        SELECT nome_peca, espessura FROM public.arquivos_pc
                        WHERE projeto = %s AND peca = %s
                        ORDER BY id DESC
                    """, (baixa['projeto'], baixa['peca']))
                    arquivos_sem_sensor = cur.fetchall()
                    
                    if arquivos_sem_sensor:
                        print(f"DEBUG BAIXAS: Encontrou {len(arquivos_sem_sensor)} arquivo(s) sem filtro de sensor para {baixa['projeto']} {baixa['peca']}")
                        arquivos_encontrados = arquivos_sem_sensor
                    else:
                        print(f"DEBUG BAIXAS: Nenhum arquivo encontrado para projeto={baixa['projeto']}, peca={baixa['peca']}, sensor={sensor_peca}")
                        continue
                
                # Para cada camada, usar o arquivo correspondente se existir múltiplos
                if len(arquivos_encontrados) > idx:
                    arquivo_info = arquivos_encontrados[idx]
                else:
                    arquivo_info = arquivos_encontrados[0]  # Usar o primeiro se não houver suficientes
                
                nome_peca = arquivo_info['nome_peca']
                espessura = arquivo_info.get('espessura', '1.0')
                
                # Gerar OP diferenciada para cada camada
                op_diferenciada = f"{baixa['op']}-{chr(65 + idx)}"  # 65 = 'A', então será A, B, C, etc.
                
                # Criar XML
                root = Element('RPOrderGenerator')
                root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
                root.set('xmlns:xsd', 'http://www.w3.org/2001/XMLSchema')
                
                queued_item = SubElement(root, 'QueuedItem')
                
                SubElement(queued_item, 'Driver').text = 'D006'
                SubElement(queued_item, 'TransactionId').text = '000'
                SubElement(queued_item, 'PartCode').text = nome_peca
                SubElement(queued_item, 'CustomerCode').text = veiculo
                part_description = f"{local_sugerido} | {baixa['projeto']} | {baixa['peca']} | {camada_nome}"
                SubElement(queued_item, 'CustomerDescription').text = part_description
                SubElement(queued_item, 'Material').text = 'Acrílico-0'
                SubElement(queued_item, 'Thickness').text = str(espessura)
                SubElement(queued_item, 'Order').text = op_diferenciada
                SubElement(queued_item, 'QtyRequired').text = '1'
                SubElement(queued_item, 'DeliveryDate').text = datetime.now().strftime('%d/%m/%Y')
                SubElement(queued_item, 'FilePart').text = nome_peca
                
                # Formatar XML
                rough_string = tostring(root, 'utf-8')
                reparsed = minidom.parseString(rough_string)
                pretty_xml = reparsed.toprettyxml(indent='  ', encoding='utf-8')
                
                # Salvar XML na pasta do SharePoint
                sharepoint_paths = [
                    os.path.expanduser(r"~\CARBON CARS\Programação e Controle de Produção - DocumentosPCP\AUTOMACAO LIBELLULA - PC"),
                    os.path.expanduser(r"~\OneDrive - CARBON CARS\Programação e Controle de Produção - DocumentosPCP\AUTOMACAO LIBELLULA - PC"),
                    os.path.expanduser(r"~\OneDrive\CARBON CARS\Programação e Controle de Produção - DocumentosPCP\AUTOMACAO LIBELLULA - PC"),
                    os.path.expanduser(r"~\Documents\XMLs")
                ]
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                if total_items > 1:
                    xml_filename = f"{baixa['op']}_{baixa['projeto']}_{baixa['peca']}_{camada_nome}_{item_num:02d}_reprocessado_{timestamp}.xml"
                else:
                    xml_filename = f"{baixa['op']}_{baixa['projeto']}_{baixa['peca']}_{camada_nome}_reprocessado_{timestamp}.xml"
                
                xml_salvo = False
                for sharepoint_path in sharepoint_paths:
                    try:
                        if os.path.exists(sharepoint_path):
                            xml_file_path = os.path.join(sharepoint_path, xml_filename)
                            with open(xml_file_path, 'wb') as f:
                                f.write(pretty_xml)
                            xml_salvo = True
                            if total_items > 1:
                                xmls_gerados.append(f"OP {op_diferenciada} - Peça {baixa['peca']} - {camada_nome} #{item_num}/{total_items} - {nome_peca}")
                            else:
                                xmls_gerados.append(f"OP {op_diferenciada} - Peça {baixa['peca']} - {camada_nome} - {nome_peca}")
                            if total_items > 1:
                                print(f"DEBUG BAIXAS: XML gerado: {xml_filename} com OP {op_diferenciada} (item {item_num}/{total_items})")
                            else:
                                print(f"DEBUG BAIXAS: XML gerado: {xml_filename} com OP {op_diferenciada}")
                            break
                    except Exception:
                        continue
        
        except Exception as xml_error:
            print(f"Erro ao gerar XML: {xml_error}")
        
        # Atualizar status da baixa
        cur.execute("""
            UPDATE public.pc_baixas 
            SET status = 'PROCESSADO', processado_por = %s, data_processamento = NOW()
            WHERE id = %s
        """, (current_user.username, baixa_id))
        
        conn.commit()
        conn.close()
        
        # Preparar mensagem com quantidade de XMLs gerados
        if xmls_gerados:
            xml_message = f", {len(xmls_gerados)} XML(s) gerado(s)"
        else:
            xml_message = ", nenhum XML gerado (arquivo não encontrado)"
        
        return jsonify({'success': True, 'message': f'Peça reprocessada{xml_message} e adicionada às otimizadas!'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/lotes')
def api_lotes():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Primeiro testar se a tabela existe
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'plano_controle_corte_vidro2'
        """)
        table_exists = cur.fetchone()[0] > 0
        print(f"DEBUG: Tabela plano_controle_corte_vidro2 existe: {table_exists}")
        
        if not table_exists:
            conn.close()
            return jsonify({'error': 'Tabela plano_controle_corte_vidro2 não encontrada'}), 500
        
        # Testar se há dados na tabela
        cur.execute("SELECT COUNT(*) FROM public.plano_controle_corte_vidro2")
        total_records = cur.fetchone()[0]
        print(f"DEBUG: Total de registros na tabela: {total_records}")
        
        # Query agrupada para evitar duplicatas
        cur.execute("""
            SELECT id_lote, data_programacao, turno_programacao,
                   MAX(CASE WHEN etapa_baixa IS NOT NULL AND etapa_baixa != '' THEN 1 ELSE 0 END) as tem_baixa
            FROM public.plano_controle_corte_vidro2 
            WHERE id_lote IS NOT NULL AND id_lote != ''
            AND (pc_cortado IS NULL OR pc_cortado = '' OR pc_cortado != 'CORTADO')
            GROUP BY id_lote, data_programacao, turno_programacao
            ORDER BY data_programacao DESC, turno_programacao
        """)
        
        rows = cur.fetchall()
        print(f"DEBUG: Encontrados {len(rows)} lotes distintos")
        
        lotes_formatados = []
        for row in rows:
            print(f"DEBUG: Processando lote: {row['id_lote']}, data: {row['data_programacao']}, turno: {row['turno_programacao']}")
            
            # Converter turno
            turno_map = {
                'primeiro': '1°',
                'segundo': '2°', 
                'terceiro': '3°'
            }
            turno = turno_map.get(row['turno_programacao'], row['turno_programacao'])
            
            # Formatar data de YYYY-MM-DD para DD/MM/YYYY
            data_formatada = row['data_programacao']
            if data_formatada:
                try:
                    from datetime import datetime
                    data_obj = datetime.strptime(str(data_formatada), '%Y-%m-%d')
                    data_formatada = data_obj.strftime('%d/%m/%Y')
                except:
                    pass
            
            # Verificar se é lote de baixas
            is_baixa = row['tem_baixa'] == 1
            display_text = f"{turno} - {data_formatada} - {row['id_lote']}"
            if is_baixa:
                display_text += " - BAIXAS"
            
            lotes_formatados.append({
                'id_lote': row['id_lote'],
                'display': display_text
            })
        
        conn.close()
        print(f"DEBUG: Retornando {len(lotes_formatados)} lotes formatados")
        return jsonify(lotes_formatados)
        
    except Exception as e:
        print(f"DEBUG: Erro na API lotes: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/buscar-arquivo')
@login_required
def buscar_arquivo():
    try:
        projeto = request.args.get('projeto', '').strip()
        peca = request.args.get('peca', '').strip()
        sensor = request.args.get('sensor', '').strip() or '1'
        
        if not projeto or not peca:
            return jsonify({'encontrado': False, 'message': 'Projeto e peça são obrigatórios'})
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Buscar arquivo com sensor exato primeiro
        cur.execute("""
            SELECT nome_peca FROM public.arquivos_pc
            WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
            AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
            AND UPPER(TRIM(CAST(sensor AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
            ORDER BY id DESC
            LIMIT 1
        """, (str(projeto), str(peca), str(sensor)))
        
        arquivo_exato = cur.fetchone()
        
        if arquivo_exato:
            conn.close()
            return jsonify({
                'encontrado': True,
                'nome_arquivo': arquivo_exato['nome_peca'],
                'tipo': 'exato'
            })
        
        # Se não encontrou com sensor exato, buscar por nome_peca que contenha o sensor
        cur.execute("""
            SELECT nome_peca FROM public.arquivos_pc
            WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
            AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
            AND nome_peca LIKE %s
            ORDER BY id DESC
            LIMIT 1
        """, (str(projeto), str(peca), f'%_{sensor}'))
        
        arquivo_similar = cur.fetchone()
        
        if arquivo_similar:
            conn.close()
            return jsonify({
                'encontrado': True,
                'nome_arquivo': arquivo_similar['nome_peca'],
                'tipo': 'similar',
                'message': 'Arquivo encontrado com sensor no nome'
            })
        
        # Se ainda não encontrou, buscar qualquer arquivo da peça
        cur.execute("""
            SELECT nome_peca FROM public.arquivos_pc
            WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
            AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
            ORDER BY id DESC LIMIT 1
        """, (str(projeto), str(peca)))
        
        arquivo_generico = cur.fetchone()
        conn.close()
        
        if arquivo_generico:
            return jsonify({
                'encontrado': True,
                'nome_arquivo': arquivo_generico['nome_peca'],
                'tipo': 'generico',
                'message': 'Arquivo encontrado sem sensor específico'
            })
        
        return jsonify({
            'encontrado': False,
            'message': 'Nenhum arquivo encontrado para este projeto/peça'
        })
        
    except Exception as e:
        return jsonify({'encontrado': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/limpar-pecas-manuais', methods=['POST'])
@login_required
def limpar_pecas_manuais():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Criar tabela se não existir
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.pc_manuais (
                id SERIAL PRIMARY KEY,
                op TEXT,
                peca TEXT,
                projeto TEXT,
                veiculo TEXT,
                sensor TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Fazer truncate na tabela
        cur.execute("TRUNCATE TABLE public.pc_manuais RESTART IDENTITY")
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Tabela pc_manuais limpa com sucesso!'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao limpar tabela: {str(e)}'}), 500

@app.route('/api/buscar-veiculo-local')
@login_required
def buscar_veiculo_local():
    global contador_slots_temp
    contador_slots_temp = {}  # Limpar contador no início de cada busca
    
    try:
        projeto = request.args.get('projeto', '').strip()
        peca = request.args.get('peca', '').strip()
        
        if not projeto or not peca:
            return jsonify({'success': False, 'message': 'Projeto e peça são obrigatórios'})
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Buscar veículo da mesma forma que na tela index
        cur.execute("""
            SELECT COALESCE(CONCAT(f.marca, ' ', f.modelo), 'Não encontrado') as veiculo
            FROM public.ficha_tecnica_veiculos f 
            WHERE f.codigo_veiculo = %s
            LIMIT 1
        """, (projeto,))
        
        veiculo_result = cur.fetchone()
        veiculo = veiculo_result['veiculo'] if veiculo_result else 'Não encontrado'
        
        # Sugerir local com contador limpo
        local_sugerido, rack_sugerido = sugerir_local_armazenamento(peca, set(), conn)
        
        conn.close()
        
        if local_sugerido is None:
            return jsonify({
                'success': False,
                'message': f'Não há slots disponíveis para a peça {peca}. Todos os slots estão cheios!'
            })
        
        return jsonify({
            'success': True,
            'veiculo': veiculo,
            'local': local_sugerido
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/entrada-manual-estoque', methods=['POST'])
@login_required
def entrada_manual_estoque():
    global contador_slots_temp
    contador_slots_temp = {}  # Limpar contador no início de cada entrada manual
    
    try:
        dados = request.get_json()
        op = dados.get('op', '').strip()
        peca = dados.get('peca', '').strip()
        projeto = dados.get('projeto', '').strip()
        veiculo = dados.get('veiculo', '').strip()
        local = dados.get('local', '').strip()
        sensor_input = dados.get('sensor', '').strip()
        
        # Definir sensor baseado no tipo de peça
        if peca == 'PBS':
            sensor = sensor_input if sensor_input else '1'
        else:
            sensor = '1'
        
        if not all([op, peca, projeto]):
            return jsonify({'success': False, 'message': 'OP, Peça e Projeto são obrigatórios'})
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Verificar se já existe no estoque
        cur.execute("SELECT COUNT(*) FROM public.pc_inventory WHERE op = %s AND peca = %s", (op, peca))
        if cur.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'message': f'Peça {peca} OP {op} já existe no estoque!'})
        
        # Verificar se já existe nas otimizadas
        cur.execute("SELECT COUNT(*) FROM public.pc_otimizadas WHERE op = %s AND peca = %s AND tipo = 'PC'", (op, peca))
        if cur.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'message': f'Peça {peca} OP {op} já existe nas otimizadas!'})
        
        # Verificar capacidade do local incluindo peças otimizadas
        if local:
            cur.execute("SELECT limite FROM public.pc_locais WHERE local = %s", (local,))
            limite_result = cur.fetchone()
            if limite_result:
                limite = int(limite_result['limite']) if limite_result['limite'] else 6
                
                # Contar peças no local (estoque + otimizadas)
                cur.execute("""
                    SELECT COUNT(*) FROM (
                        SELECT local FROM public.pc_inventory WHERE local = %s
                        UNION ALL
                        SELECT local FROM public.pc_otimizadas WHERE local = %s AND tipo = 'PC'
                    ) as total_local
                """, (local, local))
                ocupacao = cur.fetchone()[0]
                
                if ocupacao >= limite:
                    conn.close()
                    return jsonify({'success': False, 'message': f'Local {local} está cheio! Limite: {limite}, Ocupado: {ocupacao}'})
        
        # Usar o sensor informado pelo usuário diretamente
        sensor_busca = sensor if sensor and sensor not in ['nan', 'NaN', 'None', ''] else '1'
        
        print(f"DEBUG ENTRADA MANUAL: Buscando arquivo para projeto='{projeto}', peca='{peca}', sensor_busca='{sensor_busca}'")
        
        # Buscar arquivo com sensor exato primeiro
        cur.execute("""
            SELECT nome_peca FROM public.arquivos_pc
            WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
            AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
            AND UPPER(TRIM(CAST(sensor AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
            ORDER BY id DESC
            LIMIT 1
        """, (str(projeto), str(peca), str(sensor_busca)))
        
        arquivo_result = cur.fetchone()
        
        # Se não encontrou com sensor exato, buscar por nome_peca que contenha o sensor
        if not arquivo_result:
            cur.execute("""
                SELECT nome_peca FROM public.arquivos_pc
                WHERE UPPER(TRIM(CAST(projeto AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT))) 
                AND UPPER(TRIM(CAST(peca AS TEXT))) = UPPER(TRIM(CAST(%s AS TEXT)))
                AND nome_peca LIKE %s
                ORDER BY id DESC
                LIMIT 1
            """, (str(projeto), str(peca), f'%_{sensor_busca}'))
            arquivo_result = cur.fetchone()
        
        print(f"DEBUG ENTRADA MANUAL: Resultado encontrado: {arquivo_result}")
        
        # Inserir no estoque
        cur.execute("""
            INSERT INTO public.pc_inventory (op, peca, projeto, veiculo, local, sensor, usuario, data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (op, peca, projeto, veiculo, local, sensor, current_user.username))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Peça {peca} OP {op} adicionada ao estoque no local {local}!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/editar-peca-estoque', methods=['PUT'])
@login_required
def editar_peca_estoque():
    try:
        dados = request.get_json()
        peca_id = dados.get('id')
        op = dados.get('op', '').strip()
        peca = dados.get('peca', '').strip()
        projeto = dados.get('projeto', '').strip()
        veiculo = dados.get('veiculo', '').strip()
        local = dados.get('local', '').strip()
        sensor = dados.get('sensor', '').strip()
        
        if not peca_id:
            return jsonify({'success': False, 'message': 'ID da peça não informado'})
        
        if not all([op, peca, projeto]):
            return jsonify({'success': False, 'message': 'OP, Peça e Projeto são obrigatórios'})
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Verificar se a peça existe
        cur.execute("SELECT * FROM public.pc_inventory WHERE id = %s", (peca_id,))
        peca_atual = cur.fetchone()
        
        if not peca_atual:
            conn.close()
            return jsonify({'success': False, 'message': 'Peça não encontrada no estoque'})
        
        # Verificar se não há duplicata (exceto a própria peça)
        cur.execute("""
            SELECT COUNT(*) FROM public.pc_inventory 
            WHERE op = %s AND peca = %s AND id != %s
        """, (op, peca, peca_id))
        
        if cur.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'message': f'Já existe outra peça {peca} OP {op} no estoque!'})
        
        # Verificar capacidade do local se mudou
        if local and local != peca_atual['local']:
            cur.execute("SELECT limite FROM public.pc_locais WHERE local = %s", (local,))
            limite_result = cur.fetchone()
            if limite_result:
                limite = int(limite_result['limite']) if limite_result['limite'] else 6
                
                # Contar peças no local (excluindo a atual)
                cur.execute("""
                    SELECT COUNT(*) FROM (
                        SELECT local FROM public.pc_inventory WHERE local = %s AND id != %s
                        UNION ALL
                        SELECT local FROM public.pc_otimizadas WHERE local = %s AND tipo = 'PC'
                    ) as total_local
                """, (local, peca_id, local))
                ocupacao = cur.fetchone()[0]
                
                if ocupacao >= limite:
                    conn.close()
                    return jsonify({'success': False, 'message': f'Local {local} está cheio! Limite: {limite}, Ocupado: {ocupacao}'})
        
        # Atualizar a peça
        cur.execute("""
            UPDATE public.pc_inventory 
            SET op = %s, peca = %s, projeto = %s, veiculo = %s, local = %s, sensor = %s
            WHERE id = %s
        """, (op, peca, projeto, veiculo, local, sensor, peca_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Peça {peca} OP {op} atualizada com sucesso!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/voltar-estoque', methods=['POST'])
@login_required
def voltar_estoque():
    try:
        dados = request.get_json()
        saida_id = dados.get('id')
        
        if not saida_id:
            return jsonify({'success': False, 'message': 'ID da saída não informado'})
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Buscar dados da saída
        cur.execute("SELECT * FROM public.pc_exit WHERE id = %s", (saida_id,))
        saida = cur.fetchone()
        
        if not saida:
            conn.close()
            return jsonify({'success': False, 'message': 'Saída não encontrada'})
        
        # Verificar se já existe no estoque
        cur.execute("SELECT COUNT(*) FROM public.pc_inventory WHERE op = %s AND peca = %s", (saida['op'], saida['peca']))
        if cur.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'message': f'Peça {saida["peca"]} OP {saida["op"]} já existe no estoque!'})
        
        # Buscar locais ocupados para sugestão
        cur.execute("SELECT local FROM public.pc_inventory UNION SELECT local FROM public.pc_otimizadas WHERE tipo = 'PC'")
        locais_ocupados = {row['local'] for row in cur.fetchall() if row['local']}
        
        # Sugerir novo local usando a regra de alocação
        local_sugerido, rack_sugerido = sugerir_local_armazenamento(saida['peca'], locais_ocupados, conn)
        
        if local_sugerido is None:
            conn.close()
            return jsonify({'success': False, 'message': f'Não há slots disponíveis para a peça {saida["peca"]}. Todos os slots estão cheios!'})
        
        # Inserir no estoque com novo local
        cur.execute("""
            INSERT INTO public.pc_inventory (op, peca, projeto, veiculo, sensor, local, usuario, data, lote_vd, lote_pc)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
        """, (
            saida['op'],
            saida['peca'],
            saida.get('projeto', ''),
            saida.get('veiculo', ''),
            saida.get('sensor', ''),
            local_sugerido,
            current_user.username,
            saida.get('lote_vd', ''),
            saida.get('lote_pc', '')
        ))
        
        # Remover da tabela de saídas
        cur.execute("DELETE FROM public.pc_exit WHERE id = %s", (saida_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Peça {saida["peca"]} retornada ao estoque no local {local_sugerido}!'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

if __name__ == '__main__':
    # Verificar se está rodando em container (sem inicialização do dashboard)
    is_container = os.getenv('FLASK_ENV') == 'production'
    
    if not is_container:
        # Execução local - iniciar dashboard em thread separada
        import subprocess
        import threading
        import time
        
        def iniciar_dashboard():
            """Inicia o dashboard em thread separada"""
            time.sleep(2)  # Aguarda 2 segundos para o app principal iniciar
            try:
                print("Iniciando Dashboard na porta 5002...")
                subprocess.Popen(['python', 'dashboard_app.py'], cwd=os.path.dirname(os.path.abspath(__file__)))
            except Exception as e:
                print(f"Erro ao iniciar dashboard: {e}")
        
        try:
            print("Iniciando servidor Flask...")
            
            # Iniciar dashboard em thread separada
            dashboard_thread = threading.Thread(target=iniciar_dashboard, daemon=True)
            dashboard_thread.start()
            
            app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
        except Exception as e:
            print(f"Erro ao iniciar servidor: {e}")
            input("Pressione Enter para sair...")
            exit(1)
    else:
        # Execução em container - apenas executar o app principal
        print("Executando em container - dashboard gerenciado pelo script de inicialização")
        app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5001)), debug=False, threaded=True)