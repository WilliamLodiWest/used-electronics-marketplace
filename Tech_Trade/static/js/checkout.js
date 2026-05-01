// ==========================
// VARIÁVEIS
// ==========================
let idProduto = null;
let precoProduto = null;
let confirmacaoUrl = "/confirmacao";
let descontoPix = 0;
let totalFinal = 0;

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
}

// ==========================
// EVENTOS PAGAMENTO
// ==========================
function configurarEventosPagamento() {

    const radios = document.querySelectorAll('input[name="metodo"]');

    if (!radios.length) return;

    radios.forEach(radio => {
        radio.addEventListener("change", atualizarTotais);
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
            alert("Preencha o endereço");
            return;
        }

        const metodoSelecionado = document.querySelector('input[name="metodo"]:checked');

        if (!metodoSelecionado) {
            alert("Selecione um método de pagamento");
            return;
        }

        const metodo = metodoSelecionado.value;

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
                alert(data.erro);
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
            alert("Erro ao finalizar compra");
        });
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
        configurarSubmit();
    }

    setTimeout(animacaoConfete, 500);
});