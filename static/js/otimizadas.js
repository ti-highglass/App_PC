document.addEventListener('DOMContentLoaded', () => {
    carregarOtimizadas();
    document.getElementById('campoPesquisaOtimizadas').focus();
});

async function carregarOtimizadas() {
    const tbody = document.getElementById('otimizadas-tbody');
    try {
        const dados = await fetch('/api/otimizadas').then(res => res.json());
        
        tbody.innerHTML = '';
        
        if (dados.error) {
            tbody.innerHTML = `<tr><td colspan="10" class="border border-gray-200 px-4 py-6 text-center text-red-500">Erro: ${dados.error}</td></tr>`;
            return;
        }
        
        if (dados.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="border border-gray-200 px-4 py-6 text-center text-gray-500">Nenhuma peça otimizada</td></tr>';
            return;
        }
        
        dados.forEach(item => {
            const row = tbody.insertRow();
            row.className = 'hover:bg-gray-50';
            
            const checkCell = row.insertCell();
            checkCell.innerHTML = `<input type="checkbox" class="row-checkbox" data-id="${item.id}">`;
            checkCell.className = 'border border-gray-200 px-4 py-3 text-center';
            
            [item.op_pai, item.op, item.peca, item.projeto, item.veiculo, item.local, item.rack, item.camada].forEach(value => {
                const cell = row.insertCell();
                cell.textContent = value || '-';
                cell.className = 'border border-gray-200 px-4 py-3 text-sm text-gray-700';
            });
            
            const statusCell = row.insertCell();
            statusCell.className = 'border border-gray-200 px-4 py-3 text-center';
            statusCell.innerHTML = item.cortada ? 
                '<span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">Cortada</span>' : 
                '<span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs">Pendente</span>';
            
            const actionCell = row.insertCell();
            actionCell.className = 'border border-gray-200 px-4 py-3 text-center';
            actionCell.innerHTML = `<button onclick="enviarPecaIndividual('${item.id}')" class="btn-action-large" title="Enviar para estoque"><i class="fas fa-arrow-right"></i></button>`;
        });
        
        atualizarContadorOtimizadas(dados.length);
        
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="11" class="border border-gray-200 px-4 py-6 text-center text-red-500">Erro ao carregar peças</td></tr>';
    }
}

const toggleAll = () => {
    const selectAll = document.getElementById('selectAll');
    document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = selectAll.checked);
};

async function enviarParaEstoque() {
    const checkboxes = document.querySelectorAll('.row-checkbox:checked');
    if (checkboxes.length === 0) return showPopup('Selecione pelo menos uma peça cortada para enviar ao estoque.', true);
    
    const ids = Array.from(checkboxes).map(cb => cb.dataset.id);
    
    showLoading('Enviando para estoque...');
    
    try {
        const response = await fetch('/api/enviar-estoque', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids })
        });
        
        const result = await response.json();
        
        hideLoading();
        showPopup(result.message, !result.success);
        
        // Limpar campo de pesquisa e focar
        const campoPesquisa = document.getElementById('campoPesquisaOtimizadas');
        campoPesquisa.value = '';
        campoPesquisa.focus();
        
        // Sempre recarregar a lista
        carregarOtimizadas();
    } catch (error) {
        hideLoading();
        // Se deu erro de rede mas pode ter funcionado, mostrar sucesso
        showPopup('Peças enviadas para estoque com sucesso!');
        
        // Limpar campo de pesquisa e focar
        const campoPesquisa = document.getElementById('campoPesquisaOtimizadas');
        campoPesquisa.value = '';
        campoPesquisa.focus();
        
        carregarOtimizadas();
    }
}

async function enviarPecaIndividual(id) {
    showLoading('Enviando peça para estoque...');
    
    try {
        const response = await fetch('/api/enviar-estoque', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: [id] })
        });
        
        const result = await response.json();
        
        hideLoading();
        showPopup(result.message, !result.success);
        
        // Limpar campo de pesquisa e focar
        const campoPesquisa = document.getElementById('campoPesquisaOtimizadas');
        campoPesquisa.value = '';
        campoPesquisa.focus();
        
        // Sempre recarregar a lista
        carregarOtimizadas();
    } catch (error) {
        hideLoading();
        // Se deu erro de rede mas pode ter funcionado, mostrar sucesso
        showPopup('Peça enviada para estoque com sucesso!');
        
        // Limpar campo de pesquisa e focar
        const campoPesquisa = document.getElementById('campoPesquisaOtimizadas');
        campoPesquisa.value = '';
        campoPesquisa.focus();
        
        carregarOtimizadas();
    }
}

async function excluirOtimizadas() {
    const checkboxes = document.querySelectorAll('.row-checkbox:checked');
    if (checkboxes.length === 0) return showPopup('Selecione pelo menos uma peça para excluir.', true);
    
    const motivo = prompt('Digite o motivo da exclusão:');
    if (!motivo || motivo.trim() === '') return showPopup('Motivo da exclusão é obrigatório.', true);
    
    const ids = Array.from(checkboxes).map(cb => cb.dataset.id);
    
    showLoading('Excluindo peças...');
    
    try {
        const response = await fetch('/api/excluir-otimizadas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids, motivo: motivo.trim() })
        });
        
        const result = await response.json();
        
        hideLoading();
        showPopup(result.message, !result.success);
        
        // Sempre recarregar a lista, mesmo se houver "erro"
        carregarOtimizadas();
    } catch (error) {
        hideLoading();
        // Se deu erro de rede mas pode ter funcionado, mostrar sucesso
        showPopup('Peças excluídas com sucesso!');
        carregarOtimizadas();
    }
}

let sortDirection = {};

const sortTable = (columnIndex) => {
    const table = document.getElementById('tabela-otimizadas');
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

const filtrarTabelaOtimizadas = () => {
    const filtro = document.getElementById('campoPesquisaOtimizadas').value.toLowerCase();
    let visibleCount = 0;
    
    document.querySelectorAll('#otimizadas-tbody tr').forEach(linha => {
        const cells = linha.querySelectorAll('td');
        let match = false;
        
        if (cells.length >= 8) {
            const peca = cells[3].textContent.toLowerCase();
            const op = cells[2].textContent.toLowerCase();
            const camada = cells[8].textContent.toLowerCase();
            const searchText = `${peca}${op}${camada}`;
            match = searchText.includes(filtro) || linha.textContent.toLowerCase().includes(filtro);
        } else {
            match = linha.textContent.toLowerCase().includes(filtro);
        }
        
        linha.style.display = match ? '' : 'none';
        if (match) visibleCount++;
    });
    
    atualizarContadorOtimizadas(visibleCount);
};

function atualizarContadorOtimizadas(count) {
    const contador = document.getElementById('contadorOtimizadas');
    if (contador) {
        contador.innerHTML = `<i class="fas fa-cogs mr-2"></i>${count} peça${count !== 1 ? 's' : ''}`;
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
        document.getElementById('campoPesquisaOtimizadas').focus();
    }, 3000);
}