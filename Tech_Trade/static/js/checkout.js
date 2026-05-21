// ==========================
// VARIÁVEIS
// ==========================
let idProduto = null;
let precoProduto = null;
let confirmacaoUrl = "/confirmacao";
let descontoPix = 0;
let totalFinal = 0;
let pixModalModo = "preview"; // preview | checkout

// ==========================
// ATUALIZAR TOTAIS
// ==========================
function atualizarTotais() {

    const metodoSelecionado = document.querySelector('input[name="metodo"]:checked');

    if (!metodoSelecionado || precoProduto === null || Number.isNaN(precoProduto)) return;

    const metodo = metodoSelecionado.value;

    if (metodo === "PIX") {
        descontoPix = precoProduto * 0.1;
        totalFinal = precoProduto - descontoPix;
    } else {
        descontoPix = 0;
        totalFinal = precoProduto;
    }

    const totalEl = document.getElementById("totalFinal");
    const descontoEl = document.getElementById("descontoPix");

    if (totalEl) {
        totalEl.innerText = `R$ ${totalFinal.toFixed(2).replace(".", ",")}`;
    }

    if (descontoEl) {
        descontoEl.innerText = `R$ ${descontoPix.toFixed(2).replace(".", ",")}`;
    }

    const pixHint = document.getElementById("pixHint");
    if (pixHint) {
        pixHint.style.display = metodo === "PIX" ? "block" : "none";
    }
}

// ==========================
// PIX — QR SIMULADO
// ==========================
function hashPixSeed(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) {
        h = ((h << 5) - h) + str.charCodeAt(i);
        h |= 0;
    }
    return Math.abs(h);
}

function desenharPadraoQr(canvas, seedText) {
    const ctx = canvas.getContext("2d");
    const n = 25;
    const cell = canvas.width / n;
    const seed = hashPixSeed(seedText);

    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    function desenharFinder(x, y) {
        ctx.fillStyle = "#000000";
        ctx.fillRect(x * cell, y * cell, 7 * cell, 7 * cell);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect((x + 1) * cell, (y + 1) * cell, 5 * cell, 5 * cell);
        ctx.fillStyle = "#000000";
        ctx.fillRect((x + 2) * cell, (y + 2) * cell, 3 * cell, 3 * cell);
    }

    desenharFinder(0, 0);
    desenharFinder(n - 7, 0);
    desenharFinder(0, n - 7);

    for (let row = 0; row < n; row++) {
        for (let col = 0; col < n; col++) {
            const emFinder =
                (row < 8 && col < 8) ||
                (row < 8 && col >= n - 8) ||
                (row >= n - 8 && col < 8);
            if (emFinder) continue;

            const bit = (seed + row * n + col) % 3;
            if (bit === 0) {
                ctx.fillStyle = "#000000";
                ctx.fillRect(col * cell, row * cell, cell, cell);
            }
        }
    }
}

function gerarCodigoPixCopiaCola() {
    const valor = totalFinal.toFixed(2);
    const id = idProduto || "0";
    return `00020126580014BR.GOV.BCB.PIX0136DEMO-TECHTRADE-${id}520400005303986540${valor.replace(".", "")}5802BR5925TECHTRADE MARKETPLACE6009SAO PAULO62070503***6304DEMO`;
}

function formatarMoeda(valor) {
    return `R$ ${valor.toFixed(2).replace(".", ",")}`;
}

function atualizarConteudoModalPix() {
    const valorEl = document.getElementById("pixValorModal");
    const copiaEl = document.getElementById("pixCopiaCola");
    const canvas = document.getElementById("pixQrCanvas");
    const codigo = gerarCodigoPixCopiaCola();

    if (valorEl) valorEl.textContent = formatarMoeda(totalFinal);
    if (copiaEl) copiaEl.value = codigo;
    if (canvas) desenharPadraoQr(canvas, codigo);
}

function abrirModalPix(modo) {
    const modal = document.getElementById("modalPix");
    const btnConfirmar = document.getElementById("btnConfirmarPix");
    if (!modal) return;

    pixModalModo = modo;
    atualizarConteudoModalPix();

    if (btnConfirmar) {
        btnConfirmar.style.display = modo === "checkout" ? "inline-block" : "none";
    }

    modal.classList.add("active");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
}

function fecharModalPix() {
    const modal = document.getElementById("modalPix");
    if (!modal) return;
    modal.classList.remove("active");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
}

function copiarCodigoPix() {
    const copiaEl = document.getElementById("pixCopiaCola");
    const btn = document.getElementById("btnCopiarPix");
    if (!copiaEl) return;

    const texto = copiaEl.value;
    navigator.clipboard.writeText(texto).then(() => {
        if (btn) {
            const original = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i><span>Copiado</span>';
            setTimeout(() => { btn.innerHTML = original; }, 2000);
        }
    }).catch(() => {
        copiaEl.select();
        document.execCommand("copy");
        window.TTNotify?.success("Código PIX copiado!", 3000);
    });
}

// ==========================
// EVENTOS PAGAMENTO
// ==========================
function configurarEventosPagamento() {

    const radios = document.querySelectorAll('input[name="metodo"]');

    if (!radios.length) return;

    radios.forEach(radio => {
        radio.addEventListener("change", function () {
            atualizarTotais();
            if (radio.value === "PIX" && radio.checked) {
                abrirModalPix("preview");
            }
        });
    });
}

function configurarModalPix() {
    const btnFechar = document.getElementById("btnFecharPix");
    const btnCancelar = document.getElementById("btnCancelarPix");
    const btnConfirmar = document.getElementById("btnConfirmarPix");
    const btnCopiar = document.getElementById("btnCopiarPix");
    const modal = document.getElementById("modalPix");

    if (btnFechar) btnFechar.addEventListener("click", fecharModalPix);
    if (btnCancelar) btnCancelar.addEventListener("click", fecharModalPix);
    if (btnCopiar) btnCopiar.addEventListener("click", copiarCodigoPix);

    if (btnConfirmar) {
        btnConfirmar.addEventListener("click", function () {
            fecharModalPix();
            executarFinalizarCompra();
        });
    }

    if (modal) {
        modal.addEventListener("click", function (e) {
            if (e.target === modal) fecharModalPix();
        });
    }
}

// ==========================
// FINALIZAR COMPRA (API)
// ==========================
function executarFinalizarCompra() {

    const endereco = document.getElementById("endereco")?.value;
    const metodoSelecionado = document.querySelector('input[name="metodo"]:checked');
    const metodo = metodoSelecionado ? metodoSelecionado.value : "";

    fetch("/techtrade/produtos/finalizar_compra_completa", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            id_produto: idProduto,
            metodo_pagamento: metodo,
            endereco_entrega: endereco
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.erro) {
            window.TTNotify?.error(data.erro);
            return;
        }

        try {
            localStorage.removeItem("produto_para_comprar");
            localStorage.removeItem("techtrade_carrinho");
        } catch (e) {}

        window.location.href = confirmacaoUrl || "/confirmacao";
    })
    .catch(erro => {
        console.error("Erro:", erro);
        window.TTNotify?.error("Erro ao finalizar compra");
    });
}

// ==========================
// SUBMIT
// ==========================
function configurarSubmit() {

    const form = document.getElementById("formCheckout");
    if (!form) return;

    form.addEventListener("submit", function (e) {

        e.preventDefault();

        const endereco = document.getElementById("endereco")?.value;

        if (!endereco) {
            window.TTNotify?.warning("Preencha o endereço");
            return;
        }

        const metodoSelecionado = document.querySelector('input[name="metodo"]:checked');

        if (!metodoSelecionado) {
            window.TTNotify?.warning("Selecione um método de pagamento");
            return;
        }

        const metodo = metodoSelecionado.value;

        if (metodo === "PIX") {
            abrirModalPix("checkout");
            return;
        }

        executarFinalizarCompra();
    });
}

// ==========================
// COMPROVANTE
// ==========================
function mostrarComprovante() {

    const sucesso = document.getElementById("sucessoContainer");
    const comp = document.getElementById("comprovanteContainer");

    if (sucesso) sucesso.style.display = "none";

    if (comp) {
        comp.style.display = "block";
        comp.scrollIntoView({ behavior: "smooth" });
    }
}

function fecharComprovante() {

    const sucesso = document.getElementById("sucessoContainer");
    const comp = document.getElementById("comprovanteContainer");

    if (comp) comp.style.display = "none";

    if (sucesso) {
        sucesso.style.display = "block";
        sucesso.scrollIntoView({ behavior: "smooth" });
    }
}

// ==========================
// IMPRESSÃO
// ==========================
window.onbeforeprint = function () {
    console.log("Preparando impressão...");
};

window.onafterprint = function () {
    console.log("Impressão finalizada");
};

// ==========================
// CONFETE (OPCIONAL)
// ==========================
function animacaoConfete() {

    if (typeof confetti === "function") {
        confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 }
        });
    }
}

// ==========================
// INIT
// ==========================
document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("formCheckout");

    if (form) {
        idProduto = Number(form.dataset.idProduto);
        precoProduto = Number(form.dataset.precoProduto);
        confirmacaoUrl = form.dataset.confirmacaoUrl || "/confirmacao";
    }

    if (precoProduto !== null && !Number.isNaN(precoProduto)) {
        atualizarTotais();
        configurarEventosPagamento();
        configurarModalPix();
        configurarSubmit();
    }

    const sucessoContainer = document.getElementById("sucessoContainer");
    if (sucessoContainer) {
        setTimeout(animacaoConfete, 500);
    }
});
