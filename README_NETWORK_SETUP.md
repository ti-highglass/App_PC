# Configuração da Pasta de Rede para XMLs

## Problema Resolvido
O erro "Failed to fetch" na geração de XMLs estava ocorrendo porque o sistema tentava salvar os arquivos em pastas do SharePoint que não existem no servidor Linux.

## Solução Implementada
O sistema agora tenta salvar os XMLs nos seguintes locais (em ordem de prioridade):

1. `/mnt/cnc-policarbonato` - Pasta da rede montada
2. `//10.150.16.39/cnc-policarbonato` - Caminho direto da rede
3. `/tmp/xmls` - Pasta temporária local (fallback)
4. `~/xmls` - Pasta local do usuário (fallback)

## Configuração no Servidor Linux

### 1. Instalar dependências CIFS
```bash
sudo apt-get update
sudo apt-get install cifs-utils
```

### 2. Criar credenciais de rede
```bash
sudo nano /etc/cifs-credentials
```

Adicionar no arquivo:
```
username=SEU_USUARIO_REDE
password=SUA_SENHA_REDE
domain=SEU_DOMINIO
```

Proteger o arquivo:
```bash
sudo chmod 600 /etc/cifs-credentials
```

### 3. Configurar montagem automática
```bash
sudo nano /etc/fstab
```

Adicionar linha:
```
//10.150.16.39/cnc-policarbonato /mnt/cnc-policarbonato cifs credentials=/etc/cifs-credentials,uid=1000,gid=1000,iocharset=utf8,file_mode=0777,dir_mode=0777 0 0
```

### 4. Montar a pasta
```bash
sudo mkdir -p /mnt/cnc-policarbonato
sudo mount -a
```

### 5. Verificar montagem
```bash
df -h | grep cnc-policarbonato
ls -la /mnt/cnc-policarbonato
```

## Script Alternativo
Use o script `mount_network.sh` para montagem manual:

```bash
chmod +x mount_network.sh
sudo ./mount_network.sh
```

## Teste da Funcionalidade
1. Acesse o sistema web
2. Vá para a tela de otimização
3. Selecione algumas peças
4. Clique em "Gerar XML"
5. Verifique se os arquivos foram salvos em `/mnt/cnc-policarbonato`

## Troubleshooting

### Se a montagem falhar:
1. Verifique as credenciais em `/etc/cifs-credentials`
2. Teste conectividade: `ping 10.150.16.39`
3. Verifique se o serviço SMB está ativo no servidor de destino
4. Use o fallback local: os XMLs serão salvos em `/tmp/xmls`

### Logs de debug:
Os logs do sistema mostrarão onde os XMLs foram salvos:
```
DEBUG: XML gerado: arquivo.xml em /mnt/cnc-policarbonato
```

## Permissões
Certifique-se de que o usuário que executa o Flask tenha permissões de escrita na pasta montada:

```bash
sudo chown -R flask_user:flask_user /mnt/cnc-policarbonato
sudo chmod -R 755 /mnt/cnc-policarbonato
```

## Monitoramento
Para verificar se a pasta está sempre montada, adicione ao crontab:

```bash
crontab -e
```

Adicionar:
```
*/5 * * * * /bin/mountpoint -q /mnt/cnc-policarbonato || /bin/mount /mnt/cnc-policarbonato
```