from flask import Flask, render_template, jsonify, request, send_file
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
import time
import pandas as pd
import io
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')

if not os.path.exists(ENV_PATH):
    print("ERRO: Arquivo .env não encontrado!")
    exit(1)

load_dotenv(ENV_PATH)

app = Flask(__name__)

# Configuração do banco PostgreSQL
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PSW'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME')
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)



@app.route('/')
def dashboard():
    return render_template('dashboard_standalone.html')

@app.route('/api/dashboard-producao')
def api_dashboard_producao():
    try:
        print(f"Connecting to database: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        conn = get_db_connection()
        print("Database connection successful")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get stock pieces grouped by PEÇA+OP
        query_estoque = """
        SELECT 
            i.op,
            i.peca,
            i.projeto,
            COALESCE(d.modelo, i.veiculo) as veiculo,
            STRING_AGG(DISTINCT i.local, ', ' ORDER BY i.local) as locais,
            COUNT(*) as quantidade,
            COALESCE(UPPER(d.etapa), 'PEÇA NÃO ESTÁ NO PPLUG OU FOI APROVADA IF') as etapa,
            COALESCE(UPPER(d.prioridade), 'NORMAL') as prioridade,
            COALESCE(
                NULLIF(STRING_AGG(DISTINCT NULLIF(i.sensor, ''), ', ' ORDER BY NULLIF(i.sensor, '')), ''),
                (
                    SELECT COALESCE(
                        NULLIF(d2.sensor, ''),
                        (
                            SELECT NULLIF(p.sensor, '')
                            FROM public.plano_controle_corte_vidro2 p
                            WHERE p.op = i.op AND p.peca = 'PBS'
                            AND p.sensor IS NOT NULL AND p.sensor != ''
                            LIMIT 1
                        )
                    )
                    FROM dados_uso_geral.dados_op d2
                    WHERE d2.op::text = i.op::text AND d2.planta = 'Jarinu'
                    LIMIT 1
                ),
                ''
            ) as sensor
        FROM pc_inventory i
        LEFT JOIN dados_uso_geral.dados_op d ON i.op::text = d.op::text AND i.peca = d.item AND d.planta = 'Jarinu'
        GROUP BY i.op, i.peca, i.projeto, COALESCE(d.modelo, i.veiculo), d.etapa, d.prioridade
        ORDER BY MAX(i.id) DESC
        """
        
        cursor.execute(query_estoque)
        resultados_estoque = cursor.fetchall()
        print(f"DEBUG: Found {len(resultados_estoque)} stock pieces")
        
        # Get pieces in production stages that are NOT in stock
        # BLOCO PLANO: CORTE, LAPIDACAO, SERIGRAFIA, SINTERIZACAO, EMPOLVADO, BUFFER
        # BLOCO CURVO: FORNO-S, RESFRIAMENTO, POS-FORNO, ACO, CORTE-CURVO
        query_producao = """
        SELECT DISTINCT
            d.op,
            d.item as peca,
            d.codigo_veiculo as projeto,
            COALESCE(CONCAT(f.marca, ' ', f.modelo), '') as veiculo,
            UPPER(d.etapa) as etapa,
            COALESCE(UPPER(d.prioridade), 'NORMAL') as prioridade,
            CASE 
                WHEN UPPER(d.etapa) IN ('CORTE', 'LAPIDACAO', 'SERIGRAFIA', 'SINTERIZACAO', 'EMPOLVADO', 'BUFFER') THEN 'BLOCO PLANO'
                WHEN UPPER(d.etapa) IN ('FORNO-S', 'RESFRIAMENTO', 'POS-FORNO', 'ACO', 'CORTE-CURVO') THEN 'BLOCO CURVO'
                ELSE 'OUTROS'
            END as bloco
        FROM dados_uso_geral.dados_op d
        LEFT JOIN public.ficha_tecnica_veiculos f ON d.codigo_veiculo = f.codigo_veiculo
        WHERE UPPER(d.etapa) IN ('CORTE', 'LAPIDACAO', 'SERIGRAFIA', 'SINTERIZACAO', 'EMPOLVADO', 'BUFFER', 'FORNO-S', 'RESFRIAMENTO', 'POS-FORNO', 'ACO', 'CORTE-CURVO')
        AND d.planta = 'Jarinu'
        AND NOT EXISTS (
            SELECT 1 FROM pc_inventory i 
            WHERE i.op::text = d.op::text AND i.peca = d.item
        )
        AND NOT EXISTS (
            SELECT 1 FROM pc_otimizadas o 
            WHERE o.op::text = d.op::text AND o.peca = d.item
        )
        AND d.op::text NOT IN (
            SELECT DISTINCT e.op::text 
            FROM pc_exit e 
            WHERE e.peca = d.item
            AND e.data >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
        )
        ORDER BY d.op, d.item
        """
        
        cursor.execute(query_producao)
        resultados_producao = cursor.fetchall()
        print(f"DEBUG: Found {len(resultados_producao)} production pieces")
        
        # Debug: Check recent exits
        cursor.execute("""
        SELECT op, peca, data, 
               EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - data))/3600 as hours_ago
        FROM pc_exit 
        WHERE data >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
        ORDER BY data DESC
        """)
        recent_exits = cursor.fetchall()
        print(f"DEBUG: Recent exits in last 24h: {len(recent_exits)}")
        for exit_row in recent_exits:
            print(f"  Exit: {exit_row[1]}+{exit_row[0]} at {exit_row[2]} ({exit_row[3]:.1f}h ago)")
        
        # Debug: Check if specific pieces in production have recent exits
        for prod_row in resultados_producao:
            cursor.execute("""
            SELECT COUNT(*), MAX(data) as last_exit
            FROM pc_exit 
            WHERE op::text = %s AND peca = %s
            AND data >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
            """, (str(prod_row[0]), prod_row[1]))
            exit_check = cursor.fetchone()
            if exit_check[0] > 0:
                print(f"  WARNING: {prod_row[1]}+{prod_row[0]} in production but has recent exit: {exit_check[1]}")
        
        # Get pieces that have passed assembly (critical stages) - ONLY those in stock
        query_pos_montagem = """
        SELECT 
            i.op,
            i.peca,
            i.projeto,
            COALESCE(d.modelo, i.veiculo) as veiculo,
            STRING_AGG(DISTINCT i.local, ', ' ORDER BY i.local) as locais,
            COUNT(*) as quantidade,
            CASE 
                WHEN (
                    SELECT a.etapa 
                    FROM apontamento_pplug_jarinu a 
                    WHERE a.op = i.op AND a.item = i.peca 
                    ORDER BY a.data DESC 
                    LIMIT 1
                ) = 'INSPECAO FINAL' THEN 'PEÇA APROVADA INSP FINAL'
                ELSE UPPER(d.etapa)
            END as etapa,
            COALESCE(UPPER(d.prioridade), 'NORMAL') as prioridade
        FROM pc_inventory i
        INNER JOIN dados_uso_geral.dados_op d ON i.op::text = d.op::text AND i.peca = d.item AND d.planta = 'Jarinu'
        WHERE UPPER(d.etapa) IN ('MONTAGEM', 'INSPECAO FINAL', 'BUFFER-AUTOCLAVE', 'AUTOCLAVE', 'EMBOLSADO')
        GROUP BY i.op, i.peca, i.projeto, COALESCE(d.modelo, i.veiculo), d.etapa, d.prioridade
        ORDER BY MAX(i.id) DESC
        """
        
        cursor.execute(query_pos_montagem)
        resultados_pos_montagem = cursor.fetchall()
        print(f"DEBUG: Found {len(resultados_pos_montagem)} post-assembly pieces")
        
        dados = []
        
        # Process stock pieces
        for row in resultados_estoque:
            etapa = row[6]
            prioridade = row[7]
            status = 'normal'
            if etapa == 'PEÇA NÃO ESTÁ NO PPLUG OU FOI APROVADA IF':
                status = 'critico'
            # Removed duplicate logic - post-assembly pieces are handled separately
            elif etapa in ['PRE-MONTAGEM', 'PREMONTAGEM']:
                status = 'aviso'
            
            if etapa == 'BUFFER-AUTOCLAVE':
                etapa = 'BUFFER-ACV'
            
            dados.append({
                'op': row[0] or '',
                'peca': row[1] or '',
                'projeto': row[2] or '',
                'veiculo': row[3] or '',
                'local': row[4] or '',
                'quantidade': row[5],
                'etapa': etapa,
                'prioridade': prioridade,
                'status': status,
                'sensor': row[8] or ''
            })
        
        # Process production pieces not in stock
        for row in resultados_producao:
            etapa = row[4]
            prioridade = row[5]
            bloco = row[6]
            
            # Define status based on block
            status = 'plano' if bloco == 'BLOCO PLANO' else 'curvo'
            
            dados.append({
                'op': row[0] or '',
                'peca': row[1] or '',
                'projeto': row[2] or '',
                'veiculo': row[3] or '',
                'local': etapa,
                'quantidade': 1,
                'etapa': etapa,
                'prioridade': prioridade,
                'status': status,
                'bloco': bloco
            })
        
        # Process pieces that have passed assembly (in stock)
        for row in resultados_pos_montagem:
            etapa = row[6]
            prioridade = row[7]
            
            dados.append({
                'op': row[0] or '',
                'peca': row[1] or '',
                'projeto': row[2] or '',
                'veiculo': row[3] or '',
                'local': row[4] or '',
                'quantidade': row[5],
                'etapa': etapa,
                'prioridade': prioridade,
                'status': 'critico'
            })
        
        cursor.close()
        conn.close()
        
        print(f"DEBUG: Returning {len(dados)} total pieces (Stock: {len(resultados_estoque)}, Production: {len(resultados_producao)}, Post-Assembly in Stock: {len(resultados_pos_montagem)})")
        return jsonify(dados)
        
    except Exception as e:
        print(f"Dashboard error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/gerar-excel-dashboard', methods=['POST'])
def gerar_excel_dashboard():
    try:
        dados = request.get_json()
        dados_dashboard = dados.get('dados', [])
        aba_ativa = dados.get('aba_ativa', 'premontagem')
        
        if not dados_dashboard:
            return jsonify({'success': False, 'message': 'Nenhum dado encontrado'})
        
        # Filtrar dados baseado na aba ativa
        if aba_ativa == 'premontagem':
            dados_filtrados = [item for item in dados_dashboard if item.get('status') == 'aviso']
            nome_aba = 'Pré-Montagem'
        elif aba_ativa == 'criticas':
            dados_filtrados = [item for item in dados_dashboard if item.get('status') == 'critico']
            nome_aba = 'Críticas'
        elif aba_ativa == 'plano':
            dados_filtrados = [item for item in dados_dashboard if item.get('status') == 'plano']
            nome_aba = 'Bloco Plano'
        elif aba_ativa == 'curvo':
            dados_filtrados = [item for item in dados_dashboard if item.get('status') == 'curvo']
            nome_aba = 'Bloco Curvo'
        else:
            dados_filtrados = dados_dashboard
            nome_aba = 'Todos'
        
        if not dados_filtrados:
            return jsonify({'success': False, 'message': f'Nenhum dado encontrado para a aba {nome_aba}'})
        
        # Preparar dados para Excel
        dados_excel = []
        for item in dados_filtrados:
            # Mapear status para categoria descritiva
            status_map = {
                'aviso': 'Peças no Corte Curvo - Pré-Montagem',
                'plano': 'Bloco Plano - Peças Sem PC',
                'curvo': 'Bloco Curvo - Peças Sem PC', 
                'critico': 'Peças que já passaram da Montagem'
            }
            
            categoria = status_map.get(item.get('status', ''), item.get('status', '').upper())
            
            dados_excel.append({
                'OP': item.get('op', ''),
                'PEÇA': item.get('peca', ''),
                'PROJETO': item.get('projeto', ''),
                'VEÍCULO': item.get('veiculo', ''),
                'LOCAL': item.get('local', ''),
                'SENSOR': item.get('sensor', ''),
                'ETAPA': item.get('etapa', ''),
                'PRIORIDADE': item.get('prioridade', ''),
                'CATEGORIA': categoria,
                'QUANTIDADE': item.get('quantidade', 1)
            })
        
        df = pd.DataFrame(dados_excel)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'dashboard_producao_{timestamp}.xlsx'
        
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl', sheet_name=nome_aba)
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
    app.run(host='0.0.0.0', port=5002, debug=False)