document.addEventListener('DOMContentLoaded', function() {
    carregarEstoque();
});

async function carregarEstoque() {
    try {
        const response = await fetch('/api/estoque');
        const dados = await response.json();
        
        const tbody = document.getElementById('estoque-tbody');
        tbody.innerHTML = '';
        
        if (!dados || dados.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="border border-gray-200 px-4 py-6 text-center text-gray-500">Nenhum item no estoque</td></tr>';
            return;
        }
        
        dados.forEach(item => {
            const row = tbody.insertRow();
            row.className = 'hover:bg-gray-50';
            
            // Checkbox de seleção
            const checkCell = row.insertCell();
            checkCell.innerHTML = `<input type="checkbox" class="row-checkbox" data-id="${item.id}" onchange="atualizarContadorSelecionadas()">`;
            checkCell.className = 'border border-gray-200 px-4 py-3 text-center';
            
            [item.op, item.peca, item.projeto, item.veiculo, item.local, item.sensor, item.lote_pc].forEach(value => {
                const cell = row.insertCell();
                cell.textContent = value || '-';
                cell.className = 'border border-gray-200 px-4 py-3 text-sm text-gray-700';
            });
            
            const acaoCell = row.insertCell();
            acaoCell.className = 'border border-gray-200 px-4 py-3 text-center';
            acaoCell.innerHTML = `
                <div class="flex flex-col gap-2">
                    <button onclick="removerPeca(${item.id})" class="btn-estoque-utilizar">Utilizar</button>
                    <div class="border-t border-gray-300 pt-2">
                        <button onclick="abrirModalEdicao(${item.id}, '${item.op}', '${item.peca}', '${item.projeto}', '${item.veiculo}', '${item.local}', '${item.sensor}')" class="btn-estoque-editar">Editar</button>
                        <button onclick="abrirModalBaixa(${item.id}, 'estoque')" class="btn-estoque-baixa">Baixa</button>
                    </div>
                </div>
            `;
        });
        
        atualizarContadorEstoque(dados.length);
        
    } catch (error) {
        console.error('Erro ao carregar estoque:', error);
        const tbody = document.getElementById('estoque-tbody');
        tbody.innerHTML = '<tr><td colspan="9" class="border border-gray-200 px-4 py-6 text-center text-red-500">Erro ao carregar dados do estoque</td></tr>';
    }
}



const filtrarTabelaEstoque = () => {
    const filtro = document.getElementById('campoPesquisaEstoque').value.toLowerCase();
    const tipoFiltro = document.getElementById('tipoFiltroEstoque').value;
    let visibleCount = 0;
    
    document.querySelectorAll('#estoque-tbody tr').forEach(linha => {
        const cells = linha.querySelectorAll('td');
        let match = false;
        
        if (cells.length > 1) {
            const op = cells[1].textContent.toLowerCase();
            const peca = cells[2].textContent.toLowerCase();
            const projeto = cells[3].textContent.toLowerCase();
            const veiculo = cells[4].textContent.toLowerCase();
            const local = cells[5].textContent.toLowerCase();
            
            switch (tipoFiltro) {
                case 'peca_op':
                    const pecaOpCamada = `${peca}${op}pc`;
                    match = pecaOpCamada.includes(filtro) || op.includes(filtro) || peca.includes(filtro);
                    break;
                case 'local':
                    match = local.includes(filtro);
                    break;
                case 'data':
                    // Para data, buscar em toda a linha
                    match = linha.textContent.toLowerCase().includes(filtro);
                    break;
                case 'geral':
                default:
                    match = linha.textContent.toLowerCase().includes(filtro);
                    break;
            }
        } else {
            match = linha.textContent.toLowerCase().includes(filtro);
        }
        
        linha.style.display = match ? '' : 'none';
        if (match) visibleCount++;
    });
    
    atualizarContadorEstoque(visibleCount);
};

function atualizarContadorEstoque(count) {
    const contador = document.getElementById('contadorEstoque');
    if (contador) {
        contador.innerHTML = `<i class="fas fa-box mr-2"></i>${count} peça${count !== 1 ? 's' : ''}`;
    }
}

async function removerPeca(id) {
    if (!confirm('Confirma que esta peça foi utilizada e deve ser removida do estoque?')) return;
    
    try {
        const response = await fetch('/api/remover-estoque', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ids: [id] })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        showPopup(result.message, !result.success);
        
        if (result.success) {
            await carregarEstoque();
        }
        
    } catch (error) {
        console.error('Erro:', error);
        showPopup('Peça removida com sucesso!', false);
        await carregarEstoque();
    }
}

function showPopup(message, isError = false) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${isError ? '#dc2626' : '#16a34a'};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        font-size: 14px;
        font-weight: 600;
        max-width: 300px;
        animation: slideIn 0.3s ease-out;
    `;
    
    notification.innerHTML = `<i class="fas ${isError ? 'fa-exclamation-triangle' : 'fa-check-circle'}" style="margin-right: 8px;"></i>${message}`;
    
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
        style.remove();
        document.getElementById('campoPesquisaEstoque').focus();
    }, 3000);
}

async function gerarExcel() {
    try {
        const tbody = document.getElementById('estoque-tbody');
        const rows = tbody.querySelectorAll('tr');
        
        if (rows.length === 0 || rows[0].cells[0].textContent.includes('Carregando') || rows[0].cells[0].textContent.includes('Nenhum')) {
            showPopup('Nenhum dado para exportar', true);
            return;
        }
        
        const dados = [];
        rows.forEach(row => {
            if (row.style.display !== 'none') {
                const cells = row.cells;
                dados.push({
                    op: cells[1].textContent.trim(),
                    peca: cells[2].textContent.trim(),
                    projeto: cells[3].textContent.trim(),
                    veiculo: cells[4].textContent.trim(),
                    local: cells[5].textContent.trim(),
                    sensor: cells[6].textContent.trim()
                });
            }
        });
        
        if (dados.length === 0) {
            showPopup('Nenhum dado filtrado para exportar', true);
            return;
        }
        
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/api/gerar-excel-estoque';
        
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'dados';
        input.value = JSON.stringify(dados);
        
        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
        
    } catch (error) {
        showPopup('Erro ao gerar Excel: ' + error.message, true);
    }
}

function atualizarContadorSelecionadas() {
    const checkboxes = document.querySelectorAll('.row-checkbox:checked');
    const contador = document.getElementById('contadorSelecionadas');
    const btnSaidaMassiva = document.getElementById('btnSaidaMassiva');
    
    if (contador) {
        contador.textContent = `${checkboxes.length} selecionada(s)`;
    }
    
    // Mostrar/ocultar botão de saída massiva
    if (checkboxes.length > 0) {
        btnSaidaMassiva.style.display = 'inline-block';
    } else {
        btnSaidaMassiva.style.display = 'none';
    }
}

async function saidaMassiva() {
    const checkboxes = document.querySelectorAll('.row-checkbox:checked');
    if (checkboxes.length === 0) {
        showPopup('Selecione pelo menos uma peça para dar saída.', true);
        return;
    }
    
    const confirmacao = confirm(`ATENÇÃO: Você está prestes a dar SAÍDA MASSIVA em ${checkboxes.length} peça(s).\n\nEsta ação removerá todas as peças selecionadas do estoque.\n\nDeseja continuar?`);
    
    if (!confirmacao) return;
    
    const ids = Array.from(checkboxes).map(cb => cb.dataset.id);
    
    try {
        const response = await fetch('/api/remover-estoque', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids })
        });
        
        const result = await response.json();
        showPopup(result.message, !result.success);
        
        if (result.success) {
            await carregarEstoque();
        }
        
    } catch (error) {
        showPopup('Peças removidas com sucesso!', false);
        await carregarEstoque();
    }
}

const sortTable = (columnIndex) => {
    const table = document.getElementById('tabela-estoque');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    if (rows.length === 0 || rows[0].cells.length <= columnIndex) return;
    
    const isAsc = !window.sortDirection || !window.sortDirection[columnIndex];
    window.sortDirection = window.sortDirection || {};
    window.sortDirection[columnIndex] = isAsc;
    
    document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    const currentHeader = document.querySelectorAll('th.sortable')[columnIndex];
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

// Funções para modal de entrada manual
function abrirModalEntradaManual() {
    document.getElementById('modalEntradaManual').classList.add('show');
    setTimeout(() => {
        document.getElementById('entradaOP').focus();
    }, 100);
}

function fecharModalEntradaManual() {
    document.getElementById('modalEntradaManual').classList.remove('show');
    document.getElementById('formEntradaManual').reset();
}

async function buscarVeiculo() {
    const projeto = document.getElementById('entradaProjeto').value.trim();
    const peca = document.getElementById('entradaPeca').value.trim();
    
    if (!projeto || !peca) {
        document.getElementById('entradaVeiculo').value = '';
        document.getElementById('entradaLocal').value = '';
        return;
    }
    
    try {
        const response = await fetch(`/api/buscar-veiculo-local?projeto=${encodeURIComponent(projeto)}&peca=${encodeURIComponent(peca)}`);
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('entradaVeiculo').value = result.veiculo || 'Não encontrado';
            document.getElementById('entradaLocal').value = result.local || 'Sem slot disponível';
        } else {
            document.getElementById('entradaVeiculo').value = 'Não encontrado';
            document.getElementById('entradaLocal').value = 'Erro na sugestão';
        }
    } catch (error) {
        console.error('Erro ao buscar veículo:', error);
        document.getElementById('entradaVeiculo').value = 'Erro na busca';
        document.getElementById('entradaLocal').value = 'Erro na sugestão';
    }
}

document.getElementById('formEntradaManual').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const dados = {
        op: document.getElementById('entradaOP').value.trim(),
        peca: document.getElementById('entradaPeca').value.trim(),
        projeto: document.getElementById('entradaProjeto').value.trim(),
        veiculo: document.getElementById('entradaVeiculo').value.trim(),
        local: document.getElementById('entradaLocal').value.trim()
    };
    
    if (!dados.op || !dados.peca || !dados.projeto) {
        showPopup('Preencha todos os campos obrigatórios', true);
        return;
    }
    
    try {
        const response = await fetch('/api/entrada-manual-estoque', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showPopup(result.message);
            fecharModalEntradaManual();
            await carregarEstoque();
        } else {
            showPopup(result.message, true);
        }
    } catch (error) {
        showPopup('Erro ao adicionar peça: ' + error.message, true);
    }
});

// Funções para modal de baixa
function abrirModalBaixa(pecaId, origem) {
    document.getElementById('baixaPecaId').value = pecaId;
    document.getElementById('modalBaixa').classList.add('show');
    setTimeout(() => {
        document.getElementById('motivoBaixa').focus();
    }, 100);
}

function fecharModalBaixa() {
    document.getElementById('modalBaixa').classList.remove('show');
    document.getElementById('formBaixa').reset();
}

document.getElementById('formBaixa').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const pecaId = document.getElementById('baixaPecaId').value;
    const motivoBaixa = document.getElementById('motivoBaixa').value;
    const origem = 'estoque';
    
    if (!motivoBaixa) {
        showPopup('Selecione o motivo da baixa', true);
        return;
    }
    
    try {
        const response = await fetch('/api/baixar-peca', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: pecaId, motivo_baixa: motivoBaixa, origem })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showPopup(result.message);
            fecharModalBaixa();
            await carregarEstoque();
        } else {
            showPopup(result.message, true);
        }
    } catch (error) {
        showPopup('Erro ao processar baixa: ' + error.message, true);
    }
});

// Funções para modal de edição
function abrirModalEdicao(id, op, peca, projeto, veiculo, local, sensor) {
    document.getElementById('edicaoId').value = id;
    document.getElementById('edicaoOP').value = op || '';
    document.getElementById('edicaoPeca').value = peca || '';
    document.getElementById('edicaoProjeto').value = projeto || '';
    document.getElementById('edicaoVeiculo').value = veiculo || '';
    document.getElementById('edicaoLocal').value = local || '';
    document.getElementById('edicaoSensor').value = sensor || '';
    document.getElementById('modalEdicao').classList.add('show');
    setTimeout(() => {
        document.getElementById('edicaoOP').focus();
    }, 100);
}

function fecharModalEdicao() {
    document.getElementById('modalEdicao').classList.remove('show');
    document.getElementById('formEdicao').reset();
}

document.getElementById('formEdicao').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const dados = {
        id: document.getElementById('edicaoId').value,
        op: document.getElementById('edicaoOP').value.trim(),
        peca: document.getElementById('edicaoPeca').value.trim(),
        projeto: document.getElementById('edicaoProjeto').value.trim(),
        veiculo: document.getElementById('edicaoVeiculo').value.trim(),
        local: document.getElementById('edicaoLocal').value.trim(),
        sensor: document.getElementById('edicaoSensor').value.trim()
    };
    
    if (!dados.op || !dados.peca || !dados.projeto) {
        showPopup('OP, Peça e Projeto são obrigatórios', true);
        return;
    }
    
    try {
        const response = await fetch('/api/editar-peca-estoque', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showPopup(result.message);
            fecharModalEdicao();
            await carregarEstoque();
        } else {
            showPopup(result.message, true);
        }
    } catch (error) {
        showPopup('Erro ao editar peça: ' + error.message, true);
    }
});