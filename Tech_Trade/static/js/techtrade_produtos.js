let todosProdutos = [];
let produtosFiltrados = [];
let paginaAtual = 1;
const produtosPorPagina = 8;
let usuarioLogadoGlobal = false;

// ==========================
// INICIALIZAÇÃO
// ==========================
document.addEventListener("DOMContentLoaded", async function () {

    if (typeof usuarioLogado !== "undefined") {
        usuarioLogadoGlobal = usuarioLogado;
    }

    await Promise.all([
        consultarCategorias(),
        carregarProdutos()
    ]);

    configurarEventos();
});

// ==========================
// EVENTOS
// ==========================
function configurarEventos() {

    const buscaInput = document.getElementById("buscaProduto");
    if (buscaInput) {
        buscaInput.addEventListener("input", aplicarFiltros);
    }

    const btnLimpar = document.getElementById("btnLimparFiltros");
    if (btnLimpar) {
        btnLimpar.addEventListener("click", limparFiltros);
    }

    document.body.addEventListener("click", function (e) {

        if (e.target.classList.contains("btn-detalhes")) {
            const data = e.target.getAttribute("data-produto");
            if (data) {
                try {
                    mostrarDetalhesProduto(JSON.parse(data));
                } catch (erro) {
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
// CARREGAR PRODUTOS
// ==========================
async function carregarProdutos() {

    const grid = document.getElementById("gridProdutos");
    const totalDiv = document.getElementById("totalProdutos");

    if (!grid) return;

    try {

        if (totalDiv) totalDiv.innerHTML = "Carregando produtos...";

        const resposta = await fetch("/techtrade/produtos/registros");

        if (!resposta.ok) {
            throw new Error(`Erro HTTP: ${resposta.status}`);
        }

        const data = await resposta.json();

        todosProdutos = (data.json_produtos || []).map(p => ({
            id: p.id_produto,
            nome: p.nome,
            preco: p.preco,
            preco_formatado: p.preco_formatado,
            imagem: p.imagem,
            descricao: p.descricao || "Sem descrição",
            categoria: p.categoria || "Outros",
            vendedor: p.criado_por || "TechTrade",
            verificado: p.verificado,
            chave_nfe: (p.chave_nfe || "").trim(),
            consulta_nfe_url: p.consulta_nfe_url || ""
        }));

        produtosFiltrados = [...todosProdutos];
        renderizarProdutos();

    } catch (erro) {

        console.error(erro);

        grid.innerHTML = `
            <div class="alert-error">
                Erro ao carregar produtos: ${erro.message}
            </div>
        `;

        if (totalDiv) totalDiv.innerHTML = "Erro ao carregar produtos";
    }
}

// ==========================
// CATEGORIAS
// ==========================
async function consultarCategorias() {

    try {

        const resposta = await fetch("/techtrade/categorias");
        const categorias = await resposta.json();

        const container = document.getElementById("categoriasLista");
        if (!container) return;

        container.innerHTML = categorias.map(cat => `
            <label class="filtro-item">
                <span>${cat[1]}</span>
                <input type="checkbox" value="${cat[1].toLowerCase()}" onchange="aplicarFiltros()">
            </label>
        `).join("");

    } catch (erro) {
        console.error("Erro categorias:", erro);
    }
}

// ==========================
// FILTROS
// ==========================
window.aplicarFiltros = function () {

    let resultados = [...todosProdutos];

    const termo = document.getElementById("buscaProduto")?.value.toLowerCase() || "";

    if (termo) {
        resultados = resultados.filter(p =>
            p.nome.toLowerCase().includes(termo) ||
            p.descricao.toLowerCase().includes(termo)
        );
    }

    const categoriasSelecionadas = Array.from(
        document.querySelectorAll("#categoriasLista input:checked")
    ).map(cb => cb.value);

    if (categoriasSelecionadas.length > 0) {
        resultados = resultados.filter(p =>
            categoriasSelecionadas.includes(p.categoria.toLowerCase())
        );
    }

    const precoMin = parseFloat(document.getElementById("precoMin")?.value) || 0;
    const precoMax = parseFloat(document.getElementById("precoMax")?.value) || Infinity;

    resultados = resultados.filter(p =>
        p.preco >= precoMin && p.preco <= precoMax
    );

    produtosFiltrados = resultados;
    paginaAtual = 1;
    renderizarProdutos();
};

// ==========================
// LIMPAR
// ==========================
window.limparFiltros = function () {

    document.getElementById("buscaProduto").value = "";
    document.getElementById("precoMin").value = "";
    document.getElementById("precoMax").value = "";

    document.querySelectorAll("#categoriasLista input")
        .forEach(cb => cb.checked = false);

    produtosFiltrados = [...todosProdutos];
    renderizarProdutos();
};

// ==========================
// RENDER
// ==========================
function renderizarProdutos() {

    const grid = document.getElementById("gridProdutos");
    if (!grid) return;

    if (produtosFiltrados.length === 0) {
        grid.innerHTML = "<p>Nenhum produto encontrado</p>";
        return;
    }

    const inicio = (paginaAtual - 1) * produtosPorPagina;
    const pagina = produtosFiltrados.slice(inicio, inicio + produtosPorPagina);

    grid.innerHTML = pagina.map(p => {

        const selo = p.verificado
            ? `<span class="badge bg-success">Verificado</span>`
            : `<span class="badge bg-secondary">Pendente</span>`;

        return `
            <div class="produto-card">
                <img src="${p.imagem}" onerror="this.src='https://via.placeholder.com/300x200'">
                <h3>${p.nome}</h3>
                ${selo}
                <p>${p.descricao}</p>
                <strong>R$ ${p.preco_formatado}</strong>

                <button class="btn-detalhes"
                    data-produto='${JSON.stringify(p)}'>
                    Detalhes
                </button>

                <button class="btn-comprar-direto"
                    data-id="${p.id}">
                    Comprar
                </button>
            </div>
        `;
    }).join("");
}

// ==========================
// DETALHES
// ==========================
function mostrarDetalhesProduto(produto) {

    document.getElementById("detalhe-nome").textContent = produto.nome;
    document.getElementById("detalhe-descricao").textContent = produto.descricao;
    document.getElementById("detalhe-preco").textContent = produto.preco_formatado;
    document.getElementById("detalhe-imagem").src = produto.imagem;

    const modal = new bootstrap.Modal(
        document.getElementById("modalDetalhesProduto")
    );

    modal.show();
}

// ==========================
// COMPRA
// ==========================
function verificarLoginAntesCompra(idProduto) {
    window.location.href = `/techtrade/produtos/checkout/${idProduto}`;
}