// ==========================================
// Arquivo: techtrade_produtos.js (ATUALIZADO)
// ==========================================

// ==========================
// VARIÁVEIS GLOBAIS
// ==========================
let todosProdutos = [];
let produtosFiltrados = [];

let paginaAtual = 1;
const produtosPorPagina = 8;

// ==========================
// ALERTA
// ==========================
window.chamar_alerta = function (tipo, mensagem) {
    console.log(`[ALERTA - ${tipo}] ${mensagem}`);

    if (tipo === "erro") alert(`Erro: ${mensagem}`);
    else if (tipo === "sucesso") alert(`✅ ${mensagem}`);
    else alert(mensagem);
};

// ==========================
// INIT
// ==========================
document.addEventListener("DOMContentLoaded", async function () {

    // prioridade: Flask → fallback localStorage
    if (typeof usuarioLogado === "undefined") {
    usuarioLogado = localStorage.getItem("usuario_logado") === "true";

    } else {
        usuarioLogado = localStorage.getItem("usuario_logado") === "true";
    }

    await Promise.all([
        consultarCategorias(),
        carregarProdutos()
    ]);

    configurarEventosProdutos();
    configurarBusca();
    configurarEventosFiltros();

    console.log("Sistema carregado com sucesso 🚀");
});

// ==========================
// BUSCA (INPUT)
// ==========================
function configurarBusca() {
    const input = document.getElementById("buscaProduto");

    if (!input) return;

    input.addEventListener("keyup", function (e) {
        const termo = e.target.value.toLowerCase();

        produtosFiltrados = todosProdutos.filter(p =>
            p.nome.toLowerCase().includes(termo) ||
            p.descricao.toLowerCase().includes(termo)
        );

        paginaAtual = 1;
        renderizarProdutos();
    });
}

function configurarEventosFiltros() {
    const btnLimpar = document.getElementById("btnLimparFiltros");
    if (btnLimpar) {
        btnLimpar.addEventListener("click", limparFiltros);
    }
}

function limparFiltros() {
    const busca = document.getElementById("buscaProduto");
    const precoMin = document.getElementById("precoMin");
    const precoMax = document.getElementById("precoMax");

    if (busca) busca.value = "";
    if (precoMin) precoMin.value = "";
    if (precoMax) precoMax.value = "";

    document.querySelectorAll("#categoriasLista input[type='checkbox']").forEach(cb => cb.checked = false);
    document.querySelectorAll("input[name='condicao']").forEach(cb => cb.checked = false);

    produtosFiltrados = [...todosProdutos];
    paginaAtual = 1;
    renderizarProdutos();
}

function filtrarPorPreco() {
    const min = parseFloat(document.getElementById("precoMin")?.value) || 0;
    const max = parseFloat(document.getElementById("precoMax")?.value) || Number.MAX_VALUE;

    produtosFiltrados = todosProdutos.filter(p => {
        const validoPreco = p.preco >= min && p.preco <= max;
        return validoPreco;
    });

    const termo = document.getElementById("buscaProduto")?.value.toLowerCase() || "";
    if (termo) {
        produtosFiltrados = produtosFiltrados.filter(p =>
            p.nome.toLowerCase().includes(termo) ||
            p.descricao.toLowerCase().includes(termo)
        );
    }

    const selecionadas = Array.from(document.querySelectorAll("#categoriasLista input:checked")).map(cb => cb.value);
    if (selecionadas.length) {
        produtosFiltrados = produtosFiltrados.filter(p => selecionadas.includes((p.categoria || "").toLowerCase()));
    }

    paginaAtual = 1;
    renderizarProdutos();
}

// ==========================
// CATEGORIAS
// ==========================
async function consultarCategorias() {
    try {
        const resposta = await fetch("/techtrade/categorias");
        if (!resposta.ok) throw new Error();

        const categorias = await resposta.json();

        const container = document.getElementById("categoriasLista");
        if (!container) return;

        container.innerHTML = categorias.map(cat => `
            <label class="filtro-item">
                ${cat[1]}
                <input type="checkbox" value="${cat[1].toLowerCase()}" onchange="filtrarCategorias()">
            </label>
        `).join("");

    } catch (erro) {
        console.error(erro);
        chamar_alerta("erro", "Erro ao carregar categorias");
    }
}

// ==========================
// FILTRO CATEGORIA
// ==========================
function filtrarCategorias() {
    const selecionadas = Array.from(
        document.querySelectorAll("#categoriasLista input:checked")
    ).map(cb => cb.value);

    if (selecionadas.length === 0) {
        produtosFiltrados = [...todosProdutos];
    } else {
        produtosFiltrados = todosProdutos.filter(p =>
            selecionadas.includes((p.categoria || "").toLowerCase())
        );
    }

    paginaAtual = 1;
    renderizarProdutos();
}

// ==========================
// CARREGAR PRODUTOS (API)
// ==========================
async function carregarProdutos() {
    const grid = document.getElementById("gridProdutos");
    if (!grid) return;

    try {
        const resposta = await fetch("/techtrade/produtos/registros");
        if (!resposta.ok) throw new Error();

        const data = await resposta.json();

        todosProdutos = (data.json_produtos || []).map(p => ({
            id: p.id_produto,
            nome: p.nome,
            preco: p.preco,
            preco_formatado: p.preco_formatado,
            imagem: p.imagem,
            descricao: p.descricao,
            categoria: p.categoria || "Outros",
            vendedor: p.criado_por,
            verificado: p.verificado
        }));

        produtosFiltrados = [...todosProdutos];

        renderizarProdutos();

    } catch (erro) {
        console.error(erro);
        grid.innerHTML = `<p class="text-danger">Erro ao carregar produtos</p>`;
    }
}

// ==========================
// RENDER PRODUTOS (GRID NOVO)
// ==========================
function renderizarProdutos() {
    const grid = document.getElementById("gridProdutos");
    const total = document.getElementById("totalProdutos");
    const sem = document.getElementById("semResultados");

    if (!grid) return;

    if (produtosFiltrados.length === 0) {
        grid.innerHTML = "";
        sem.style.display = "block";
        if (total) total.textContent = "Nenhum produto encontrado";
        return;
    }

    sem.style.display = "none";

    const inicio = (paginaAtual - 1) * produtosPorPagina;
    const fim = inicio + produtosPorPagina;

    const pagina = produtosFiltrados.slice(inicio, fim);

    grid.innerHTML = pagina.map(p => `
        <div class="produto-card">

            <img src="${p.imagem}" onerror="this.src='https://via.placeholder.com/300'">

            <h3>${p.nome}</h3>

            <p>${p.descricao.substring(0, 60)}...</p>

            <strong>R$ ${p.preco_formatado || p.preco}</strong>

            <button class="btn-detalhes" data-produto='${JSON.stringify(p).replace(/'/g, "&#39;")}'>
                Ver detalhes
            </button>

            <button class="btn-comprar-direto" data-id="${p.id}">
                Comprar
            </button>

        </div>
    `).join("");

    if (total) {
        total.textContent = `Mostrando ${produtosFiltrados.length} produtos`;
    }

    renderizarPaginacao();
}

// ==========================
// PAGINAÇÃO
// ==========================
function renderizarPaginacao() {
    const container = document.getElementById("paginacao");
    if (!container) return;

    const totalPaginas = Math.ceil(produtosFiltrados.length / produtosPorPagina);

    container.innerHTML = "";

    for (let i = 1; i <= totalPaginas; i++) {
        const btn = document.createElement("button");
        btn.textContent = i;
        btn.classList.add("pagina");

        if (i === paginaAtual) btn.classList.add("active");

        btn.onclick = () => {
            paginaAtual = i;
            renderizarProdutos();
            window.scrollTo({ top: 0 });
        };

        container.appendChild(btn);
    }
}

// ==========================
// MODAL DETALHES
// ==========================
function mostrarDetalhesProduto(produto) {
    if (typeof produto === "string") produto = JSON.parse(produto);

    document.getElementById("detalhe-nome").textContent = produto.nome;
    document.getElementById("detalhe-descricao").textContent = produto.descricao;
    document.getElementById("detalhe-preco").textContent = produto.preco_formatado;
    document.getElementById("detalhe-vendedor").textContent = produto.vendedor;
    document.getElementById("detalhe-imagem").src = produto.imagem;
    document.getElementById("detalhe-categoria").textContent = produto.categoria;
    const btn = document.getElementById("btn-comprar");
    btn.onclick = () => verificarLoginAntesCompra(produto.id);

    new bootstrap.Modal(document.getElementById("modalDetalhesProduto")).show();
}

// ==========================
// COMPRA
// ==========================
function verificarLoginAntesCompra(id) {
    window.location.href = `/techtrade/produtos/checkout/${id}`;
}

// ==========================
// EVENTOS
// ==========================
function configurarEventosProdutos() {
    document.body.addEventListener("click", function (e) {

        if (e.target.classList.contains("btn-detalhes")) {
            const data = e.target.getAttribute("data-produto");
            mostrarDetalhesProduto(data);
        }

        if (e.target.classList.contains("btn-comprar-direto")) {
            const id = e.target.getAttribute("data-id");
            verificarLoginAntesCompra(id);
        }

    });
}