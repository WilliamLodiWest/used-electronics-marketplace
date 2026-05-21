// Variáveis globais
let produtoModal;
let notificacaoModal;
let notificacaoModalId = null;
let notificacoesCache = [];
let currentPage = 'dashboard';
let categorias = [];

function initSidebarMobile() {
    const app = document.getElementById('vendedor-app');
    const toggle = document.getElementById('sidebar-toggle');
    const backdrop = document.getElementById('sidebar-backdrop');
    const sidebar = document.getElementById('vendedor-sidebar');
    if (!app || !toggle || !sidebar) return;

    const fechar = () => {
        app.classList.remove('sidebar-open');
        toggle.setAttribute('aria-expanded', 'false');
        if (backdrop) backdrop.hidden = true;
        document.body.style.overflow = '';
    };

    const abrir = () => {
        app.classList.add('sidebar-open');
        toggle.setAttribute('aria-expanded', 'true');
        if (backdrop) backdrop.hidden = false;
        document.body.style.overflow = 'hidden';
    };

    toggle.addEventListener('click', () => {
        if (app.classList.contains('sidebar-open')) fechar();
        else abrir();
    });
    backdrop?.addEventListener('click', fechar);
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) fechar();
    });
    document.querySelectorAll('.sidebar-nav .nav-link').forEach((link) => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 768) fechar();
        });
    });
}

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    const modalEl = document.getElementById('produtoModal');
    if (modalEl && typeof bootstrap !== 'undefined') {
        produtoModal = new bootstrap.Modal(modalEl);
    }
    const notifModalEl = document.getElementById('notificacaoModal');
    if (notifModalEl && typeof bootstrap !== 'undefined') {
        notificacaoModal = new bootstrap.Modal(notifModalEl);
    }
    document.getElementById('notif-modal-excluir')?.addEventListener('click', () => {
        if (notificacaoModalId) excluirNotificacao(notificacaoModalId, true);
    });

    initSidebarMobile();

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
                        <small class="text-danger"><i class="fas fa-exclamation-triangle" aria-hidden="true"></i> Estoque baixo!</small>
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
                        <p class="product-stock">Estoque: ${produto.estoque} unidades</p>
                        <p class="product-category">${produto.categoria || 'Sem categoria'}</p>
                        ${produto.verificado ? '<span class="badge bg-success">Verificado</span>' : '<span class="badge bg-warning">Pendente</span>'}
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
        const response = await fetch('/vendedor/pedidos/json');
        const pedidos = await response.json();

        if (!Array.isArray(pedidos)) {
            document.getElementById('vendas-tabela').innerHTML =
                `<tr><td colspan="9" class="text-center text-danger">${pedidos.erro || 'Erro ao carregar vendas'}</td></tr>`;
            return;
        }

        if (pedidos.length === 0) {
            document.getElementById('vendas-tabela').innerHTML =
                '<tr><td colspan="9" class="text-center">Nenhuma venda realizada ainda</td></tr>';
            return;
        }

        const vendasHtml = pedidos.map((p) => {
            const acoes = buildAcoesVenda(p);
            const statusTxt = p.status_label || formatStatusLabel(p.status);
            const rastreio = p.codigo_rastreio
                ? `<span class="font-monospace small">${p.codigo_rastreio}</span>`
                : '—';
            return `
                <tr>
                    <td>#${p.id_compra}</td>
                    <td>${p.produto_nome}</td>
                    <td>${p.quantidade}</td>
                    <td>R$ ${p.total.toLocaleString('pt-BR')}</td>
                    <td>${p.metodo_pagamento}</td>
                    <td>${rastreio}</td>
                    <td><span class="badge bg-${getStatusColor(p.status)}">${statusTxt}</span></td>
                    <td>${p.data_compra}</td>
                    <td class="text-nowrap vendas-acoes">${acoes}</td>
                </tr>
            `;
        }).join('');
        document.getElementById('vendas-tabela').innerHTML = vendasHtml;
    } catch (error) {
        console.error('Erro ao carregar vendas:', error);
    }
}

async function aprovarPedido(id) {
    const ok = await window.TTNotify?.confirm(
        'Aprovar este pedido? O estoque será baixado e a separação ficará liberada.'
    );
    if (!ok) return;
    try {
        const response = await fetch(`/vendedor/pedidos/aprovar/${id}`, { method: 'POST' });
        const data = await response.json();
        if (!response.ok) {
            window.TTNotify?.error(data.erro || 'Erro ao aprovar');
            return;
        }
        window.TTNotify?.success(data.mensagem || 'Pedido aprovado.');
        carregarVendas();
        carregarDashboard();
    } catch (e) {
        window.TTNotify?.error('Erro ao aprovar pedido.');
    }
}

async function reprovarPedido(id) {
    const ok = await window.TTNotify?.confirm(
        'Reprovar e cancelar este pedido? (Sem baixa de estoque.)',
        { danger: true, okText: 'Reprovar' }
    );
    if (!ok) return;
    try {
        const response = await fetch(`/vendedor/pedidos/reprovar/${id}`, { method: 'POST' });
        const data = await response.json();
        if (!response.ok) {
            window.TTNotify?.error(data.erro || 'Erro ao reprovar');
            return;
        }
        window.TTNotify?.success(data.mensagem || 'Pedido cancelado.');
        carregarVendas();
        carregarDashboard();
    } catch (e) {
        window.TTNotify?.error('Erro ao reprovar pedido.');
    }
}

function formatStatusLabel(status) {
    const map = {
        aguardando_aprovacao: 'Aguardando aprovação',
        pendente: 'Aguardando aprovação',
        pago: 'Aprovado — em preparação',
        processando: 'Aprovado — em preparação',
        enviado: 'Despachado / em transporte',
        entregue: 'Entregue',
        cancelado: 'Cancelado',
    };
    return map[(status || '').toLowerCase()] || status;
}

function buildAcoesVenda(p) {
    const s = (p.status || '').toLowerCase();
    const statusAposAprovacao = ['processando', 'pago', 'enviado', 'entregue', 'cancelado'];

    // Aguardando aprovação (não exibir botões se o status já avançou)
    if (p.aguarda_aprovacao_admin && !statusAposAprovacao.includes(s)) {
        return `
            <button type="button"
                class="btn btn-sm btn-success me-1"
                onclick="aprovarPedido(${p.id_compra})">
                Aprovar
            </button>

            <button type="button"
                class="btn btn-sm btn-danger"
                onclick="reprovarPedido(${p.id_compra})">
                Reprovar
            </button>
        `;
    }

    // Pedido cancelado ou entregue
    if (s === 'cancelado' || s === 'entregue') {
        return `<span class="text-success fw-bold">
            ${s === 'entregue' ? 'Pedido entregue' : 'Pedido cancelado'}
        </span>`;
    }

    // Pedido aprovado -> mostrar botão despachar
    if (s === 'processando' || s === 'pago') {
        return `
            <button type="button"
                class="btn btn-sm btn-primary"
                onclick="marcarDespachado(${p.id_compra})">
                <i class="fas fa-truck" aria-hidden="true"></i> Despachado / em transporte
            </button>
        `;
    }

    // Pedido enviado -> mostrar botão entregue
    if (s === 'enviado') {
        return `
            <button type="button"
                class="btn btn-sm btn-success"
                onclick="marcarEntregue(${p.id_compra})">
                <i class="fas fa-box-open" aria-hidden="true"></i> Entregue
            </button>
        `;
    }

    return `<span class="text-muted">—</span>`;
}

async function atualizarStatusPedido(id, status, confirmMsg) {
    if (confirmMsg) {
        const ok = await window.TTNotify?.confirm(confirmMsg);
        if (!ok) return;
    }
    try {
        const response = await fetch(`/vendedor/pedidos/atualizar_status/${id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status }),
        });
        const data = await response.json();
        if (!response.ok) {
            window.TTNotify?.error(data.erro || 'Erro ao atualizar');
            return;
        }
        window.TTNotify?.success(data.mensagem || 'Status atualizado.');
        carregarVendas();
        carregarDashboard();
    } catch (e) {
        window.TTNotify?.error('Erro ao atualizar status.');
    }
}

async function marcarDespachado(id) {
    await atualizarStatusPedido(
        id,
        'enviado',
        'Marcar como despachado / em transporte? O cliente verá essa etapa no rastreio e em Meus Pedidos.'
    );
}

async function marcarEntregue(id) {
    await atualizarStatusPedido(
        id,
        'entregue',
        'Confirmar entrega? O cliente verá o pedido como entregue.'
    );
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : String(text);
    return div.innerHTML;
}

function truncarMensagem(texto, max = 140) {
    const t = (texto || '').trim();
    if (t.length <= max) return t;
    return t.slice(0, max).trimEnd() + '…';
}

// Carregar Notificações
async function carregarNotificacoes() {
    try {
        const response = await fetch('/vendedor/api/notificacoes');
        const notificacoes = await response.json();
        notificacoesCache = Array.isArray(notificacoes) ? notificacoes : [];
        
        if (notificacoesCache.length > 0) {
            const notifHtml = notificacoesCache.map(notif => `
                <div class="notification-item ${notif.lida ? '' : 'unread'}" data-notif-id="${notif.id}">
                    <button type="button" class="notification-main" onclick="abrirNotificacao(${notif.id})" aria-label="Ver notificação completa">
                        <div class="notification-content">
                            <div class="notification-title">
                                ${escapeHtml(notif.titulo || 'Notificação')}
                                ${!notif.lida ? '<span class="badge bg-primary ms-2">Nova</span>' : ''}
                            </div>
                            <div class="notification-message">${escapeHtml(truncarMensagem(notif.mensagem))}</div>
                            <div class="notification-date">${escapeHtml(notif.data)}</div>
                            <div class="notification-hint"><i class="fas fa-expand-alt"></i> Clique para ver a mensagem completa</div>
                        </div>
                        <div class="notification-status" aria-hidden="true">
                            ${!notif.lida ? '<i class="fas fa-circle text-primary"></i>' : '<i class="far fa-circle text-muted"></i>'}
                        </div>
                    </button>
                    <div class="notification-actions">
                        <button type="button" class="btn-notif-delete" title="Excluir notificação" aria-label="Excluir notificação" onclick="event.stopPropagation(); excluirNotificacao(${notif.id})">
                            <i class="fas fa-trash"></i>
                        </button>
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
        const categoriasNormalizadas = (categorias || [])
            .map(cat => {
                if (Array.isArray(cat)) {
                    return { id_categoria: cat[0], nome: cat[1] };
                }
                return {
                    id_categoria: cat.id_categoria ?? cat.id ?? null,
                    nome: cat.nome ?? cat.categoria ?? ''
                };
            })
            .filter(cat => cat.id_categoria !== null && cat.nome);

        select.innerHTML = '<option value="">Selecione uma categoria</option>' +
            categoriasNormalizadas.map(cat => `<option value="${cat.id_categoria}">${cat.nome}</option>`).join('');
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
                    for (let i = 0; i < select.options.length; i++) {
                        const batePorId = produto.categoria_id && String(select.options[i].value) === String(produto.categoria_id);
                        const batePorNome = select.options[i].text === produto.categoria;
                        if (batePorId || batePorNome) {
                            select.selectedIndex = i;
                            break;
                        }
                    }
                }
            });
    }
    
    produtoModal?.show();
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
    
    if (
        !dados.nome ||
        !dados.descricao ||
        Number.isNaN(dados.preco) ||
        Number.isNaN(dados.estoque) ||
        Number.isNaN(dados.categoria_id)
    ) {
        window.TTNotify?.warning('Por favor, preencha todos os campos obrigatórios (incluindo a categoria).');
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
        
        if (response.ok && (result.success || result.mensagem)) {
            window.TTNotify?.success(result.mensagem || 'Produto salvo com sucesso!');
            produtoModal?.hide();
            carregarProdutos();
            carregarDashboard();
        } else {
            window.TTNotify?.error('Erro: ' + (result.erro || result.mensagem || 'Tente novamente'));
        }
    } catch (error) {
        console.error('Erro ao salvar produto:', error);
        window.TTNotify?.error('Erro ao salvar produto. Tente novamente.');
    }
}

// Deletar produto
async function deletarProduto(id) {
    const ok = await window.TTNotify?.confirm(
        'Tem certeza que deseja remover este produto? Esta ação pode ser irreversível.',
        { danger: true, okText: 'Remover' }
    );
    if (ok) {
        try {
            const response = await fetch(`/vendedor/produto/deletar/${id}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                window.TTNotify?.success(result.mensagem);
                carregarProdutos();
                carregarDashboard();
            } else {
                window.TTNotify?.error('Erro ao deletar produto');
            }
        } catch (error) {
            console.error('Erro ao deletar produto:', error);
            window.TTNotify?.error('Erro ao deletar produto. Tente novamente.');
        }
    }
}

// Abrir modal com mensagem completa
async function abrirNotificacao(id) {
    const notif = notificacoesCache.find((n) => n.id === id);
    if (!notif) return;

    notificacaoModalId = id;
    document.getElementById('notif-modal-titulo').textContent = notif.titulo || 'Notificação';
    document.getElementById('notif-modal-data').textContent = notif.data || '';
    document.getElementById('notif-modal-mensagem').textContent = notif.mensagem || '';

    const badge = document.getElementById('notif-modal-badge');
    if (!notif.lida) {
        badge.classList.remove('d-none');
    } else {
        badge.classList.add('d-none');
    }

    notificacaoModal?.show();

    if (!notif.lida) {
        await marcarLida(id, true);
        const badge = document.getElementById('notif-modal-badge');
        badge?.classList.add('d-none');
    }
}

// Marcar notificação como lida
async function marcarLida(id, recarregar = true) {
    try {
        await fetch('/vendedor/api/notificacoes/marcar_lida', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_notificacao: id })
        });

        const item = notificacoesCache.find((n) => n.id === id);
        if (item) item.lida = true;

        if (recarregar) {
            carregarNotificacoes();
            carregarDashboard();
        } else {
            carregarDashboard();
        }
    } catch (error) {
        console.error('Erro ao marcar notificação:', error);
    }
}

// Excluir notificação
async function excluirNotificacao(id, fromModal = false) {
    const ok = await window.TTNotify?.confirm(
        'Excluir esta notificação? Esta ação não pode ser desfeita.',
        { danger: true, okText: 'Excluir' }
    );
    if (!ok) return;
    try {
        const response = await fetch('/vendedor/api/notificacoes/excluir', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_notificacao: id }),
        });
        const data = await response.json();
        if (!response.ok) {
            window.TTNotify?.error(data.erro || 'Erro ao excluir notificação');
            return;
        }
        window.TTNotify?.success(data.mensagem || 'Notificação excluída.');
        if (fromModal) notificacaoModal?.hide();
        notificacaoModalId = null;
        carregarNotificacoes();
        carregarDashboard();
    } catch (error) {
        console.error('Erro ao excluir notificação:', error);
        window.TTNotify?.error('Erro ao excluir notificação. Tente novamente.');
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
        'aguardando_aprovacao': 'warning',
        'pendente': 'warning',
        'pago': 'info',
        'processando': 'info',
        'enviado': 'primary',
        'entregue': 'success',
        'cancelado': 'danger'
    };
    return colors[status] || 'secondary';
}