import pandas as pd
import os
import json
import requests
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from loguru import logger

def atualizar_apontamentos():
    """Função para atualizar dados de apontamentos"""
    load_dotenv()
    
    try:
        DB_HOST = os.getenv('DB_HOST')
        DB_USER = os.getenv('DB_USER')
        DB_PASSWORD = os.getenv('DB_PSW')
        DB_PORT = os.getenv('DB_PORT')
        DB_NAME = os.getenv('DB_NAME')
        connection_string = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

        ontem = (datetime.today() - timedelta(days=3)).strftime('%y-%m-%d')
        hoje = datetime.today().strftime('%y-%m-%d')

        url = f"https://www.pplug.com.br/PP_pesquisa_api_vertco.php?etapa_aponta=TODAS&data_aponta={ontem}&data_fim={hoje}&token=acessoJARINUconsulta"
        headers = {'User-Agent': 'Mozilla/5.0'}

        logger.info(f"Iniciando a seção")
        time.sleep(5)
        session = requests.Session()
        response = session.get(url, headers=headers)
        response_clear = response.text[1:-1]
        data = json.loads(response_clear)

        logger.info(f"Criando o DataFrame")
        df = pd.DataFrame(data)
        df.columns = df.iloc[0]             # define colunas reais
        df = df.drop([0]).reset_index(drop=True)

        logger.info(f"Colunas disponíveis: {df.columns.tolist()}")  # Diagnóstico útil

        df['Veículo'] = df['MODELO'].apply(lambda x: ' '.join(x.split(' ')[2:]) if pd.notna(x) else None)

        # Converte a data e gera colunas adicionais
        df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True)
        df['PROJETO'] = df['MODELO'].apply(lambda x: x.split(' ')[0] if pd.notna(x) else '')
        df['ITEM'] = df['ITEM'].str[:3]
        df['Projeto + Peça'] = df['PROJETO'] + df['ITEM']
        df['CÓDIGO DE BARRAS'] = df['ITEM'] + df['OP'].astype(str)

        # Merge com dados de metros quadrados do banco
        engine = create_engine(connection_string)
        with engine.connect() as connection:
            query_m2 = text("SELECT projeto_peca, m2 FROM dados_uso_geral.metro_quadrado_pecas")
            df_m2 = pd.read_sql(query_m2, connection)
        df = pd.merge(left=df, right=df_m2.rename(columns={'projeto_peca': 'Projeto + Peça'}), on='Projeto + Peça', how='left')

        # Agora sim pode usá-la no df_apontamentos
        df_apontamentos = df[[
        'ID','DATA','ETAPA','USUÁRIO','COLABORADOR','CLIENTE','OP','PRIORIDADE','ITEM','CÓD',
        'MODELO','OBS','CABINE','ETAPA_BAIXA','MOTIVO','RESUMO','RTRP','PRODUTO','ETAPA_RESP','PROJETO','Veículo',
        'CÓDIGO DE BARRAS','m2','Projeto + Peça'
        ]]

        colunas_nomeadas = {
            'ID':'id',
            'DATA':'data',
            'ETAPA':'etapa',
            'USUÁRIO':'usuario',
            'COLABORADOR':'colaborador',
            'CLIENTE':'cliente',
            'OP':'op',
            'PRIORIDADE':'prioridade',
            'ITEM':'item',
            'CÓD':'serial',
            'MODELO':'modelo',
            'OBS':'obs',
            'CABINE':'cabine',
            'ETAPA_RESP':'etapa_resp',
            'MOTIVO':'motivo',
            'RESUMO':'resumo',
            'RTRP':'status',
            'PRODUTO':'produto',
            'PROJETO':'projeto',
            'Veículo':'veiculo',
            'CÓDIGO DE BARRAS':'codigo_de_barras',
            'm2':'m2',
            'Projeto + Peça':'projeto_peca',
            'ETAPA_BAIXA':'etapa_refugo'
        }

        df_final = df_apontamentos.rename(columns=colunas_nomeadas)

        # Tratamento de tipos
        df_final['id'] = df_final['id'].apply(lambda x: None if pd.isna(x) or x == '' else x).astype('Int64')
        df_final['op'] = df_final['op'].apply(lambda x: None if pd.isna(x) or x == '' else x).astype('Int64')
        df_final['data'] = pd.to_datetime(df_final['data'], errors='coerce')

        for col in ['etapa', 'usuario', 'colaborador', 'cliente', 'prioridade', 'item']:
            df_final[col] = df_final[col].replace("", None).astype(str)

        # Verificação e conexão
        logger.info("Verificando dados antes da inserção")

        with engine.connect() as connection:
            query = text(f"SELECT id, data FROM public.apontamento_pplug_jarinu")
            existing_data = pd.read_sql(query, connection)

        df_final['id'] = df_final['id'].fillna(0).astype('int64')
        existing_data['id'] = existing_data['id'].astype(int)
        df_final['data'] = pd.to_datetime(df_final['data'], errors='coerce')
        existing_data['data'] = pd.to_datetime(existing_data['data'], errors='coerce')
        df_final['op'] = df_final['op'].fillna(0).astype('int64')

        # Remove duplicatas
        df_novo = df_final[~df_final['id'].isin(existing_data['id']) & ~df_final['data'].isin(existing_data['data'])]
        df_novo.columns = df_novo.columns.str.strip()
        df_novo = df_novo.map(lambda x: None if x == '' else x)
        df_novo['id'] = df_novo['id'].astype(pd.Int64Dtype())
        df_novo['op'] = df_novo['op'].astype(pd.Int64Dtype())
        df_novo.drop_duplicates(subset=['id'], inplace=True)

        if not df_novo.empty:
            df_novo.to_sql('apontamento_pplug_jarinu', engine, schema='public', index=False, if_exists='append')
            logger.info(f"{len(df_novo)} novos registros inseridos.")
        else:
            logger.warning("Nenhum novo dado para inserir.")

        engine.dispose()

        return {"success": True, "message": "Dados atualizados com sucesso"}
        
    except Exception as e:
        logger.error(f"Erro durante o processo: {e}")
        return {"success": False, "message": str(e)}

if __name__ == "__main__":
    result = atualizar_apontamentos()
    print(result)