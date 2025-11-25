#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para testar conectividade com a pasta de rede
Execute este script para verificar se o sistema consegue acessar \\10.150.16.39\cnc-policarbonato
"""

import os
import sys

def test_network_access():
    """Testa o acesso à pasta de rede"""
    
    network_paths = [
        r"\\10.150.16.39\cnc-policarbonato",  # Caminho UNC da rede
        r"Z:\cnc-policarbonato",  # Drive mapeado (se existir)
    ]
    
    print("=== TESTE DE CONECTIVIDADE COM PASTA DE REDE ===\n")
    
    for path in network_paths:
        print(f"Testando: {path}")
        
        try:
            # Testar se o caminho existe
            if os.path.exists(path):
                print(f"✅ Caminho acessível: {path}")
                
                # Testar listagem de arquivos
                try:
                    files = os.listdir(path)
                    print(f"   📁 Arquivos encontrados: {len(files)}")
                    if files:
                        print(f"   📄 Primeiros arquivos: {files[:3]}")
                except Exception as e:
                    print(f"   ❌ Erro ao listar arquivos: {e}")
                
                # Testar criação de arquivo
                try:
                    test_file = os.path.join(path, "test_conexao.txt")
                    with open(test_file, 'w') as f:
                        f.write("Teste de conectividade")
                    
                    # Verificar se foi criado
                    if os.path.exists(test_file):
                        print(f"   ✅ Escrita bem-sucedida")
                        # Remover arquivo de teste
                        os.remove(test_file)
                        print(f"   🗑️ Arquivo de teste removido")
                    else:
                        print(f"   ❌ Arquivo não foi criado")
                        
                except Exception as e:
                    print(f"   ❌ Erro ao escrever: {e}")
                
            else:
                print(f"❌ Caminho não acessível: {path}")
                
        except Exception as e:
            print(f"❌ Erro geral: {e}")
        
        print("-" * 50)
    
    print("\n=== INSTRUÇÕES ===")
    print("Se nenhum caminho funcionou:")
    print("1. Verifique se o servidor 10.150.16.39 está online")
    print("2. Teste no Windows Explorer: \\\\10.150.16.39\\cnc-policarbonato")
    print("3. Mapeie como drive de rede:")
    print("   net use Z: \\\\10.150.16.39\\cnc-policarbonato /persistent:yes")
    print("4. Verifique credenciais de rede se necessário")

if __name__ == "__main__":
    test_network_access()
    input("\nPressione Enter para sair...")