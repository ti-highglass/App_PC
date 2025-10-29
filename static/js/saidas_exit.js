document.addEventListener('DOMContentLoaded', function() {
    carregarSaidasExit();
});

async function carregarSaidasExit() {
    try {
        const response = await fetch('/api/saidas-exit');
        const dados = await response.json();
        
        const tbody = document.getElementById('exit-tbody');
        tbody.innerHTML = '';
        
        if (!dados || dados.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="border border-gray-200 px-4 py-6 text-center text-gray-500">Nenhuma saída encontrada</td></tr>';
            return;
        }
        
        dados.forEach(item => {
            const row = tbody.insertRow();
            row.className = 'hover:bg-gray-50';
            
            [
                item.op || '',
                item.peca || '',
                item.projeto || '',
                item.veiculo || '',
                item.local || '',
                item.rack || '',
                item.usuario || '',
                item.data || '',
                item.motivo || ''
            ].forEach(value => {
                const cell = row.insertCell();
                cell.textContent = value;
                cell.className = 'border border-gray-200 px-4 py-3 text-sm text-gray-700';
            });
        });
        
    } catch (error) {
        console.error('Erro ao carregar saídas:', error);
        const tbody = document.getElementById('exit-tbody');
        tbody.innerHTML = '<tr><td colspan="9" class="border border-gray-200 px-4 py-6 text-center text-red-500">Erro ao carregar dados</td></tr>';
    }
}

function filtrarTabelaExit() {
    const filtro = document.getElementById('campoPesquisaExit').value.toLowerCase();
    
    document.querySelectorAll('#exit-tbody tr').forEach(linha => {
        const match = linha.textContent.toLowerCase().includes(filtro);
        linha.style.display = match ? '' : 'none';
    });
}