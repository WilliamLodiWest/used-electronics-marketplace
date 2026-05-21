/**
 * TechTrade — toasts + confirmação customizada (sem alert/confirm nativos).
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

    let confirmOverlay = null;
    let confirmMessageEl = null;
    let confirmOkBtn = null;
    let confirmCancelBtn = null;
    let confirmResolve = null;

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

    function ensureConfirmUi() {
        if (confirmOverlay) return;

        confirmOverlay = document.createElement('div');
        confirmOverlay.className = 'tt-confirm-overlay';
        confirmOverlay.hidden = true;
        confirmOverlay.setAttribute('role', 'presentation');
        confirmOverlay.innerHTML =
            '<div class="tt-confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="tt-confirm-msg">' +
            '<p class="tt-confirm-message" id="tt-confirm-msg"></p>' +
            '<div class="tt-confirm-actions">' +
            '<button type="button" class="tt-confirm-btn tt-confirm-btn--cancel">Cancelar</button>' +
            '<button type="button" class="tt-confirm-btn tt-confirm-btn--ok">Confirmar</button>' +
            '</div></div>';

        document.body.appendChild(confirmOverlay);

        const dialog = confirmOverlay.querySelector('.tt-confirm-dialog');
        confirmMessageEl = confirmOverlay.querySelector('.tt-confirm-message');
        confirmOkBtn = confirmOverlay.querySelector('.tt-confirm-btn--ok');
        confirmCancelBtn = confirmOverlay.querySelector('.tt-confirm-btn--cancel');

        function finish(result) {
            if (!confirmResolve) return;
            const resolve = confirmResolve;
            confirmResolve = null;
            confirmOverlay.hidden = true;
            document.body.style.overflow = '';
            resolve(result);
        }

        confirmOkBtn.addEventListener('click', function () {
            finish(true);
        });

        confirmCancelBtn.addEventListener('click', function () {
            finish(false);
        });

        confirmOverlay.addEventListener('click', function (e) {
            if (e.target === confirmOverlay) finish(false);
        });

        dialog.addEventListener('click', function (e) {
            e.stopPropagation();
        });

        document.addEventListener('keydown', function (e) {
            if (confirmOverlay.hidden || !confirmResolve) return;
            if (e.key === 'Escape') {
                e.preventDefault();
                finish(false);
            }
            if (e.key === 'Enter') {
                e.preventDefault();
                finish(true);
            }
        });
    }

    function confirm(message, options) {
        const opts = options || {};
        const msg = message == null ? '' : String(message).trim();
        if (!msg) return Promise.resolve(false);

        ensureConfirmUi();

        return new Promise(function (resolve) {
            if (confirmResolve) {
                confirmResolve(false);
            }
            confirmResolve = resolve;

            confirmMessageEl.textContent = msg;
            confirmOkBtn.textContent = opts.okText || 'Confirmar';
            confirmCancelBtn.textContent = opts.cancelText || 'Cancelar';

            confirmOkBtn.classList.toggle('tt-confirm-btn--danger', !!opts.danger);
            confirmOverlay.hidden = false;
            document.body.style.overflow = 'hidden';
            confirmCancelBtn.focus();
        });
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
        confirm: confirm,
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
