(function () {
    function fecharMenus() {
        document.querySelectorAll('.menu-mobile.active').forEach(function (btn) {
            btn.classList.remove('active');
            btn.setAttribute('aria-expanded', 'false');
        });
        document.querySelectorAll('.nav-links.active').forEach(function (nav) {
            nav.classList.remove('active');
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.menu-mobile').forEach(function (btn) {
            var container = btn.closest('.nav-container, .navbar, .checkout-navbar');
            if (!container) return;

            var nav = container.querySelector('.nav-links');
            if (!nav) return;

            btn.addEventListener('click', function (event) {
                event.stopPropagation();
                var aberto = !btn.classList.contains('active');
                fecharMenus();
                if (aberto) {
                    btn.classList.add('active');
                    nav.classList.add('active');
                    btn.setAttribute('aria-expanded', 'true');
                }
            });

            nav.querySelectorAll('a').forEach(function (link) {
                link.addEventListener('click', function () {
                    fecharMenus();
                });
            });
        });

        document.addEventListener('click', function (event) {
            if (event.target.closest('.menu-mobile') || event.target.closest('.nav-links')) {
                return;
            }
            fecharMenus();
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                fecharMenus();
            }
        });
    });
})();
