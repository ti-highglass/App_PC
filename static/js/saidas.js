let paginaAtual = 1;
let totalPaginas = 1;
const itensPorPagina = 50;
let dadosCompletos = [];
let dadosFiltrados = [];

document.addEventListener('DOMContentLoaded', function() {
    carregarSaidas();
});

async function carregarSaidas() {
    try {
        const response = await fetch('/api/saidas');
        const dados = await response.json();
        
        dadosCompletos = dados;
        dadosFiltrados = dados;
        
        if (!dados || dados.length === 0) {
            const tbody = document.getElementById('saidas-tbody');
            tbody.innerHTML = '<tr><td colspan="8" class="border border-gray-200 px-4 py-6 text-center text-gray-500">Nenhuma saída registrada</td></tr>';
            document.getElementById('paginacao').style.display = 'none';
            return;
        }
        
        totalPaginas = Math.ceil(dadosFiltrados.length / itensPorPagina);
        renderizarPagina();
        atualizarPaginacao();
        
    } catch (error) {
        console.error('Erro ao carregar saídas:', error);
        const tbody = document.getElementById('saidas-tbody');
        tbody.innerHTML = '<tr><td colspan="8" class="border border-gray-200 px-4 py-6 text-center text-red-500">Erro ao carregar dados das saídas</td></tr>';
        document.getElementById('paginacao').style.display = 'none';
    }
}

function renderizarPagina() {
    const tbody = document.getElementById('saidas-tbody');
    tbody.innerHTML = '';
    
    const inicio = (paginaAtual - 1) * itensPorPagina;
    const fim = inicio + itensPorPagina;
    const dadosPagina = dadosFiltrados.slice(inicio, fim);
    
    dadosPagina.forEach(item => {
        const row = tbody.insertRow();
        row.className = 'hover:bg-gray-50';
        
        [item.op, item.peca, item.projeto, item.veiculo, item.local, item.usuario].forEach(value => {
            const cell = row.insertCell();
            cell.textContent = value || '-';
            cell.className = 'border border-gray-200 px-4 py-3 text-sm text-gray-700';
        });
        
        // Data column - show only date part
        const dataCell = row.insertCell();
        const dataFormatada = item.data ? item.data.split(' ')[0] : '-';
        dataCell.textContent = dataFormatada;
        dataCell.className = 'border border-gray-200 px-4 py-3 text-sm text-gray-700';
        
        // Actions column
        const acaoCell = row.insertCell();
        acaoCell.className = 'border border-gray-200 px-4 py-3 text-center';
        acaoCell.innerHTML = `
            <button onclick="abrirModalBaixa('${item.id}', 'saidas')" class="btn-yellow text-white" title="Baixa">
                Baixa
            </button>
        `;
    });
}

function atualizarPaginacao() {
    const paginacao = document.getElementById('paginacao');
    const btnAnterior = document.getElementById('btnAnterior');
    const btnProximo = document.getElementById('btnProximo');
    const infoPagina = document.getElementById('infoPagina');
    
    if (totalPaginas <= 1) {
        paginacao.style.display = 'none';
        return;
    }
    
    paginacao.style.display = 'flex';
    btnAnterior.disabled = paginaAtual === 1;
    btnProximo.disabled = paginaAtual === totalPaginas;
    infoPagina.textContent = `Página ${paginaAtual} de ${totalPaginas}`;
}

function mudarPagina(direcao) {
    const novaPagina = paginaAtual + direcao;
    if (novaPagina >= 1 && novaPagina <= totalPaginas) {
        paginaAtual = novaPagina;
        renderizarPagina();
        atualizarPaginacao();
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
    
    if (!filtro) {
        dadosFiltrados = dadosCompletos;
    } else {
        dadosFiltrados = dadosCompletos.filter(item => {
            const op = (item.op || '').toLowerCase();
            const peca = (item.peca || '').toLowerCase();
            const projeto = (item.projeto || '').toLowerCase();
            const veiculo = (item.veiculo || '').toLowerCase();
            const local = (item.local || '').toLowerCase();
            const usuario = (item.usuario || '').toLowerCase();
            const data = (item.data || '').toLowerCase();
            
            const pecaOpCamada = `${peca}${op}pc`;
            
            return op.includes(filtro) ||
                   peca.includes(filtro) ||
                   projeto.includes(filtro) ||
                   veiculo.includes(filtro) ||
                   local.includes(filtro) ||
                   usuario.includes(filtro) ||
                   data.includes(filtro) ||
                   pecaOpCamada.includes(filtro);
        });
    }
    
    paginaAtual = 1;
    totalPaginas = Math.ceil(dadosFiltrados.length / itensPorPagina);
    renderizarPagina();
    atualizarPaginacao();
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
        
        const dados = dadosFiltrados.map(item => ({
            op: item.op || '',
            peca: item.peca || '',
            projeto: item.projeto || '',
            veiculo: item.veiculo || '',
            local: item.local || '',
            usuario: item.usuario || '',
            data: item.data ? item.data.split(' ')[0] : ''
        }));
        
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
    const columns = ['op', 'peca', 'projeto', 'veiculo', 'local', 'usuario', 'data'];
    const column = columns[columnIndex];
    
    if (!column) return;
    
    const isAsc = !window.sortDirection || !window.sortDirection[columnIndex];
    window.sortDirection = window.sortDirection || {};
    window.sortDirection[columnIndex] = isAsc;
    
    document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    const currentHeader = document.querySelectorAll('th.sortable')[columnIndex];
    currentHeader.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
    
    dadosFiltrados.sort((a, b) => {
        const aValue = (a[column] || '').toString();
        const bValue = (b[column] || '').toString();
        
        const aNum = parseFloat(aValue);
        const bNum = parseFloat(bValue);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAsc ? aNum - bNum : bNum - aNum;
        }
        
        return isAsc ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
    });
    
    renderizarPagina();
};

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
    const origem = 'saidas';
    
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
            await carregarSaidas();
        } else {
            showPopup(result.message, true);
        }
    } catch (error) {
        showPopup('Erro ao processar baixa: ' + error.message, true);
    }
});