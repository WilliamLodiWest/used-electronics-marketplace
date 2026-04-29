let todosProdutos = [];
let produtosFiltrados = [];
let paginaAtual = 1;
const produtosPorPagina = 8;
let usuarioLogadoGlobal = false;

// ==========================
// INICIALIZAÇÃO
// ==========================
document.addEventListener("DOMContentLoaded", async function () {
    // Verificar se o usuário está logado (vindo do HTML)
    if (typeof usuarioLogado !== 'undefined') {
        usuarioLogadoGlobal = usuarioLogado;
    }
    

    // Carregar categorias e produtos
    await Promise.all([
        consultarCategorias(),
        carregarProdutos()
    ]);

    configurarEventos();
    
});

// ==========================
// CONFIGURAR EVENTOS
// ==========================
function configurarEventos() {
    // Busca em tempo real
    const buscaInput = document.getElementById("buscaProduto");
    if (buscaInput) {
        buscaInput.addEventListener("input", function() {
            aplicarFiltros();
        });
    }

    // Botão limpar filtros
    const btnLimpar = document.getElementById("btnLimparFiltros");
    if (btnLimpar) {
        btnLimpar.addEventListener("click", limparFiltros);
    }

    // Eventos para detalhes e compra (delegação)
    document.body.addEventListener("click", function(e) {
        if (e.target.classList.contains("btn-detalhes")) {
            const data = e.target.getAttribute("data-produto");
            if (data) {
                try {
                    mostrarDetalhesProduto(JSON.parse(data));
                } catch(erro) {
                    console.error("Erro ao parsear produto:", erro);
                }
            }
        }

        if (e.target.classList.contains("btn-comprar-direto")) {
            const id = e.target.getAttribute("data-id");
            if (id) verificarLoginAntesCompra(id);
        }
    });
}

// ==========================
// CARREGAR PRODUTOS (API PÚBLICA - SEM LOGIN)
// ==========================
async function carregarProdutos() {
    const grid = document.getElementById("gridProdutos");
    const totalDiv = document.getElementById("totalProdutos");
    
    if (!grid) return;

    try {
        if (totalDiv) totalDiv.innerHTML = " Carregando produtos...";
        
        // ROTA PÚBLICA - não exige login
        const resposta = await fetch("/techtrade/produtos/registros");
        
        if (!resposta.ok) {
            throw new Error(`Erro HTTP: ${resposta.status}`);
        }
        
        const data = await resposta.json();

        if (data.erro) {
            throw new Error(data.erro);
        }

        todosProdutos = (data.json_produtos || []).map(p => ({
            id: p.id_produto,
            nome: p.nome,
            preco: p.preco,
            preco_formatado: p.preco_formatado,
            imagem: p.imagem,
            descricao: p.descricao || "Sem descrição disponível",
            categoria: p.categoria || "Outros",
            vendedor: p.criado_por || "TechTrade",
            verificado: p.verificado,
            disponivel: p.disponivel
        }));

        produtosFiltrados = [...todosProdutos];
        
        renderizarProdutos();

    } catch (erro) {
        console.error("Erro ao carregar produtos:", erro);
        if (grid) {
            grid.innerHTML = `<div class="alert-error"> Erro ao carregar produtos: ${erro.message}</div>`;
        }
        if (totalDiv) totalDiv.innerHTML = " Erro ao carregar produtos";
    }
}

// ==========================
// CONSULTAR CATEGORIAS
// ==========================
async function consultarCategorias() {
    try {
        const resposta = await fetch("/techtrade/categorias");
        if (!resposta.ok) throw new Error();
        
        const categorias = await resposta.json();
        const container = document.getElementById("categoriasLista");
        
        if (!container) return;

        if (!categorias || categorias.length === 0) {
            container.innerHTML = "<p>Nenhuma categoria encontrada</p>";
            return;
        }

        container.innerHTML = categorias.map(cat => `
            <label class="filtro-item">
                <span>${cat[1]}</span>
                <input type="checkbox" value="${cat[1].toLowerCase()}" onchange="aplicarFiltros()">
            </label>
        `).join("");

    } catch (erro) {
        console.error("Erro ao carregar categorias:", erro);
    }
}

// ==========================
// APLICAR FILTROS
// ==========================
window.aplicarFiltros = function() {
    let resultados = [...todosProdutos];
    
    // Filtro de busca
    const termo = document.getElementById("buscaProduto")?.value.toLowerCase() || "";
    if (termo) {
        resultados = resultados.filter(p =>
            p.nome.toLowerCase().includes(termo) ||
            p.descricao.toLowerCase().includes(termo)
        );
    }
    
    // Filtro de categorias
    const categoriasSelecionadas = Array.from(
        document.querySelectorAll("#categoriasLista input:checked")
    ).map(cb => cb.value);
    
    if (categoriasSelecionadas.length > 0) {
        resultados = resultados.filter(p =>
            categoriasSelecionadas.includes((p.categoria || "").toLowerCase())
        );
    }
    
    // Filtro de preço
    const precoMin = parseFloat(document.getElementById("precoMin")?.value) || 0;
    const precoMax = parseFloat(document.getElementById("precoMax")?.value) || Infinity;
    
    resultados = resultados.filter(p => p.preco >= precoMin && p.preco <= precoMax);
    
    produtosFiltrados = resultados;
    paginaAtual = 1;
    renderizarProdutos();
};

// ==========================
// FILTRAR POR PREÇO
// ==========================
window.filtrarPorPreco = function() {
    aplicarFiltros();
};

// ==========================
// LIMPAR FILTROS
// ==========================
window.limparFiltros = function() {
    // Limpar busca
    const busca = document.getElementById("buscaProduto");
    if (busca) busca.value = "";
    
    // Limpar preços
    const precoMin = document.getElementById("precoMin");
    const precoMax = document.getElementById("precoMax");
    if (precoMin) precoMin.value = "";
    if (precoMax) precoMax.value = "";
    
    // Limpar categorias
    document.querySelectorAll("#categoriasLista input[type='checkbox']").forEach(cb => cb.checked = false);
    
    // Resetar produtos
    produtosFiltrados = [...todosProdutos];
    paginaAtual = 1;
    renderizarProdutos();
};

// ==========================
// RENDERIZAR PRODUTOS
// ==========================
function renderizarProdutos() {
    const grid = document.getElementById("gridProdutos");
    const total = document.getElementById("totalProdutos");
    const sem = document.getElementById("semResultados");

    if (!grid) return;

    if (produtosFiltrados.length === 0) {
        grid.innerHTML = "";
        if (sem) sem.style.display = "block";
        if (total) total.textContent = "📭 Nenhum produto encontrado";
        const paginacao = document.getElementById("paginacao");
        if (paginacao) paginacao.innerHTML = "";
        return;
    }

    if (sem) sem.style.display = "none";

    const inicio = (paginaAtual - 1) * produtosPorPagina;
    const fim = inicio + produtosPorPagina;
    const pagina = produtosFiltrados.slice(inicio, fim);

    grid.innerHTML = pagina.map(p => `
        <div class="produto-card">
            <img src="${p.imagem}" onerror="this.src='https://via.placeholder.com/300x200?text=Sem+Imagem'" alt="${p.nome}">
            <h3 title="${p.nome}">${p.nome.length > 40 ? p.nome.substring(0, 40) + '...' : p.nome}</h3>
            <p>${p.descricao.length > 60 ? p.descricao.substring(0, 60) + '...' : p.descricao}</p>
            <strong>R$ ${p.preco_formatado || p.preco.toFixed(2)}</strong>
            <button class="btn-detalhes" data-produto='${JSON.stringify(p).replace(/'/g, "&#39;")}'>
                 Ver detalhes
            </button>
            <button class="btn-comprar-direto" data-id="${p.id}">
                 Comprar
            </button>
        </div>
    `).join("");

    if (total) {
        total.textContent = ` Mostrando ${produtosFiltrados.length} produtos (${inicio + 1}-${Math.min(fim, produtosFiltrados.length)})`;
    }

    renderizarPaginacao();
}

// ==========================
// RENDERIZAR PAGINAÇÃO
// ==========================
function renderizarPaginacao() {
    const container = document.getElementById("paginacao");
    if (!container) return;

    const totalPaginas = Math.ceil(produtosFiltrados.length / produtosPorPagina);
    
    if (totalPaginas <= 1) {
        container.innerHTML = "";
        return;
    }

    container.innerHTML = "";

    for (let i = 1; i <= totalPaginas; i++) {
        const btn = document.createElement("button");
        btn.textContent = i;
        btn.classList.add("pagina");
        if (i === paginaAtual) btn.classList.add("active");

        btn.onclick = () => {
            paginaAtual = i;
            renderizarProdutos();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        };

        container.appendChild(btn);
    }
}

// ==========================
// MOSTRAR DETALHES DO PRODUTO
// ==========================
function mostrarDetalhesProduto(produto) {
    document.getElementById("detalhe-nome").textContent = produto.nome;
    document.getElementById("detalhe-descricao").textContent = produto.descricao;
    document.getElementById("detalhe-preco").textContent = produto.preco_formatado || produto.preco.toFixed(2);
    document.getElementById("detalhe-vendedor").textContent = produto.vendedor;
    document.getElementById("detalhe-imagem").src = produto.imagem;
    document.getElementById("detalhe-categoria").textContent = produto.categoria;
    
    const btnComprar = document.getElementById("btn-comprar");
    btnComprar.onclick = () => verificarLoginAntesCompra(produto.id);
    
    const modal = new bootstrap.Modal(document.getElementById("modalDetalhesProduto"));
    modal.show();
}

// ==========================
// VERIFICAR LOGIN ANTES DA COMPRA
// ==========================
function verificarLoginAntesCompra(idProduto) {
    window.location.href = `/techtrade/produtos/checkout/${idProduto}`;
}

// Verificar se veio de um redirecionamento de compra
document.addEventListener("DOMContentLoaded", function() {
    const produtoPendente = localStorage.getItem("produto_para_comprar");
    if (produtoPendente && usuarioLogadoGlobal) {
        localStorage.removeItem("produto_para_comprar");
        window.location.href = `/techtrade/produtos/checkout/${produtoPendente}`;
    }
});