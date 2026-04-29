// Variáveis globais
let produtoModal;
let currentPage = 'dashboard';
let categorias = [];

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    produtoModal = new bootstrap.Modal(document.getElementById('produtoModal'));
    
    // Navegação
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.dataset.page;
            mudarPagina(page);
        });
    });
    
    // Carregar dados iniciais
    carregarDashboard();
    carregarCategorias();
    
    // Atualizar a cada 30 segundos
    setInterval(() => {
        if (currentPage === 'dashboard') carregarDashboard();
        else if (currentPage === 'produtos') carregarProdutos();
        else if (currentPage === 'vendas') carregarVendas();
        else if (currentPage === 'notificacoes') carregarNotificacoes();
    }, 30000);
});

// Mudar página
function mudarPagina(page) {
    currentPage = page;
    
    // Atualizar active class nos links
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.dataset.page === page) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
    
    // Mostrar página correta
    document.querySelectorAll('.page-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${page}-page`).classList.add('active');
    
    // Carregar dados da página
    if (page === 'dashboard') carregarDashboard();
    else if (page === 'produtos') carregarProdutos();
    else if (page === 'vendas') carregarVendas();
    else if (page === 'notificacoes') carregarNotificacoes();
}

// Carregar Dashboard
async function carregarDashboard() {
    try {
        const response = await fetch('/vendedor/api/dashboard');
        const data = await response.json();
        
        // Atualizar stats
        const statsHtml = `
            <div class="stat-card">
                <div class="stat-info">
                    <h3>Total de Produtos</h3>
                    <div class="stat-number">${data.total_produtos || 0}</div>
                </div>
                <div class="stat-icon"><i class="fas fa-box"></i></div>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <h3>Total em Estoque</h3>
                    <div class="stat-number">${data.total_estoque || 0}</div>
                </div>
                <div class="stat-icon"><i class="fas fa-warehouse"></i></div>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <h3>Vendas Realizadas</h3>
                    <div class="stat-number">${data.total_vendas || 0}</div>
                </div>
                <div class="stat-icon"><i class="fas fa-shopping-cart"></i></div>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <h3>Receita Total</h3>
                    <div class="stat-number">R$ ${(data.receita_total || 0).toLocaleString('pt-BR')}</div>
                </div>
                <div class="stat-icon"><i class="fas fa-chart-line"></i></div>
            </div>
        `;
        document.getElementById('stats-container').innerHTML = statsHtml;
        
        // Atualizar badge de notificações
        const notifBadge = document.getElementById('notif-badge');
        if (data.notificacoes_nao_lidas > 0) {
            notifBadge.textContent = data.notificacoes_nao_lidas;
            notifBadge.style.display = 'inline-block';
        } else {
            notifBadge.style.display = 'none';
        }
        
        // Vendas recentes
        if (data.vendas_recentes && data.vendas_recentes.length > 0) {
            const vendasHtml = data.vendas_recentes.map(venda => `
                <div class="mb-3 pb-2 border-bottom">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${venda.produto}</strong>
                            <div>Qtd: ${venda.quantidade} | Total: R$ ${venda.total.toLocaleString('pt-BR')}</div>
                            <small class="text-muted">${venda.data}</small>
                        </div>
                        <span class="badge bg-${getStatusColor(venda.status)}">${venda.status}</span>
                    </div>
                </div>
            `).join('');
            document.getElementById('vendas-recentes').innerHTML = vendasHtml;
        } else {
            document.getElementById('vendas-recentes').innerHTML = '<p class="text-muted">Nenhuma venda recente</p>';
        }
        
        // Estoque baixo
        if (data.estoque_baixo && data.estoque_baixo.length > 0) {
            const estoqueHtml = data.estoque_baixo.map(produto => `
                <div class="mb-3 pb-2 border-bottom">
                    <div>
                        <strong>${produto.nome}</strong>
                        <div>Estoque: ${produto.estoque} unidades</div>
                        <small class="text-danger">⚠️ Estoque baixo!</small>
                    </div>
                </div>
            `).join('');
            document.getElementById('estoque-baixo').innerHTML = estoqueHtml;
        } else {
            document.getElementById('estoque-baixo').innerHTML = '<p class="text-muted">Todos os produtos com estoque OK</p>';
        }
        
    } catch (error) {
        console.error('Erro ao carregar dashboard:', error);
        document.getElementById('stats-container').innerHTML = '<div class="alert alert-danger">Erro ao carregar dados</div>';
    }
}

// Carregar Produtos
async function carregarProdutos() {
    try {
        const response = await fetch('/vendedor/api/produtos');
        const produtos = await response.json();
        
        if (produtos.length > 0) {
            const produtosHtml = produtos.map(produto => `
                <div class="product-card">
                    <img src="${produto.imagem}" alt="${produto.nome}" class="product-image">
                    <div class="product-info">
                        <h3 class="product-title">${produto.nome}</h3>
                        <p class="product-price">R$ ${produto.preco.toLocaleString('pt-BR')}</p>
                        <p class="product-stock">📦 Estoque: ${produto.estoque} unidades</p>
                        <p class="product-category">🏷️ ${produto.categoria || 'Sem categoria'}</p>
                        ${produto.verificado ? '<span class="badge bg-success">✓ Verificado</span>' : '<span class="badge bg-warning">⏳ Pendente</span>'}
                    </div>
                    <div class="product-actions">
                        <button class="btn-edit" onclick="editarProduto(${produto.id})">
                            <i class="fas fa-edit"></i> Editar
                        </button>
                        <button class="btn-delete" onclick="deletarProduto(${produto.id})">
                            <i class="fas fa-trash"></i> Remover
                        </button>
                    </div>
                </div>
            `).join('');
            document.getElementById('produtos-container').innerHTML = produtosHtml;
        } else {
            document.getElementById('produtos-container').innerHTML = `
                <div class="text-center p-5">
                    <i class="fas fa-box-open fa-3x text-muted mb-3"></i>
                    <p>Você ainda não tem produtos cadastrados.</p>
                    <button class="btn btn-primary" onclick="abrirModalProduto()">Adicionar Primeiro Produto</button>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erro ao carregar produtos:', error);
        document.getElementById('produtos-container').innerHTML = '<div class="alert alert-danger">Erro ao carregar produtos</div>';
    }
}

// Carregar Vendas
async function carregarVendas() {
    try {
        const response = await fetch('/vendedor/api/dashboard');
        const data = await response.json();
        
        if (data.vendas_recentes && data.vendas_recentes.length > 0) {
            const vendasHtml = data.vendas_recentes.map(venda => `
                <tr>
                    <td>#${venda.id}</td>
                    <td>${venda.produto}</td>
                    <td>${venda.quantidade}</td>
                    <td>R$ ${venda.total.toLocaleString('pt-BR')}</td>
                    <td>${venda.metodo}</td>
                    <td><span class="badge bg-${getStatusColor(venda.status)}">${venda.status}</span></td>
                    <td>${venda.data}</td>
                </tr>
            `).join('');
            document.getElementById('vendas-tabela').innerHTML = vendasHtml;
        } else {
            document.getElementById('vendas-tabela').innerHTML = '<tr><td colspan="7" class="text-center">Nenhuma venda realizada ainda</td></tr>';
        }
    } catch (error) {
        console.error('Erro ao carregar vendas:', error);
    }
}

// Carregar Notificações
async function carregarNotificacoes() {
    try {
        const response = await fetch('/vendedor/api/notificacoes');
        const notificacoes = await response.json();
        
        if (notificacoes.length > 0) {
            const notifHtml = notificacoes.map(notif => `
                <div class="notification-item ${notif.lida ? '' : 'unread'}" onclick="marcarLida(${notif.id})">
                    <div class="notification-content">
                        <div class="notification-title">
                            ${notif.titulo || 'Notificação'}
                            ${!notif.lida ? '<span class="badge bg-primary ms-2">Nova</span>' : ''}
                        </div>
                        <div class="notification-message">${notif.mensagem}</div>
                        <div class="notification-date">${notif.data}</div>
                    </div>
                    <div class="notification-status">
                        ${!notif.lida ? '<i class="fas fa-circle text-primary"></i>' : '<i class="far fa-circle text-muted"></i>'}
                    </div>
                </div>
            `).join('');
            document.getElementById('notificacoes-container').innerHTML = notifHtml;
        } else {
            document.getElementById('notificacoes-container').innerHTML = `
                <div class="text-center p-5">
                    <i class="fas fa-bell-slash fa-3x text-muted mb-3"></i>
                    <p>Nenhuma notificação no momento</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erro ao carregar notificações:', error);
    }
}

// Carregar Categorias
async function carregarCategorias() {
    try {
        const response = await fetch('/techtrade/categorias');
        categorias = await response.json();
        
        const select = document.getElementById('produto-categoria');
        select.innerHTML = '<option value="">Selecione uma categoria</option>' + 
            categorias.map(cat => `<option value="${cat.id_categoria}">${cat.nome}</option>`).join('');
    } catch (error) {
        console.error('Erro ao carregar categorias:', error);
    }
}

// Abrir modal de produto
function abrirModalProduto(id = null) {
    document.getElementById('produto-form').reset();
    document.getElementById('produto-id').value = '';
    
    if (id) {
        // Carregar dados do produto para edição
        fetch(`/vendedor/api/produtos`)
            .then(res => res.json())
            .then(produtos => {
                const produto = produtos.find(p => p.id === id);
                if (produto) {
                    document.getElementById('produto-id').value = produto.id;
                    document.getElementById('produto-nome').value = produto.nome;
                    document.getElementById('produto-descricao').value = produto.descricao;
                    document.getElementById('produto-preco').value = produto.preco;
                    document.getElementById('produto-estoque').value = produto.estoque;
                    document.getElementById('produto-imagem').value = produto.imagem;
                    
                    // Selecionar categoria
                    const select = document.getElementById('produto-categoria');
                    for(let i = 0; i < select.options.length; i++) {
                        if(select.options[i].text === produto.categoria) {
                            select.selectedIndex = i;
                            break;
                        }
                    }
                }
            });
    }
    
    produtoModal.show();
}

// Editar produto
function editarProduto(id) {
    abrirModalProduto(id);
}

// Salvar produto
async function salvarProduto() {
    const id = document.getElementById('produto-id').value;
    const dados = {
        nome: document.getElementById('produto-nome').value,
        descricao: document.getElementById('produto-descricao').value,
        preco: parseFloat(document.getElementById('produto-preco').value),
        estoque: parseInt(document.getElementById('produto-estoque').value),
        categoria_id: parseInt(document.getElementById('produto-categoria').value),
        imagem: document.getElementById('produto-imagem').value
    };
    
    if (!dados.nome || !dados.descricao || !dados.preco || !dados.estoque || !dados.categoria_id) {
        alert('Por favor, preencha todos os campos obrigatórios!');
        return;
    }
    
    try {
        let response;
        if (id) {
            response = await fetch(`/vendedor/produto/editar/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            });
        } else {
            response = await fetch('/vendedor/produto/novo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            alert(result.mensagem);
            produtoModal.hide();
            carregarProdutos();
            carregarDashboard();
        } else {
            alert('Erro: ' + (result.erro || 'Tente novamente'));
        }
    } catch (error) {
        console.error('Erro ao salvar produto:', error);
        alert('Erro ao salvar produto. Tente novamente.');
    }
}

// Deletar produto
async function deletarProduto(id) {
    if (confirm('Tem certeza que deseja remover este produto? Esta ação pode ser irreversível.')) {
        try {
            const response = await fetch(`/vendedor/produto/deletar/${id}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert(result.mensagem);
                carregarProdutos();
                carregarDashboard();
            } else {
                alert('Erro ao deletar produto');
            }
        } catch (error) {
            console.error('Erro ao deletar produto:', error);
            alert('Erro ao deletar produto. Tente novamente.');
        }
    }
}

// Marcar notificação como lida
async function marcarLida(id) {
    try {
        await fetch('/vendedor/api/notificacoes/marcar_lida', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_notificacao: id })
        });
        
        carregarNotificacoes();
        carregarDashboard();
    } catch (error) {
        console.error('Erro ao marcar notificação:', error);
    }
}

// Marcar todas como lidas
async function marcarTodasLidas() {
    try {
        await fetch('/vendedor/api/notificacoes/marcar_todas_lidas', {
            method: 'POST'
        });
        
        carregarNotificacoes();
        carregarDashboard();
    } catch (error) {
        console.error('Erro ao marcar notificações:', error);
    }
}

// Helper: Status color
function getStatusColor(status) {
    const colors = {
        'pendente': 'warning',
        'pago': 'info',
        'enviado': 'primary',
        'entregue': 'success',
        'cancelado': 'danger'
    };
    return colors[status] || 'secondary';
}