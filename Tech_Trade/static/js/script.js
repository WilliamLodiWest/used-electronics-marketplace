document.addEventListener('DOMContentLoaded', function () {

    // ================= TROCA DE TELAS =================
    window.showRegister = () => toggleScreens('registerScreen');
    window.showLogin = () => toggleScreens('loginScreen');
    window.showForgotPassword = () => toggleScreens('forgotPasswordScreen');
    window.showResetPassword = () => toggleScreens('resetPasswordScreen');
    window.showSupport = () => toggleScreens('supportScreen', true);

    function toggleScreens(screenId, isBlock = false) {
        const screens = [
            'loginScreen',
            'registerScreen',
            'forgotPasswordScreen',
            'resetPasswordScreen',
            'supportScreen'
        ];

        screens.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.style.display = (id === screenId)
                    ? (isBlock ? 'block' : 'flex')
                    : 'none';
            }
        });
    }

    // ================= VALIDAÇÃO =================
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function (e) {
            const inputs = form.querySelectorAll('input[required]');
            let invalido = false;

            inputs.forEach(input => {
                if (!input.value.trim()) invalido = true;
            });

            if (invalido) {
                e.preventDefault();
                alert('Preencha todos os campos!');
            }
        });
    });

    // ================= ESQUECI SENHA =================
    const forgotForm = document.getElementById('forgotPasswordForm');
    if (forgotForm) {
        forgotForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const email = document.getElementById('resetEmail').value;

            if (email) {
                document.getElementById('forgotSuccess').style.display = 'block';
                document.getElementById('forgotSuccess').innerText =
                    `Link enviado para ${email}`;

                setTimeout(() => showResetPassword(), 2000);
            }
        });
    }

    // ================= RESET =================
    const resetForm = document.getElementById('resetPasswordForm');
    if (resetForm) {
        resetForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const nova = document.getElementById('novaSenha').value;
            const confirmar = document.getElementById('confirmarSenha').value;

            if (nova !== confirmar) {
                alert('Senhas não coincidem');
            } else {
                alert('Senha redefinida!');
                showLogin();
            }
        });
    }

});