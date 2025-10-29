document.addEventListener('DOMContentLoaded', function() {
    carregarBaixas();
});

async function carregarBaixas() {
    try {
        const response = await fetch('/api/baixas');
        const dados = await response.json();
        
        const tbody = document.getElementById('baixas-tbody');
        tbody.innerHTML = '';
        
        if (!dados || dados.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="border border-gray-200 px-4 py-6 text-center text-gray-500">Nenhuma peça em baixa</td></tr>';
            return;
        }
        
        dados.forEach(item => {
            const row = tbody.insertRow();
            row.className = 'hover:bg-gray-50';
            
            // OP
            const opCell = row.insertCell();
            opCell.textContent = item.op || '-';
            opCell.className = 'border border-gray-200 px-4 py-3 text-sm text-gray-700';
            
            // PEÇA
            const pecaCell = row.insertCell();
            pecaCell.textContent = item.peca || '-';
            pecaCell.className = 'border border-gray-200 px-4 py-3 text-sm text-gray-700';
            
            // PROJETO
            const projetoCell = row.insertCell();
            projetoCell.textContent = item.projeto || '-';
            projetoCell.className = 'border border-gray-200 px-4 py-3 text-sm text-gray-700';
            
            // MOTIVO
            const motivoCell = row.insertCell();
            motivoCell.textContent = item.motivo_baixa || '-';
            motivoCell.className = 'border border-gray-200 px-4 py-3 text-sm text-gray-700';
            motivoCell.title = item.motivo_baixa; // Tooltip para motivos longos
            
            // DATA BAIXA
            const dataCell = row.insertCell();
            dataCell.textContent = item.data_baixa || '-';
            dataCell.className = 'border border-gray-200 px-4 py-3 text-sm text-gray-700';
            
            // STATUS
            const statusCell = row.insertCell();
            statusCell.className = 'border border-gray-200 px-4 py-3 text-center';
            const statusClass = item.status === 'PROCESSADO' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800';
            statusCell.innerHTML = `<span class="${statusClass} px-2 py-1 rounded text-xs">${item.status}</span>`;
            
            // USUÁRIO
            const usuarioCell = row.insertCell();
            usuarioCell.textContent = item.usuario_apontamento || '-';
            usuarioCell.className = 'border border-gray-200 px-4 py-3 text-sm text-gray-700';
            
            // AÇÃO
            const acaoCell = row.insertCell();
            acaoCell.className = 'border border-gray-200 px-4 py-3 text-center';
            
            if (item.status === 'PENDENTE') {
                acaoCell.innerHTML = `
                    <button onclick="reprocessarBaixa(${item.id})" class="btn-green text-white" title="Reprocessar peça">
                        <i class="fas fa-redo mr-1"></i> Reprocessar
                    </button>
                `;
            } else {
                acaoCell.innerHTML = '<span class="text-gray-400 text-sm">Processado</span>';
            }
        });
        
        atualizarEstatisticas(dados);
        
    } catch (error) {
        console.error('Erro ao carregar baixas:', error);
        const tbody = document.getElementById('baixas-tbody');
        tbody.innerHTML = '<tr><td colspan="8" class="border border-gray-200 px-4 py-6 text-center text-red-500">Erro ao carregar dados das baixas</td></tr>';
    }
}

async function reprocessarBaixa(id) {
    if (!confirm('Confirma o reprocessamento desta peça? Ela será adicionada novamente às otimizadas.')) return;
    
    try {
        const response = await fetch('/api/reprocessar-baixa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showPopup(result.message);
            await carregarBaixas();
        } else {
            showPopup(result.message, true);
        }
    } catch (error) {
        showPopup('Erro ao reprocessar baixa: ' + error.message, true);
    }
}

const filtrarTabelaBaixas = () => {
    const filtro = document.getElementById('campoPesquisaBaixas').value.toLowerCase();
    let visibleCount = 0;
    
    document.querySelectorAll('#baixas-tbody tr').forEach(linha => {
        const cells = linha.querySelectorAll('td');
        let match = false;
        
        if (cells.length >= 7) {
            const op = cells[0].textContent.toLowerCase();
            const peca = cells[1].textContent.toLowerCase();
            const motivo = cells[3].textContent.toLowerCase();
            const searchText = `${op}${peca}${motivo}`;
            match = searchText.includes(filtro) || linha.textContent.toLowerCase().includes(filtro);
        } else {
            match = linha.textContent.toLowerCase().includes(filtro);
        }
        
        linha.style.display = match ? '' : 'none';
        if (match) visibleCount++;
    });
    
    // Manter estatísticas originais durante filtro
};

function atualizarEstatisticas(dados) {
    const total = dados.length;
    const pendentes = dados.filter(item => item.status === 'PENDENTE').length;
    const processadas = dados.filter(item => item.status === 'PROCESSADO').length;
    
    document.getElementById('totalBaixas').textContent = total;
    document.getElementById('baixasPendentes').textContent = pendentes;
    document.getElementById('baixasProcessadas').textContent = processadas;
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
        document.getElementById('campoPesquisaBaixas').focus();
    }, 3000);
}

const sortTable = (columnIndex) => {
    const table = document.getElementById('tabela-baixas');
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