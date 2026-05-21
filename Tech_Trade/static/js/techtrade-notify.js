/**
 * TechTrade — integração de toasts (Bootstrap 5 + simple-notif.js)
 */
(function () {
    'use strict';

    const TYPE_MAP = {
        success: 'success',
        sucesso: 'success',
        ok: 'success',
        danger: 'error',
        erro: 'error',
        error: 'error',
        warning: 'warning',
        aviso: 'warning',
        alert: 'warning',
        info: 'info',
        primary: 'info',
        question: 'question',
    };

    function normalizeType(type) {
        if (!type) return 'info';
        return TYPE_MAP[String(type).toLowerCase()] || 'info';
    }

    function inferTypeFromMessage(message) {
        const m = String(message || '').toLowerCase();
        if (
            m.includes('erro') ||
            m.includes('falha') ||
            m.includes('incorret') ||
            m.includes('inválid') ||
            m.includes('não foi possível') ||
            m.includes('nao foi possivel')
        ) {
            return 'error';
        }
        if (
            m.includes('sucesso') ||
            m.includes('copiado') ||
            m.includes('salvo') ||
            m.includes('aprovad') ||
            m.includes('cancelad') ||
            m.includes('atualizad') ||
            m.includes('registrad') ||
            m.includes('realizada')
        ) {
            return 'success';
        }
        if (
            m.includes('preencha') ||
            m.includes('selecione') ||
            m.includes('informe') ||
            m.includes('obrigat')
        ) {
            return 'warning';
        }
        return 'info';
    }

    function show(message, type, delay) {
        const msg = message == null ? '' : String(message).trim();
        if (!msg) return false;

        const toastType = type ? normalizeType(type) : inferTypeFromMessage(msg);
        const delayMs = delay == null ? 5000 : Number(delay);

        if (typeof window.fireNotif === 'function') {
            return window.fireNotif(msg, toastType, delayMs);
        }
        return false;
    }

    function flushPending() {
        document.querySelectorAll('.tt-flash-pending[data-tt-msg]').forEach(function (el) {
            const msg = el.getAttribute('data-tt-msg');
            const type = el.getAttribute('data-tt-type');
            show(msg, type, 6000);
            el.remove();
        });
    }

    function init() {
        flushPending();

        document.querySelectorAll('.tt-toast-on-load').forEach(function (el) {
            show(el.textContent.trim(), el.getAttribute('data-tt-type'), 6000);
            el.remove();
        });
    }

    window.TTNotify = {
        show: show,
        success: function (m, d) {
            return show(m, 'success', d);
        },
        error: function (m, d) {
            return show(m, 'error', d);
        },
        warning: function (m, d) {
            return show(m, 'warning', d);
        },
        info: function (m, d) {
            return show(m, 'info', d);
        },
        flush: flushPending,
    };

    const nativeAlert = window.alert;
    window.alert = function (message) {
        if (show(message)) return;
        nativeAlert(message);
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
