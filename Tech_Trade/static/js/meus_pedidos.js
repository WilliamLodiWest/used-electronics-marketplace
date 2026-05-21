(function () {
    const cfg = window.TECHTRADE_MEUS_PEDIDOS || {};
    const elLoad = document.getElementById('mpLoading');
    const elVazio = document.getElementById('mpVazio');
    const elLista = document.getElementById('mpLista');
    const elAlertas = document.getElementById('mpAlertas');


    function iconTimeline(state) {
        if (state === 'done') return '<i class="fas fa-check-circle text-success"></i>';
        if (state === 'current') return '<i class="fas fa-dot-circle text-primary"></i>';
        if (state === 'cancelado') return '<i class="fas fa-times-circle text-danger"></i>';
        return '<i class="far fa-circle text-muted"></i>';
    }


    function badgeClass(status) {
        const s = (status || '').toLowerCase();
        const map = {
            aguardando_aprovacao: 'bg-warning text-dark',
            pendente: 'bg-warning text-dark',
            pago: 'bg-info text-dark',
            processando: 'bg-primary',
            enviado: 'bg-info',
            entregue: 'bg-success',
            cancelado: 'bg-danger',
        };
        return map[s] || 'bg-secondary';
    }


    function renderPedidos(pedidos) {
        if (!pedidos.length) {
            elVazio.classList.remove('d-none');
            return;
        }
        elLista.innerHTML = pedidos
            .map((p) => {
                const steps = (p.timeline || [])
                    .map(
                        (step) =>
                            `<li>${iconTimeline(step.state)}<span>${escapeHtml(step.label)}</span></li>`
                    )
                    .join('');
                const rastreio = p.codigo_rastreio
                    ? `<a href="${escapeAttr(p.rastreio_url)}" class="btn btn-sm btn-outline-primary mt-2">Abrir rastreio</a>`
                    : '';
                return `
<div class="card mp-card mp-pedido-card">
  <div class="card-header d-flex flex-column flex-sm-row justify-content-between align-items-start gap-2 py-3">
    <div>
      <span class="text-muted small">Pedido</span>
      <strong class="d-block">#${p.id_compra}</strong>
    </div>
    <span class="badge ${badgeClass(p.status)} mp-badge-status">${escapeHtml(p.status_label || p.status)}</span>
  </div>
  <div class="card-body">
    <div class="d-flex flex-column flex-md-row gap-3 mb-3">
      <img class="mp-prod-thumb" src="${escapeAttr(p.imagem)}" alt="">
      <div class="flex-grow-1 min-w-0">
        <h2 class="h5 mb-1">${escapeHtml(p.produto_nome)}</h2>
        <p class="mp-meta mb-1">Quantidade: ${p.quantidade} · Total <strong class="text-success">R$ ${escapeHtml(
                    p.total_formatado
                )}</strong></p>
        <p class="mp-meta mb-1"><i class="fas fa-calendar-alt me-1"></i>${escapeHtml(p.data_compra)}</p>
        <p class="mp-meta mb-0"><i class="fas fa-credit-card me-1"></i>${escapeHtml(p.metodo_pagamento)}</p>
        ${
            p.endereco_entrega
                ? `<p class="mp-meta mt-2 mb-0"><i class="fas fa-map-marker-alt me-1"></i>${escapeHtml(
                      p.endereco_entrega
                  )}</p>`
                : ''
        }
        ${p.codigo_rastreio ? `<p class="mt-2 mb-0 font-monospace small"><strong>Rastreio:</strong> ${escapeHtml(p.codigo_rastreio)}</p>` : ''}
        ${rastreio}
      </div>
    </div>
    <h3 class="h6 mp-timeline-section-title mb-2 text-uppercase">Andamento</h3>
    <div class="mp-timeline-wrap">
    <ul class="mp-timeline list-group list-group-flush rounded-3 border-0 bg-transparent">${steps}</ul>
    </div>
  </div>
</div>`;
            })
            .join('');
        elLista.classList.remove('d-none');
    }


    function escapeHtml(s) {
        const d = document.createElement('div');
        d.textContent = s == null ? '' : String(s);
        return d.innerHTML;
    }


    function escapeAttr(s) {
        return escapeHtml(s).replace(/"/g, '&quot;');
    }


    async function marcarLida(id) {
        const base = cfg.marcarLidaPrefix || '';
        if (!base || !id) return;
        try {
            await fetch(base + id, { method: 'POST', headers: { Accept: 'application/json' } });
        } catch (e) {
            /* ignore */
        }
    }


    function renderNotificacoes(data) {
        elAlertas.innerHTML = '';
        if (!data || !data.notificacoes || !data.notificacoes.length) {
        }
        const naoLidas = data.notificacoes.filter((n) => !n.lida);
        naoLidas.forEach((n) => {
            const wrap = document.createElement('div');
            wrap.className = 'alert alert-primary mp-notif-nova d-flex flex-column flex-md-row justify-content-between gap-2 align-items-start';
            wrap.innerHTML = `
<div>
  <strong><i class="fas fa-bell me-1"></i>Pedido confirmado</strong>
  <p class="mb-0 small mt-1">${escapeHtml(n.mensagem)}</p>
  <small class="text-muted">${escapeHtml(n.data_envio)}</small>
</div>
<button type="button" class="btn btn-sm btn-light align-self-md-center">Entendi</button>`;
            const btn = wrap.querySelector('button');
            btn.addEventListener('click', async () => {
                await marcarLida(n.id_notificacao);
                wrap.remove();
            });
            elAlertas.appendChild(wrap);
        });
    }


    async function init() {
        try {
            const [resP, resN] = await Promise.all([
                fetch(cfg.apiPedidos, { headers: { Accept: 'application/json' } }),
                fetch(cfg.apiNotifs, { headers: { Accept: 'application/json' } }),
            ]);
            const dataP = await resP.json().catch(() => ({}));
            const dataN = await resN.json().catch(() => ({}));


            elLoad.classList.add('d-none');


            if (!resP.ok) {
                const msg = dataP.erro || 'Não foi possível carregar os pedidos.';
                window.TTNotify?.error(msg);
                return;
            }


            renderNotificacoes(dataN);
            renderPedidos(dataP.pedidos || []);
        } catch (e) {
            elLoad.classList.add('d-none');
            window.TTNotify?.error('Erro de conexão. Tente novamente.');
        }
    }


    init();
})();
