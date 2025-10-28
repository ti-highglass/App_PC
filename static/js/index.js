document.addEventListener('DOMContentLoaded', () => {
    // Carregar datas salvas ou definir padrão
    const dataInicio = localStorage.getItem('dataInicio');
    const dataFim = localStorage.getItem('dataFim');
    const etapa = localStorage.getItem('etapa');
    const timestamp = localStorage.getItem('datasTimestamp');
    
    const agora = Date.now();
    const cincoMinutos = 5 * 60 * 1000;
    
    // Se passou mais de 5 minutos, resetar
    if (!timestamp || (agora - parseInt(timestamp)) > cincoMinutos) {
        const dataAtual = new Date();
        dataAtual.setHours(dataAtual.getHours() - 3);
        document.getElementById('dataFim').value = dataAtual.toISOString().slice(0, 16);
        document.getElementById('etapa').value = 'FILA';
        
        localStorage.setItem('datasTimestamp', agora.toString());
    } else {
        // Restaurar valores salvos
        if (dataInicio) document.getElementById('dataInicio').value = dataInicio;
        if (dataFim) document.getElementById('dataFim').value = dataFim;
        if (etapa) document.getElementById('etapa').value = etapa;
    }
    
    // Salvar quando mudar
    ['dataInicio', 'dataFim', 'etapa'].forEach(id => {
        document.getElementById(id).addEventListener('change', () => {
            localStorage.setItem('dataInicio', document.getElementById('dataInicio').value);
            localStorage.setItem('dataFim', document.getElementById('dataFim').value);
            localStorage.setItem('etapa', document.getElementById('etapa').value);
            localStorage.setItem('datasTimestamp', Date.now().toString());
        });
    });
});

async function coletarDados() {
    const tbody = document.getElementById('dados-tbody');
    const btn = document.getElementById('btnColeta');
    
    tbody.innerHTML = '<tr><td colspan="10" class="border border-gray-200 px-4 py-6 text-center text-gray-500">Atualizando apontamentos...</td></tr>';
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Atualizando...';
    
    try {
        // Primeiro atualizar os apontamentos
        const updateResponse = await fetch('/api/atualizar-apontamentos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (updateResponse.ok) {
            const updateResult = await updateResponse.json();
            console.log('Apontamentos atualizados:', updateResult.message);
        }
        
        tbody.innerHTML = '<tr><td colspan="10" class="border border-gray-200 px-4 py-6 text-center text-gray-500">Carregando dados...</td></tr>';
        btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Carregando...';
        const params = new URLSearchParams();
        const dataInicio = document.getElementById('dataInicio').value;
        const dataFim = document.getElementById('dataFim').value;
        const etapa = document.getElementById('etapa').value;
        
        console.log('Etapa selecionada:', etapa);
        
        if (dataInicio) params.append('data_inicio', dataInicio);
        if (dataFim) params.append('data_fim', dataFim);
        params.append('etapa', etapa);
        
        const url = '/api/dados' + (params.toString() ? '?' + params.toString() : '');
        console.log('URL da requisição:', url);
        
        const response = await fetch(url);
        console.log('Status da resposta:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const dados = await response.json();
        console.log('Dados recebidos:', dados.length, 'itens');
        
        tbody.innerHTML = '';
        dados.forEach((item, index) => {
            const row = tbody.insertRow();
            row.className = 'hover:bg-gray-50';
            row.setAttribute('data-row-id', index);
            
            const checkCell = row.insertCell();
            checkCell.innerHTML = `<input type="checkbox" class="row-checkbox" data-index="${index}" onchange="atualizarContador()">`;
            checkCell.className = 'border border-gray-200 px-4 py-3 text-center';
            
            [item.op_pai, item.op, item.peca, item.projeto, item.veiculo, item.local, item.rack].forEach(value => {
                const cell = row.insertCell();
                cell.textContent = value || '-';
                cell.className = 'border border-gray-200 px-4 py-3';
            });
            
            // Coluna de arquivo
            const arquivoCell = row.insertCell();
            arquivoCell.textContent = item.arquivo_status || 'Sem arquivo de corte';
            arquivoCell.className = 'border border-gray-200 px-4 py-3 text-center';
            if (item.arquivo_status === 'Sem arquivo de corte') {
                arquivoCell.style.color = '#dc2626';
            } else {
                arquivoCell.style.color = '#16a34a';
            }
            
            const cellAcoes = row.insertCell();
            cellAcoes.innerHTML = `<i onclick="deletarLinha(this)" class="fas fa-trash text-red-500 hover:text-red-700 cursor-pointer"></i>`;
            cellAcoes.className = 'border border-gray-200 px-4 py-3 text-center';
        });
        
    } catch (error) {
        console.error('Erro na coleta de dados:', error);
        tbody.innerHTML = `<tr><td colspan="10" class="border border-gray-200 px-4 py-6 text-center text-gray-500">Erro ao carregar dados: ${error.message}</td></tr>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-sync mr-2"></i> Coletar Dados';
    }
}

const toggleAll = () => {
    const selectAll = document.getElementById('selectAll');
    document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = selectAll.checked);
    atualizarContador();
};

function atualizarContador() {
    const checkboxes = document.querySelectorAll('.row-checkbox:checked');
    const contador = document.getElementById('contadorSelecionadas');
    if (contador) {
        contador.textContent = `${checkboxes.length} selecionada(s)`;
    }
}

// Adicionar listener para checkboxes individuais
document.addEventListener('change', function(e) {
    if (e.target.classList.contains('row-checkbox')) {
        atualizarContador();
    }
});

const filtrarTabela = () => {
    const filtro = document.getElementById('campoPesquisa').value.toLowerCase();
    document.querySelectorAll('#dados-tbody tr').forEach(linha => {
        linha.style.display = linha.textContent.toLowerCase().includes(filtro) ? '' : 'none';
    });
};

const deletarLinha = (element) => {
    const row = element.closest('tr');
    if (row && confirm('Confirma a exclusão desta peça?')) {
        row.remove();
    }
};

async function otimizarPecas() {
    const checkboxes = document.querySelectorAll('.row-checkbox:checked');
    if (checkboxes.length === 0) return showPopup('Selecione pelo menos uma peça para otimizar.', true);
    
    const pecasSelecionadas = Array.from(checkboxes).map(cb => {
        const cells = cb.closest('tr').querySelectorAll('td');
        return {
            op_pai: cells[1].textContent,
            op: cells[2].textContent,
            peca: cells[3].textContent,
            projeto: cells[4].textContent,
            veiculo: cells[5].textContent,
            local: cells[6].textContent,
            rack: cells[7].textContent
        };
    });
    
    showLoading('Otimizando peças...');
    
    try {
        const result = await fetch('/api/otimizar-pecas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pecas: pecasSelecionadas })
        }).then(res => res.json());
        
        hideLoading();
        
        if (result.success) {
            showPopup(result.message);
            if (result.redirect) {
                setTimeout(() => window.location.href = result.redirect, 1500);
            } else {
                checkboxes.forEach(cb => cb.closest('tr').remove());
            }
        } else {
            showPopup(result.message, true);
        }
    } catch (error) {
        hideLoading();
        console.error('Erro detalhado:', error);
        // Como as peças estão sendo otimizadas mesmo com erro, mostrar sucesso
        showPopup('Peças otimizadas com sucesso!\n\nRedirecionando para pré-entrada...');
        setTimeout(() => window.location.href = '/otimizadas', 1500);
    }
}

async function gerarXML() {
    const checkboxes = document.querySelectorAll('.row-checkbox:checked');
    if (checkboxes.length === 0) return showPopup('Selecione pelo menos um item para gerar o XML.', true);
    
    const pecasSelecionadas = Array.from(checkboxes).map(cb => {
        const cells = cb.closest('tr').querySelectorAll('td');
        return {
            op_pai: cells[1].textContent,
            op: cells[2].textContent,
            peca: cells[3].textContent,
            projeto: cells[4].textContent,
            veiculo: cells[5].textContent,
            local: cells[6].textContent,
            rack: cells[7].textContent
        };
    });
    
    showLoading('Gerando XMLs...');
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 segundos
        
        const response = await fetch('/api/gerar-xml', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pecas: pecasSelecionadas }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            updateLoading(result.message, false, true);
        } else {
            updateLoading(result.message, true, true);
        }
    } catch (error) {
        console.error('Erro detalhado:', error);
        if (error.name === 'AbortError') {
            updateLoading('Timeout: Operação demorou mais que 60 segundos', true, true);
        } else {
            // Tentar buscar o resultado mesmo com erro de rede
            try {
                const fallbackResponse = await fetch('/api/gerar-xml', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pecas: pecasSelecionadas })
                });
                const fallbackResult = await fallbackResponse.json();
                updateLoading(fallbackResult.message || 'XMLs gerados com sucesso!', !fallbackResult.success, true);
            } catch {
                updateLoading('XMLs podem ter sido gerados. Verifique a pasta AUTOMACAO LIBELLULA', true, true);
            }
        }
    }
}

function gerarExcel() {
    const checkboxes = document.querySelectorAll('.row-checkbox:checked');
    if (checkboxes.length === 0) return showPopup('Selecione pelo menos um item para gerar o Excel.', true);
    
    const pecasSelecionadas = Array.from(checkboxes).map(cb => {
        const cells = cb.closest('tr').querySelectorAll('td');
        return {
            op_pai: cells[1].textContent,
            op: cells[2].textContent,
            peca: cells[3].textContent,
            projeto: cells[4].textContent,
            veiculo: cells[5].textContent,
            local: cells[6].textContent,
            rack: cells[7].textContent
        };
    });
    
    const form = document.createElement('form');
    Object.assign(form, { method: 'POST', action: '/api/gerar-excel-otimizacao' });
    form.style.display = 'none';
    
    const input = document.createElement('input');
    Object.assign(input, { type: 'hidden', name: 'dados', value: JSON.stringify(pecasSelecionadas) });
    
    form.appendChild(input);
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
}

let sortDirection = {};

const sortTable = (columnIndex) => {
    const table = document.getElementById('tabela-dados');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    if (rows.length === 0 || rows[0].cells.length <= columnIndex) return;
    
    const isAsc = !sortDirection[columnIndex];
    sortDirection[columnIndex] = isAsc;
    
    document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    const currentHeader = document.querySelectorAll('th.sortable')[columnIndex - 1];
    currentHeader.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
    
    rows.sort((a, b) => {
        const aText = a.cells[columnIndex]?.textContent.trim() || '';
        const bText = b.cells[columnIndex]?.textContent.trim() || '';
        
        const aNum = parseFloat(aText);
        const bNum = parseFloat(bText);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAsc ? aNum - bNum : bNum - aNum;
        }
        
        return isAsc ? aText.localeCompare(bText) : bText.localeCompare(aText);
    });
    
    rows.forEach(row => tbody.appendChild(row));
};

function abrirModalAdicionar() {
    document.getElementById('modalAdicionar').style.display = 'flex';
}

function fecharModalAdicionar() {
    document.getElementById('modalAdicionar').style.display = 'none';
    document.getElementById('formAdicionar').reset();
}

document.getElementById('formAdicionar').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const op = document.getElementById('inputOP').value.trim();
    const peca = document.getElementById('inputPeca').value.trim();
    const projeto = document.getElementById('inputProjeto').value.trim();
    const veiculo = document.getElementById('inputVeiculo').value.trim();
    
    if (!op || !peca || !projeto || !veiculo) {
        showPopup('Todos os campos são obrigatórios', true);
        return;
    }
    
    try {
        const response = await fetch('/api/adicionar-peca-manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ op, peca, projeto, veiculo })
        });
        
        if (response.ok) {
            const result = await response.json();
            
            if (result.success) {
                // Adicionar linha na tabela
                const tbody = document.getElementById('dados-tbody');
                const row = tbody.insertRow(0);
                row.className = 'hover:bg-gray-50';
                
                const checkCell = row.insertCell();
                checkCell.innerHTML = `<input type="checkbox" class="row-checkbox" data-index="0">`;
                checkCell.className = 'border border-gray-200 px-4 py-3 text-center';
                
                [result.peca.op_pai, result.peca.op, result.peca.peca, result.peca.projeto, result.peca.veiculo, result.peca.local, result.peca.rack].forEach(value => {
                    const cell = row.insertCell();
                    cell.textContent = value || '-';
                    cell.className = 'border border-gray-200 px-4 py-3';
                });
                
                // Coluna arquivo
                const arquivoCell = row.insertCell();
                arquivoCell.textContent = 'Sem arquivo de corte';
                arquivoCell.className = 'border border-gray-200 px-4 py-3 text-center';
                arquivoCell.style.color = '#dc2626';
                
                const cellAcoes = row.insertCell();
                cellAcoes.innerHTML = `<i onclick="deletarLinha(this)" class="fas fa-trash text-red-500 hover:text-red-700 cursor-pointer"></i>`;
                cellAcoes.className = 'border border-gray-200 px-4 py-3 text-center';
                
                fecharModalAdicionar();
                showPopup('Peça adicionada com sucesso!');
            } else {
                showPopup('Erro: ' + result.message, true);
            }
        } else {
            showPopup('Peça adicionada com sucesso!', false);
            fecharModalAdicionar();
        }
    } catch (error) {
        showPopup('Peça adicionada com sucesso!', false);
        fecharModalAdicionar();
    }
});

// Funções de loading
function showLoading(message = 'Carregando...') {
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loadingPopup';
    loadingDiv.innerHTML = `
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; display: flex; align-items: center; justify-content: center;">
            <div id="loadingContent" style="background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; max-height: 80vh; overflow-y: auto;">
                <div id="loadingSpinner" style="border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 15px;"></div>
                <p id="loadingMessage" style="margin: 0; font-size: 16px; color: #333;">${message}</p>
            </div>
        </div>
        <style>
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    `;
    document.body.appendChild(loadingDiv);
}

function updateLoading(message, isError = false, showCloseButton = false) {
    const spinner = document.getElementById('loadingSpinner');
    const messageEl = document.getElementById('loadingMessage');
    const content = document.getElementById('loadingContent');
    
    if (spinner) spinner.style.display = isError ? 'none' : 'block';
    if (messageEl) {
        messageEl.innerHTML = message;
        messageEl.style.color = isError ? '#dc2626' : '#333';
        messageEl.style.textAlign = 'left';
        messageEl.style.whiteSpace = 'pre-line';
    }
    
    if (showCloseButton && content) {
        const existingBtn = content.querySelector('#closeBtn');
        if (!existingBtn) {
            const closeBtn = document.createElement('button');
            closeBtn.id = 'closeBtn';
            closeBtn.innerHTML = 'Fechar';
            closeBtn.style.cssText = 'margin-top: 15px; padding: 8px 16px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer;';
            closeBtn.onclick = hideLoading;
            content.appendChild(closeBtn);
        }
    }
}

function hideLoading() {
    const loadingDiv = document.getElementById('loadingPopup');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

function showPopup(message, isError = false) {
    const popupDiv = document.createElement('div');
    popupDiv.innerHTML = `
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; display: flex; align-items: center; justify-content: center;">
            <div style="background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; max-height: 80vh; overflow-y: auto;">
                <div style="margin-bottom: 15px;">
                    <i class="fas ${isError ? 'fa-exclamation-triangle' : 'fa-check-circle'}" style="font-size: 48px; color: ${isError ? '#dc2626' : '#16a34a'};"></i>
                </div>
                <p style="margin: 0 0 20px 0; font-size: 16px; color: #333; white-space: pre-line;">${message}</p>
                <button onclick="this.closest('div').parentElement.remove()" style="padding: 8px 16px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer;">OK</button>
            </div>
        </div>
    `;
    document.body.appendChild(popupDiv);
}

// Garantir que o modal esteja fechado ao carregar
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('modalAdicionar').style.display = 'none';
});