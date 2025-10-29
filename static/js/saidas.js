document.addEventListener('DOMContentLoaded', function() {
    carregarSaidas();
});

async function carregarSaidas() {
    try {
        const response = await fetch('/api/saidas');
        const dados = await response.json();
        
        const tbody = document.getElementById('saidas-tbody');
        tbody.innerHTML = '';
        
        if (!dados || dados.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="border border-gray-200 px-4 py-6 text-center text-gray-500">Nenhuma saída registrada</td></tr>';
            return;
        }
        
        dados.forEach(item => {
            const row = tbody.insertRow();
            row.className = 'hover:bg-gray-50';
            
            [item.op, item.peca, item.projeto, item.veiculo, item.local, item.usuario, item.data].forEach(value => {
                const cell = row.insertCell();
                cell.textContent = value || '-';
                cell.className = 'border border-gray-200 px-4 py-3 text-sm text-gray-700';
            });
            
            const acaoCell = row.insertCell();
            acaoCell.className = 'border border-gray-200 px-4 py-3 text-center';
            acaoCell.innerHTML = `
                <button onclick="voltarEstoque(${item.id})" class="btn-green" title="Voltar para o estoque">
                    <i class="fas fa-undo mr-1"></i>Voltar
                </button>
            `;
        });
        
    } catch (error) {
        console.error('Erro ao carregar saídas:', error);
        const tbody = document.getElementById('saidas-tbody');
        tbody.innerHTML = '<tr><td colspan="8" class="border border-gray-200 px-4 py-6 text-center text-red-500">Erro ao carregar dados das saídas</td></tr>';
    }
}

async function voltarEstoque(id) {
    if (!confirm('Confirma que deseja retornar esta peça ao estoque?')) return;
    
    try {
        const response = await fetch('/api/voltar-estoque', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showPopup(result.message);
            await carregarSaidas();
        } else {
            showPopup(result.message, true);
        }
    } catch (error) {
        showPopup('Erro ao retornar peça ao estoque: ' + error.message, true);
    }
}

const filtrarTabelaSaidas = () => {
    const filtro = document.getElementById('campoPesquisaSaidas').value.toLowerCase();
    document.querySelectorAll('#saidas-tbody tr').forEach(linha => {
        const cells = linha.querySelectorAll('td');
        let match = false;
        
        if (cells.length > 1) {
            const op = cells[0].textContent.toLowerCase();
            const peca = cells[1].textContent.toLowerCase();
            
            // Buscar por peça+op+camada (formato: TSP12345PC)
            const pecaOpCamada = `${peca}${op}pc`;
            
            match = linha.textContent.toLowerCase().includes(filtro) ||
                   pecaOpCamada.includes(filtro);
        } else {
            match = linha.textContent.toLowerCase().includes(filtro);
        }
        
        linha.style.display = match ? '' : 'none';
    });
};

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
    }, 3000);
}

async function gerarExcel() {
    try {
        const tbody = document.getElementById('saidas-tbody');
        const rows = tbody.querySelectorAll('tr');
        
        if (rows.length === 0 || rows[0].cells[0].textContent.includes('Carregando') || rows[0].cells[0].textContent.includes('Nenhuma')) {
            showPopup('Nenhum dado para exportar', true);
            return;
        }
        
        const dados = [];
        rows.forEach(row => {
            if (row.style.display !== 'none') {
                const cells = row.cells;
                dados.push({
                    op: cells[0].textContent.trim(),
                    peca: cells[1].textContent.trim(),
                    projeto: cells[2].textContent.trim(),
                    veiculo: cells[3].textContent.trim(),
                    local: cells[4].textContent.trim(),
                    usuario: cells[5].textContent.trim(),
                    data: cells[6].textContent.trim()
                });
            }
        });
        
        if (dados.length === 0) {
            showPopup('Nenhum dado filtrado para exportar', true);
            return;
        }
        
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/api/gerar-excel-saidas';
        
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

const sortTable = (columnIndex) => {
    const table = document.getElementById('tabela-saidas');
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