/**
 * Bootstrap 5 Toast — padrão simple-notif.js (jqueryscript.net)
 * Toast branco com cabeçalho e ícone contextual (sem text-bg-* no card inteiro).
 */
(function ($) {
    'use strict';

    const toastContainerHtml =
        '<div aria-live="polite" aria-atomic="true" class="position-relative tt-toast-root">' +
        '<div class="toast-container position-fixed top-0 end-0 p-3"></div></div>';

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
                return {
                    icon: '<i class="fas fa-check-circle text-success me-2" aria-hidden="true"></i>',
                    titleClass: 'text-success',
                    type: 'Sucesso',
                };
            case 'error':
                return {
                    icon: '<i class="fas fa-times-circle text-danger me-2" aria-hidden="true"></i>',
                    titleClass: 'text-danger',
                    type: 'Erro',
                };
            case 'warning':
                return {
                    icon: '<i class="fas fa-triangle-exclamation text-warning me-2" aria-hidden="true"></i>',
                    titleClass: 'text-warning',
                    type: 'Atenção',
                };
            case 'question':
                return {
                    icon: '<i class="fas fa-question-circle text-secondary me-2" aria-hidden="true"></i>',
                    titleClass: 'text-secondary',
                    type: 'Confirmação',
                };
            case 'info':
            default:
                return {
                    icon: '<i class="fas fa-info-circle text-primary me-2" aria-hidden="true"></i>',
                    titleClass: 'text-primary',
                    type: 'Informação',
                };
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
            '<div class="toast tt-toast-item" role="alert" aria-live="assertive" aria-atomic="true">' +
            '<div class="toast-header">' +
            data.icon +
            '<strong class="me-auto ' +
            data.titleClass +
            '">' +
            data.type +
            '</strong>' +
            '<button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Fechar"></button>' +
            '</div>' +
            '<div class="toast-body">' +
            safeMsg +
            '</div>' +
            '</div>';

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
