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
            
            const checkCell = row.insertCell();
            checkCell.innerHTML = `<input type="checkbox" class="row-checkbox" data-id="${item.id}">`;
            checkCell.className = 'border border-gray-200 px-4 py-3 text-center';
            
            [item.op_pai, item.op, item.peca, item.projeto, item.veiculo, item.local, item.rack].forEach(value => {
                const cell = row.insertCell();
                cell.textContent = value || '-';
                cell.className = 'border border-gray-200 px-4 py-3 text-sm text-gray-700';
            });
            
            const acaoCell = row.insertCell();
            acaoCell.className = 'border border-gray-200 px-4 py-3 text-center';
            acaoCell.innerHTML = `<button onclick="removerPeca(${item.id})" class="btn-red text-white">Confirmar Utilização</button>`;
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
    let visibleCount = 0;
    
    document.querySelectorAll('#estoque-tbody tr').forEach(linha => {
        const cells = linha.querySelectorAll('td');
        let match = false;
        
        if (cells.length >= 7) {
            const peca = cells[3].textContent.toLowerCase();
            const op = cells[2].textContent.toLowerCase();
            const searchText = `${peca}${op}`;
            match = searchText.includes(filtro) || linha.textContent.toLowerCase().includes(filtro);
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
                    op_pai: cells[1].textContent.trim(),
                    op: cells[2].textContent.trim(),
                    peca: cells[3].textContent.trim(),
                    projeto: cells[4].textContent.trim(),
                    veiculo: cells[5].textContent.trim(),
                    local: cells[6].textContent.trim(),
                    rack: cells[7].textContent.trim()
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

const toggleAll = () => {
    const selectAll = document.getElementById('selectAll');
    // Selecionar apenas checkboxes visíveis (não filtrados)
    document.querySelectorAll('.row-checkbox').forEach(cb => {
        const row = cb.closest('tr');
        if (row && row.style.display !== 'none') {
            cb.checked = selectAll.checked;
        }
    });
};

async function saidaMassiva() {
    // Buscar apenas checkboxes selecionados que estão visíveis (não filtrados)
    const checkboxes = Array.from(document.querySelectorAll('.row-checkbox:checked')).filter(cb => {
        const row = cb.closest('tr');
        return row && row.style.display !== 'none';
    });
    
    if (checkboxes.length === 0) return showPopup('Selecione pelo menos uma peça para dar saída.', true);
    
    if (!confirm(`Confirma a saída de ${checkboxes.length} peça(s) do estoque?`)) return;
    
    try {
        const ids = checkboxes.map(cb => parseInt(cb.dataset.id));
        
        const response = await fetch('/api/remover-estoque', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ids })
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
        showPopup(`${checkboxes.length} peça(s) removida(s) com sucesso!`, false);
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