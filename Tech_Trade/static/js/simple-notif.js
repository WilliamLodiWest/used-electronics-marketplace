/**
 * TechTrade — toasts escuros (estilo card com ícone + título + mensagem).
 */
(function ($) {
    'use strict';

    const toastContainerHtml =
        '<div aria-live="polite" aria-atomic="true" class="position-relative tt-toast-root">' +
        '<div class="toast-container position-fixed top-0 end-0 p-3 d-flex flex-column"></div></div>';

    function ensureContainer() {
        if (!$('.tt-toast-root .toast-container').length) {
            $('body').append(toastContainerHtml);
        }
    }

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function getType(name) {
        switch (name) {
            case 'success':
                return { mod: 'success', glyph: 'OK', title: 'Sucesso' };
            case 'error':
                return { mod: 'error', glyph: 'X', title: 'Erro' };
            case 'warning':
                return { mod: 'warning', glyph: '!', title: 'Atenção' };
            case 'question':
                return { mod: 'question', glyph: '?', title: 'Confirmação' };
            case 'info':
            default:
                return { mod: 'info', glyph: 'i', title: 'Informação' };
        }
    }

    window.fireNotif = function fireNotif(message, icon, delay) {
        if (typeof $ === 'undefined' || typeof bootstrap === 'undefined') {
            return false;
        }

        ensureContainer();

        const msg = message == null ? '' : String(message);
        const type = icon || 'info';
        const delayMs = delay == null ? 5000 : Number(delay);
        const data = getType(type);
        const toastElm = $('.tt-toast-root .toast-container');
        const safeMsg = escapeHtml(msg);

        const elm =
            '<div class="toast tt-toast-item tt-toast--' +
            data.mod +
            '" role="alert" aria-live="assertive" aria-atomic="true">' +
            '<div class="toast-body">' +
            '<div class="tt-toast-inner">' +
            '<div class="tt-toast-icon" aria-hidden="true">' +
            data.glyph +
            '</div>' +
            '<div class="tt-toast-content">' +
            '<strong class="tt-toast-title">' +
            data.title +
            '</strong>' +
            '<p class="tt-toast-message">' +
            safeMsg +
            '</p>' +
            '</div>' +
            '<button type="button" class="tt-toast-close" data-bs-dismiss="toast" aria-label="Fechar">×</button>' +
            '</div></div></div>';

        toastElm.append(elm);

        const toastEl = toastElm.find('.toast').last()[0];
        const toast = new bootstrap.Toast(toastEl, {
            delay: delayMs,
            autohide: delayMs !== 0,
        });

        toastEl.addEventListener(
            'hidden.bs.toast',
            function () {
                toastEl.remove();
            },
            { once: true }
        );

        toast.show();
        return true;
    };
})(window.jQuery);
