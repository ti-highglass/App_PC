let todosLotes = [];

document.addEventListener('DOMContentLoaded', async () => {
    // Carregar lotes
    try {
        console.log('Iniciando carregamento de lotes...');
        const response = await fetch('/api/lotes');
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const lotes = await response.json();
        console.log('Lotes recebidos:', lotes);
        
        todosLotes = lotes;
        preencherOpcoesLotes(lotes);
        
    } catch (error) {
        console.error('Erro ao carregar lotes:', error);
    }
    
    // Carregar contador de locais
    carregarContadorLocais();
    
    // Fechar dropdown ao clicar fora
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.dropdown-container')) {
            fecharDropdown();
        }
    });
});

function preencherOpcoesLotes(lotes) {
    const loteOptions = document.getElementById('loteOptions');
    loteOptions.innerHTML = '<div class="dropdown-option" data-value="" onclick="selecionarLote(\'\', \'Selecionar lote\')">Selecionar lote</div>';
    
    if (lotes && lotes.length > 0) {
        lotes.forEach(lote => {
            const option = document.createElement('div');
            option.className = 'dropdown-option';
            option.setAttribute('data-value', lote.id_lote);
            option.textContent = lote.display;
            option.onclick = () => selecionarLote(lote.id_lote, lote.display);
            loteOptions.appendChild(option);
        });
        console.log('Lotes adicionados ao dropdown:', lotes.length);
    } else {
        console.log('Nenhum lote encontrado');
    }
}

function toggleDropdown() {
    const dropdown = document.getElementById('loteDropdown');
    const container = document.querySelector('.dropdown-container');
    
    if (dropdown.style.display === 'none' || !dropdown.style.display) {
        dropdown.style.display = 'block';
        container.classList.add('open');
        document.getElementById('loteFilter').focus();
    } else {
        fecharDropdown();
    }
}

function fecharDropdown() {
    const dropdown = document.getElementById('loteDropdown');
    const container = document.querySelector('.dropdown-container');
    dropdown.style.display = 'none';
    container.classList.remove('open');
    document.getElementById('loteFilter').value = '';
    preencherOpcoesLotes(todosLotes);
}

function selecionarLote(valor, texto) {
    document.getElementById('lote').value = valor;
    document.getElementById('loteSearch').value = texto;
    
    // Atualizar seleção visual
    document.querySelectorAll('.dropdown-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    
    const optionSelecionada = document.querySelector(`[data-value="${valor}"]`);
    if (optionSelecionada) {
        optionSelecionada.classList.add('selected');
    }
    
    fecharDropdown();
    localStorage.setItem('lote', valor);
}

function filtrarLotes() {
    const filtro = document.getElementById('loteFilter').value.toLowerCase();
    const lotesFiltrados = todosLotes.filter(lote => 
        lote.display.toLowerCase().includes(filtro) || 
        lote.id_lote.toLowerCase().includes(filtro)
    );
    preencherOpcoesLotes(lotesFiltrados);
}

async function coletarDados() {
    const tbody = document.getElementById('dados-tbody');
    const btn = document.getElementById('btnColeta');
    
    tbody.innerHTML = '<tr><td colspan="10" class="border border-gray-200 px-4 py-6 text-center text-gray-500">Atualizando apontamentos...</td></tr>';
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Atualizando...';
    
    try {
        const params = new URLSearchParams();
        const lote = document.getElementById('lote').value;
        
        console.log('Lote selecionado:', lote);
        
        if (lote) params.append('lote', lote);
        
        const url = '/api/dados' + (params.toString() ? '?' + params.toString() : '');
        console.log('URL da requisição:', url);
        
        const response = await fetch(url);
        console.log('Status da resposta:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const resultado = await response.json();
        
        // Verificar se há erro na resposta
        if (resultado.error) {
            throw new Error(resultado.error);
        }
        
        // Verificar se é o novo formato com dados e peças sem local
        let dados, pecasSemLocal = [];
        if (resultado.dados && Array.isArray(resultado.dados)) {
            dados = resultado.dados;
            pecasSemLocal = resultado.pecas_sem_local || [];
        } else if (Array.isArray(resultado)) {
            // Formato antigo - compatibilidade
            dados = resultado;
        } else {
            throw new Error('Formato de resposta inválido');
        }
        
        console.log('Dados recebidos:', dados.length, 'itens');
        console.log('Peças sem local:', pecasSemLocal.length, 'itens');
        
        tbody.innerHTML = '';
        dados.forEach((item, index) => {
            const row = tbody.insertRow();
            row.className = 'hover:bg-gray-50';
            row.setAttribute('data-row-id', index);
            row.setAttribute('data-lote-vd', item.lote_vd || '');
            row.setAttribute('data-lote-pc', item.lote_pc || '');
            
            const checkCell = row.insertCell();
            checkCell.innerHTML = `<input type="checkbox" class="row-checkbox" data-index="${index}" onchange="atualizarContador()">`;
            checkCell.className = 'border border-gray-200 px-4 py-3 text-center';
            
            [item.op, item.peca, item.projeto, item.veiculo, item.local, item.sensor].forEach(value => {
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
            cellAcoes.innerHTML = `
                <i onclick="editarLinha(this)" class="fas fa-edit text-blue-500 hover:text-blue-700 cursor-pointer mr-2" title="Editar"></i>
                <i onclick="deletarLinha(this)" class="fas fa-trash text-red-500 hover:text-red-700 cursor-pointer" title="Excluir"></i>
            `;
            cellAcoes.className = 'border border-gray-200 px-4 py-3 text-center';
        });
        
        // Mostrar alerta para peças sem local disponível
        if (pecasSemLocal.length > 0) {
            mostrarAlertaPecasSemLocal(pecasSemLocal);
        }
        
    } catch (error) {
        console.error('Erro na coleta de dados:', error);
        tbody.innerHTML = `<tr><td colspan="9" class="border border-gray-200 px-4 py-6 text-center text-gray-500">Erro ao carregar dados: ${error.message}</td></tr>`;
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

// Listener para mudança do sensor no modal de edição
document.getElementById('editSensor').addEventListener('input', async function() {
    const sensor = this.value.trim();
    const projeto = document.getElementById('editProjeto').value.trim();
    const peca = document.getElementById('editPeca').value.trim();
    
    if (projeto && peca) {
        try {
            const response = await fetch(`/api/buscar-arquivo?projeto=${encodeURIComponent(projeto)}&peca=${encodeURIComponent(peca)}&sensor=${encodeURIComponent(sensor)}`);
            if (response.ok) {
                const result = await response.json();
                const statusElement = document.getElementById('arquivoStatus');
                if (statusElement) {
                    if (result.encontrado) {
                        statusElement.textContent = `✓ Arquivo encontrado: ${result.nome_arquivo}`;
                        statusElement.style.color = '#16a34a';
                    } else {
                        statusElement.textContent = '✗ Arquivo não encontrado';
                        statusElement.style.color = '#dc2626';
                    }
                }
            }
        } catch (error) {
            console.log('Erro ao buscar arquivo:', error);
        }
    }
});

const filtrarTabela = () => {
    const filtro = document.getElementById('campoPesquisa').value.toLowerCase();
    document.querySelectorAll('#dados-tbody tr').forEach(linha => {
        const cells = linha.querySelectorAll('td');
        if (cells.length > 1) {
            const op = cells[1].textContent.toLowerCase();
            const peca = cells[2].textContent.toLowerCase();
            const projeto = cells[3].textContent.toLowerCase();
            const veiculo = cells[4].textContent.toLowerCase();
            const local = cells[5].textContent.toLowerCase();
            const sensor = cells[6].textContent.toLowerCase();
            
            // Buscar por peça+op+camada (formato: TSP12345PC)
            const pecaOpCamada = `${peca}${op}pc`;
            
            const match = linha.textContent.toLowerCase().includes(filtro) ||
                         pecaOpCamada.includes(filtro);
            
            linha.style.display = match ? '' : 'none';
        }
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
    
    const dataCorte = document.getElementById('dataCorte').value;
    if (!dataCorte) return showPopup('Selecione a data de corte.', true);
    
    const pecasSelecionadas = Array.from(checkboxes).map(cb => {
        const row = cb.closest('tr');
        const cells = row.querySelectorAll('td');
        return {
            op: cells[1].textContent,
            peca: cells[2].textContent,
            projeto: cells[3].textContent,
            veiculo: cells[4].textContent,
            local: cells[5].textContent,
            sensor: cells[6].textContent,
            rack: 'SLOT',
            lote_vd: row.getAttribute('data-lote-vd') || '',
            lote_pc: row.getAttribute('data-lote-pc') || '',
            data_corte: dataCorte
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
            carregarContadorLocais();
            if (result.redirect) {
                setTimeout(() => window.location.href = result.redirect, 1500);
            } else {
                checkboxes.forEach(cb => cb.closest('tr').remove());
            }
        } else {
            // Mostrar erro sem bloquear interface
            const alertDiv = document.createElement('div');
            alertDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #fee2e2; border: 1px solid #fecaca; color: #991b1b; padding: 16px; border-radius: 8px; max-width: 400px; z-index: 1000; box-shadow: 0 4px 6px rgba(0,0,0,0.1);';
            alertDiv.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <strong>Erro:</strong><br>
                        ${result.message}
                    </div>
                    <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; font-size: 18px; cursor: pointer; color: #991b1b; margin-left: 10px;">&times;</button>
                </div>
            `;
            document.body.appendChild(alertDiv);
            
            // Auto-remover após 10 segundos
            setTimeout(() => {
                if (alertDiv.parentElement) {
                    alertDiv.remove();
                }
            }, 10000);
        }
    } catch (error) {
        hideLoading();
        console.error('Erro detalhado:', error);
        showPopup('Erro na comunicação com o servidor: ' + error.message, true);
    }
}

async function gerarXML() {
    const checkboxes = document.querySelectorAll('.row-checkbox:checked');
    if (checkboxes.length === 0) return showPopup('Selecione pelo menos um item para gerar o XML.', true);
    
    const pecasSelecionadas = Array.from(checkboxes).map(cb => {
        const row = cb.closest('tr');
        const cells = row.querySelectorAll('td');
        return {
            op: cells[1].textContent,
            peca: cells[2].textContent,
            projeto: cells[3].textContent,
            veiculo: cells[4].textContent,
            local: cells[5].textContent,
            sensor: cells[6].textContent,
            rack: 'SLOT',
            lote_vd: row.getAttribute('data-lote-vd') || '',
            lote_pc: row.getAttribute('data-lote-pc') || ''
        };
    });
    
    showLoading('Gerando XMLs...');
    
    try {
        const response = await fetch('/api/gerar-xml', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pecas: pecasSelecionadas })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            updateLoading(result.message, false, true);
            
            // Se tem download, iniciar download
            if (result.download && result.filename) {
                setTimeout(() => {
                    window.location.href = `/download-xml/${result.filename}`;
                }, 1000);
            }
        } else {
            updateLoading(result.message, true, true);
        }
    } catch (error) {
        console.error('Erro detalhado:', error);
        updateLoading('Erro ao gerar XMLs: ' + error.message, true, true);
    }
}

function gerarExcel() {
    const checkboxes = document.querySelectorAll('.row-checkbox:checked');
    if (checkboxes.length === 0) return showPopup('Selecione pelo menos um item para gerar o Excel.', true);
    
    const pecasSelecionadas = Array.from(checkboxes).map(cb => {
        const row = cb.closest('tr');
        const cells = row.querySelectorAll('td');
        return {
            op: cells[1].textContent,
            peca: cells[2].textContent,
            projeto: cells[3].textContent,
            veiculo: cells[4].textContent,
            local: cells[5].textContent,
            sensor: cells[6].textContent,
            rack: 'SLOT',
            lote_vd: row.getAttribute('data-lote-vd') || '',
            lote_pc: row.getAttribute('data-lote-pc') || ''
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
    selecionarModo('manual');
}

function fecharModalAdicionar() {
    document.getElementById('modalAdicionar').style.display = 'none';
    document.getElementById('formAdicionar').reset();
    document.getElementById('inputExcel').value = '';
    document.getElementById('previewContainer').style.display = 'none';
    document.getElementById('btnProcessarExcel').style.display = 'none';
}

function selecionarModo(modo) {
    const btnManual = document.getElementById('btnManual');
    const btnExcel = document.getElementById('btnExcelImport');
    const modoManual = document.getElementById('modoManual');
    const modoExcel = document.getElementById('modoExcel');
    
    if (modo === 'manual') {
        btnManual.className = 'btn-modal btn-blue-modal';
        btnExcel.className = 'btn-modal btn-gray';
        modoManual.style.display = 'block';
        modoExcel.style.display = 'none';
    } else {
        btnManual.className = 'btn-modal btn-gray';
        btnExcel.className = 'btn-modal btn-blue-modal';
        modoManual.style.display = 'none';
        modoExcel.style.display = 'block';
        configurarDragDrop();
    }
}

function configurarDragDrop() {
    const dropZone = document.getElementById('dropZone');
    const inputExcel = document.getElementById('inputExcel');
    
    dropZone.addEventListener('click', () => inputExcel.click());
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#3b82f6';
        dropZone.style.backgroundColor = '#eff6ff';
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = '#d1d5db';
        dropZone.style.backgroundColor = 'transparent';
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#d1d5db';
        dropZone.style.backgroundColor = 'transparent';
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            inputExcel.files = files;
            previewExcel();
        }
    });
    
    inputExcel.addEventListener('change', previewExcel);
}

document.getElementById('formAdicionar').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const op = document.getElementById('inputOP').value.trim();
    const peca = document.getElementById('inputPeca').value.trim();
    const projeto = document.getElementById('inputProjeto').value.trim();
    const veiculo = document.getElementById('inputVeiculo').value.trim();
    const sensor = document.getElementById('inputSensor').value.trim();
    
    if (!op || !peca || !projeto || !veiculo) {
        showPopup('Todos os campos são obrigatórios', true);
        return;
    }
    
    try {
        const response = await fetch('/api/adicionar-peca-manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ op, peca, projeto, veiculo, sensor })
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
                
                [result.peca.op, result.peca.peca, result.peca.projeto, result.peca.veiculo, result.peca.local, result.peca.sensor || sensor || '-'].forEach(value => {
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
                cellAcoes.innerHTML = `
                    <i onclick="editarLinha(this)" class="fas fa-edit text-blue-500 hover:text-blue-700 cursor-pointer mr-2" title="Editar"></i>
                    <i onclick="deletarLinha(this)" class="fas fa-trash text-red-500 hover:text-red-700 cursor-pointer" title="Excluir"></i>
                `;
                cellAcoes.className = 'border border-gray-200 px-4 py-3 text-center';
                
                fecharModalAdicionar();
                carregarContadorLocais(); // Atualizar contador após adicionar
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
                <button onclick="removePopup(this)" style="padding: 8px 16px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer;">OK</button>
            </div>
        </div>
    `;
    document.body.appendChild(popupDiv);
}

function removePopup(button) {
    const popup = button.closest('div').parentElement;
    popup.remove();
    // Garantir que não há elementos bloqueando a interface
    document.body.style.pointerEvents = 'auto';
    document.body.style.overflow = 'auto';
}

function mostrarAlertaPecasSemLocal(pecasSemLocal) {
    let mensagem = `⚠️ ATENÇÃO: ${pecasSemLocal.length} peça(s) não puderam ser coletadas por falta de slots disponíveis:\n\n`;
    
    // Mostrar até 10 peças na mensagem
    const pecasParaMostrar = pecasSemLocal.slice(0, 10);
    pecasParaMostrar.forEach(peca => {
        mensagem += `• OP ${peca.op} - ${peca.peca} (${peca.projeto})\n`;
    });
    
    if (pecasSemLocal.length > 10) {
        mensagem += `\n... e mais ${pecasSemLocal.length - 10} peça(s)\n`;
    }
    
    mensagem += `\n💡 Solução: Libere slots no estoque ou aumente a capacidade dos slots existentes.`;
    
    const alertDiv = document.createElement('div');
    alertDiv.innerHTML = `
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; display: flex; align-items: center; justify-content: center;">
            <div style="background: white; padding: 25px; border-radius: 12px; text-align: left; box-shadow: 0 8px 16px rgba(0,0,0,0.15); max-width: 600px; max-height: 80vh; overflow-y: auto; border-left: 6px solid #f59e0b;">
                <div style="display: flex; align-items: center; margin-bottom: 20px;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 32px; color: #f59e0b; margin-right: 15px;"></i>
                    <h3 style="margin: 0; font-size: 20px; color: #333; font-weight: bold;">Peças Não Coletadas</h3>
                </div>
                <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #fbbf24;">
                    <p style="margin: 0; font-size: 14px; color: #92400e; font-weight: 500;">
                        <i class="fas fa-info-circle" style="margin-right: 8px;"></i>
                        Estas peças não aparecem na tabela porque todos os slots estão cheios.
                    </p>
                </div>
                <div style="max-height: 300px; overflow-y: auto; margin-bottom: 20px;">
                    <pre style="margin: 0; font-size: 14px; color: #374151; white-space: pre-line; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.5;">${mensagem}</pre>
                </div>
                <div style="text-align: center;">
                    <button onclick="fecharAlertaPecasSemLocal(this)" style="padding: 12px 24px; background: #f59e0b; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 16px; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#d97706'" onmouseout="this.style.backgroundColor='#f59e0b'">Entendi</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(alertDiv);
}

function fecharAlertaPecasSemLocal(button) {
    const alertDiv = button.closest('div').parentElement;
    alertDiv.remove();
    
    // Garantir que a interface está desbloqueada
    document.body.style.pointerEvents = 'auto';
    document.body.style.overflow = 'auto';
    
    // Remover qualquer overlay que possa estar bloqueando
    const overlays = document.querySelectorAll('[style*="position: fixed"][style*="z-index"]');
    overlays.forEach(overlay => {
        if (overlay !== alertDiv && overlay.style.zIndex >= 9999) {
            overlay.remove();
        }
    });
}

async function limparPecasManuais() {
    if (!confirm('ATENÇÃO: Esta ação irá limpar todas as peças manuais da tabela pc_manuais.\n\nDeseja continuar?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/limpar-pecas-manuais', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showPopup(result.message);
        } else {
            showPopup(result.message, true);
        }
    } catch (error) {
        showPopup('Erro ao limpar peças manuais: ' + error.message, true);
    }
}



async function previewExcel() {
    const fileInput = document.getElementById('inputExcel');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showLoading('Processando arquivo Excel...');
        
        const response = await fetch('/api/importar-excel-pecas', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            mostrarPreview(result.pecas);
            document.getElementById('btnProcessarExcel').disabled = false;
        } else {
            showPopup(result.message, true);
        }
    } catch (error) {
        hideLoading();
        showPopup('Erro ao processar arquivo: ' + error.message, true);
    }
}

function mostrarPreview(pecas) {
    const previewBody = document.getElementById('previewTableBody');
    const previewContainer = document.getElementById('previewContainer');
    const btnProcessar = document.getElementById('btnProcessarExcel');
    
    previewBody.innerHTML = '';
    
    pecas.slice(0, 10).forEach(peca => {
        const row = previewBody.insertRow();
        [peca.op, peca.peca, peca.projeto, peca.veiculo, peca.sensor, peca.local, peca.arquivo_status].forEach(value => {
            const cell = row.insertCell();
            cell.textContent = (value && value !== 'nan' && value !== 'NaN') ? value : '-';
            cell.className = 'border px-2 py-1';
        });
    });
    
    previewContainer.style.display = 'block';
    btnProcessar.style.display = 'inline-block';
    
    window.pecasImportadas = pecas;
}

async function processarExcel() {
    if (!window.pecasImportadas || window.pecasImportadas.length === 0) {
        showPopup('Nenhuma peça para processar', true);
        return;
    }
    
    try {
        const tbody = document.getElementById('dados-tbody');
        
        if (tbody.children.length === 1 && tbody.children[0].children.length === 1) {
            tbody.innerHTML = '';
        }
        
        let adicionadas = 0;
        
        window.pecasImportadas.forEach((peca, index) => {
            const row = tbody.insertRow();
            row.className = 'hover:bg-gray-50';
            row.setAttribute('data-row-id', tbody.children.length + index);
            
            const checkCell = row.insertCell();
            checkCell.innerHTML = `<input type="checkbox" class="row-checkbox" data-index="${tbody.children.length + index}" onchange="atualizarContador()">`;
            checkCell.className = 'border border-gray-200 px-4 py-3 text-center';
            
            [peca.op, peca.peca, peca.projeto, peca.veiculo, peca.local, peca.sensor].forEach(value => {
                const cell = row.insertCell();
                cell.textContent = (value && value !== 'nan' && value !== 'NaN') ? value : '-';
                cell.className = 'border border-gray-200 px-4 py-3';
            });
            
            const arquivoCell = row.insertCell();
            arquivoCell.textContent = peca.arquivo_status || 'Sem arquivo de corte';
            arquivoCell.className = 'border border-gray-200 px-4 py-3 text-center';
            if (peca.arquivo_status === 'Sem arquivo de corte') {
                arquivoCell.style.color = '#dc2626';
            } else {
                arquivoCell.style.color = '#16a34a';
            }
            
            const cellAcoes = row.insertCell();
            cellAcoes.innerHTML = `
                <i onclick="editarLinha(this)" class="fas fa-edit text-blue-500 hover:text-blue-700 cursor-pointer mr-2" title="Editar"></i>
                <i onclick="deletarLinha(this)" class="fas fa-trash text-red-500 hover:text-red-700 cursor-pointer" title="Excluir"></i>
            `;
            cellAcoes.className = 'border border-gray-200 px-4 py-3 text-center';
            
            adicionadas++;
        });
        
        fecharModalAdicionar();
        showPopup(`${adicionadas} peça(s) importada(s) com sucesso!`);
        
    } catch (error) {
        showPopup('Erro ao processar peças: ' + error.message, true);
    }
}

async function editarLinha(element) {
    const row = element.closest('tr');
    const cells = row.querySelectorAll('td');
    
    document.getElementById('editIndex').value = row.getAttribute('data-row-id') || row.rowIndex;
    document.getElementById('editOP').value = cells[1].textContent;
    document.getElementById('editPeca').value = cells[2].textContent;
    document.getElementById('editProjeto').value = cells[3].textContent;
    document.getElementById('editVeiculo').value = cells[4].textContent;
    document.getElementById('editSensor').value = cells[6].textContent === '-' ? '' : cells[6].textContent;
    
    // Mostrar status atual do arquivo
    const statusElement = document.getElementById('arquivoStatus');
    const arquivoAtual = cells[7].textContent;
    if (arquivoAtual === 'Sem arquivo de corte') {
        statusElement.textContent = '✗ Nenhum arquivo encontrado';
        statusElement.style.color = '#dc2626';
    } else {
        statusElement.textContent = `✓ Arquivo atual: ${arquivoAtual}`;
        statusElement.style.color = '#16a34a';
    }
    
    window.linhaEditando = row;
    document.getElementById('modalEditar').style.display = 'flex';
}

function fecharModalEditar() {
    document.getElementById('modalEditar').style.display = 'none';
    document.getElementById('formEditar').reset();
    window.linhaEditando = null;
}

document.getElementById('formEditar').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    if (!window.linhaEditando) return;
    
    const op = document.getElementById('editOP').value.trim();
    const peca = document.getElementById('editPeca').value.trim();
    const projeto = document.getElementById('editProjeto').value.trim();
    const veiculo = document.getElementById('editVeiculo').value.trim();
    const sensor = document.getElementById('editSensor').value.trim();
    
    if (!op || !peca || !projeto || !veiculo) {
        showPopup('Todos os campos obrigatórios devem ser preenchidos', true);
        return;
    }
    
    // Buscar arquivo correspondente ao novo sensor
    let arquivoStatus = 'Sem arquivo de corte';
    try {
        const arquivoResponse = await fetch(`/api/buscar-arquivo?projeto=${encodeURIComponent(projeto)}&peca=${encodeURIComponent(peca)}&sensor=${encodeURIComponent(sensor)}`);
        if (arquivoResponse.ok) {
            const arquivoResult = await arquivoResponse.json();
            if (arquivoResult.encontrado) {
                arquivoStatus = arquivoResult.nome_arquivo;
            }
        }
    } catch (error) {
        console.log('Erro ao buscar arquivo:', error);
    }
    
    const cells = window.linhaEditando.querySelectorAll('td');
    cells[1].textContent = op;
    cells[2].textContent = peca;
    cells[3].textContent = projeto;
    cells[4].textContent = veiculo;
    cells[6].textContent = sensor || '-';
    
    // Atualizar coluna de arquivo
    const arquivoCell = cells[7];
    arquivoCell.textContent = arquivoStatus;
    if (arquivoStatus === 'Sem arquivo de corte') {
        arquivoCell.style.color = '#dc2626';
    } else {
        arquivoCell.style.color = '#16a34a';
    }
    
    fecharModalEditar();
    showPopup('Peça editada com sucesso!');
});

// Função para carregar contador de locais
async function carregarContadorLocais() {
    try {
        const [locaisResponse, contagemResponse] = await Promise.all([
            fetch('/api/locais'),
            fetch('/api/contagem-pecas-locais')
        ]);
        
        if (locaisResponse.ok && contagemResponse.ok) {
            const locais = await locaisResponse.json();
            const contagem = await contagemResponse.json();
            
            // Criar mapa de ocupação
            const ocupacaoMap = {};
            contagem.forEach(item => {
                ocupacaoMap[item.local] = item.total;
            });
            
            let totalLocais = 0;
            let locaisOcupados = 0;
            let locaisDisponiveis = 0;
            
            locais.forEach(local => {
                if (local.status === 'Ativo') {
                    totalLocais++;
                    const ocupacao = ocupacaoMap[local.local] || 0;
                    
                    // Usar a mesma lógica da tela de locais: se tem peças = ocupado
                    if (ocupacao > 0) {
                        locaisOcupados++;
                    } else {
                        locaisDisponiveis++;
                    }
                }
            });
            
            // Atualizar contadores na tela (mesma ordem da tela de locais)
            document.getElementById('contadorTotalLocais').textContent = totalLocais;
            document.getElementById('contadorLocaisOcupados').textContent = locaisOcupados;
            document.getElementById('contadorLocaisDisponiveis').textContent = locaisDisponiveis;
        }
    } catch (error) {
        console.error('Erro ao carregar contador de locais:', error);
        document.getElementById('contadorLocaisDisponiveis').textContent = 'Erro';
        document.getElementById('contadorLocaisOcupados').textContent = 'Erro';
        document.getElementById('contadorTotalLocais').textContent = 'Erro';
    }
}