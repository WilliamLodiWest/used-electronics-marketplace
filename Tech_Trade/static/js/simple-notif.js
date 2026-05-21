/**
 * Bootstrap 5 Toast notifications (simple-notif.js pattern)
 * https://www.jqueryscript.net/other/easy-toast-notification-bootstrap.html
 */
(function ($) {
    'use strict';

    const toastContainerHtml =
        '<div aria-live="polite" aria-atomic="true" class="position-relative tt-toast-root">' +
        '<div class="toast-container position-fixed top-0 end-0 p-3"></div></div>';

    function ensureContainer() {
        if (!$('.toast-container').length) {
            $('body').append(toastContainerHtml);
        }
    }

    function getType(name) {
        switch (name) {
            case 'success':
                return {
                    class: 'text-bg-success',
                    icon: '<i class="fa-solid fa-check-circle me-1"></i>',
                    type: 'Sucesso',
                };
            case 'error':
                return {
                    class: 'text-bg-danger',
                    icon: '<i class="fa-solid fa-xmark-circle me-1"></i>',
                    type: 'Erro',
                };
            case 'warning':
                return {
                    class: 'text-bg-warning',
                    icon: '<i class="fa-solid fa-triangle-exclamation me-1"></i>',
                    type: 'Atenção',
                };
            case 'question':
                return {
                    class: 'text-bg-secondary',
                    icon: '<i class="fa-solid fa-circle-question me-1"></i>',
                    type: 'Confirmação',
                };
            case 'info':
            default:
                return {
                    class: 'text-bg-primary',
                    icon: '<i class="fa-solid fa-info-circle me-1"></i>',
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
        const toastElm = $('.toast-container');

        const elm =
            '<div class="toast align-items-center border-0 ' +
            data.class +
            '" role="alert" aria-live="assertive" aria-atomic="true">' +
            '<div class="toast-header">' +
            data.icon +
            '<strong class="me-auto">' +
            data.type +
            '</strong>' +
            '<button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Fechar"></button>' +
            '</div>' +
            '<div class="d-flex"><div class="toast-body">' +
            msg +
            '</div></div></div>';

        toastElm.append(elm);

        const toastEl = toastElm.find('.toast').last()[0];
        const toast = new bootstrap.Toast(toastEl, {
            delay: delayMs,
            autohide: delayMs !== 0,
        });
        toast.show();
        return true;
    };
})(window.jQuery);
