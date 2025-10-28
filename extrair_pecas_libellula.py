import pandas as pd
import unicodedata

entrada = r"C:\Users\Pedro Torres\Downloads\pcs lib.xls"
saida = r"C:\Users\Pedro Torres\Downloads\pçs lib1.xlsx"

# Ler sem cabeçalho
df = pd.read_excel(entrada, header=None)

def normalizar(texto):
    """Remove acentos, coloca em minúsculo e trata None."""
    if pd.isna(texto) or texto is None:
        return ""
    texto = str(texto)
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower().strip()

nomes = []
espessuras = []

print("Analisando arquivo com células mescladas...")
print(f"Total de linhas: {len(df)}")
print(f"Total de colunas: {len(df.columns)}")

for i in range(len(df)):
    # Verificar colunas B, C, D (indices 1, 2, 3) para os títulos
    for j in [1, 2, 3]:  # Colunas B, C, D
        if j >= len(df.columns):
            continue
            
        celula = df.iloc[i, j]
        if pd.isna(celula):
            continue
            
        celula_norm = normalizar(celula)
        
        # Se encontrou "Nome da peça" nas colunas B, C ou D
        if any(termo in celula_norm for termo in ["nome da peca", "nome da peça", "nome peca", "nome peça"]):
            print(f"Título 'Nome da peça' encontrado na linha {i+1}, coluna {chr(65+j)}")
            
            # Buscar valores nas colunas E até AB (indices 4 até 27)
            valores_linha = []
            for col in range(4, min(28, len(df.columns))):  # E até AB
                valor = df.iloc[i, col]
                if not pd.isna(valor) and str(valor).strip():
                    valores_linha.append(str(valor).strip())
            
            if valores_linha:
                # Juntar todos os valores da linha (células mescladas)
                nome_completo = " ".join(valores_linha)
                nomes.append(nome_completo)
                print(f"✅ Nome encontrado: '{nome_completo}'")
        
        # Se encontrou "Espessura" nas colunas B, C ou D
        if "espessura" in celula_norm:
            print(f"Título 'Espessura' encontrado na linha {i+1}, coluna {chr(65+j)}")
            
            # Buscar valores nas colunas E até K (indices 4 até 10)
            valores_linha = []
            for col in range(4, min(11, len(df.columns))):  # E até K
                valor = df.iloc[i, col]
                if not pd.isna(valor) and str(valor).strip():
                    valores_linha.append(str(valor).strip())
            
            if valores_linha:
                # Juntar todos os valores da linha (células mescladas)
                espessura_completa = " ".join(valores_linha)
                espessuras.append(espessura_completa)
                print(f"✅ Espessura encontrada: '{espessura_completa}'")

print(f"\nTotal encontrado - Nomes: {len(nomes)}, Espessuras: {len(espessuras)}")

# Garantir mesmo tamanho de listas
tamanho = max(len(nomes), len(espessuras)) if nomes or espessuras else 0

if tamanho == 0:
    print("⚠️ Nenhum dado encontrado nas colunas especificadas!")
    print("\n=== MOSTRANDO ESTRUTURA PARA DEBUG ===")
    for i in range(min(10, len(df))):
        print(f"Linha {i+1}:")
        for j in range(min(10, len(df.columns))):
            valor = df.iloc[i, j]
            if not pd.isna(valor):
                print(f"  {chr(65+j)}{i+1}: '{valor}'")
    
    nomes = ["Nenhum nome encontrado"]
    espessuras = ["Nenhuma espessura encontrada"]
    tamanho = 1

nomes += [""] * (tamanho - len(nomes))
espessuras += [""] * (tamanho - len(espessuras))

saida_df = pd.DataFrame({
    "Nome da peça": nomes,
    "Espessura (mm)": espessuras
})

saida_df.to_excel(saida, index=False)
print(f"\n✅ Planilha gerada com sucesso: {saida}")