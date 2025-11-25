#!/bin/bash

# Script para montar a pasta da rede CNC Policarbonato
# Execute este script no servidor Linux antes de iniciar o sistema

# Criar diretório de montagem se não existir
sudo mkdir -p /mnt/cnc-policarbonato

# Montar a pasta da rede
# Substitua 'usuario' e 'senha' pelas credenciais corretas da rede
sudo mount -t cifs //10.150.16.39/cnc-policarbonato /mnt/cnc-policarbonato -o username=usuario,password=senha,uid=1000,gid=1000,iocharset=utf8

# Verificar se a montagem foi bem-sucedida
if mountpoint -q /mnt/cnc-policarbonato; then
    echo "Pasta da rede montada com sucesso em /mnt/cnc-policarbonato"
    ls -la /mnt/cnc-policarbonato
else
    echo "Erro ao montar a pasta da rede"
    echo "Criando pasta local como fallback..."
    mkdir -p /tmp/xmls
    chmod 777 /tmp/xmls
fi

# Dar permissões adequadas
sudo chmod 755 /mnt/cnc-policarbonato