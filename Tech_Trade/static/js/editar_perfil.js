(function () {
        var zone = document.getElementById('editarPerfilPhoto');
        if (!zone) return;

        var originalUrl = (zone.getAttribute('data-original-url') || '').trim();
        var fileInput = document.getElementById('perfil_foto_input');
        var img = document.getElementById('editarPerfilAvatarImg');
        var fallback = document.getElementById('editarPerfilAvatarFallback');
        var initialsEl = document.getElementById('editarPerfilAvatarInitials');
        var nomeInput = document.getElementById('perfil_nome');
        var removerHidden = document.getElementById('perfil_remover_foto');
        var btnAvatar = document.getElementById('editarPerfilAvatarBtn');
        var btnLimpar = document.getElementById('editarPerfilLimparArquivo');
        var btnRemoverSalva = document.getElementById('editarPerfilRemoverSalva');
        var msgEl = document.getElementById('editarPerfilPhotoMsg');

        var objectUrl = null;
        var maxBytes = 5 * 1024 * 1024;

        function showMsg(text) {
            if (!msgEl) return;
            if (!text) {
                msgEl.textContent = '';
                msgEl.hidden = true;
                return;
            }
            msgEl.textContent = text;
            msgEl.hidden = false;
        }

        function iniciais(nome) {
            nome = (nome || '').trim();
            if (!nome) return '';
            var partes = nome.split(/\s+/).filter(Boolean);
            if (partes.length >= 2) {
                return (partes[0].charAt(0) + partes[partes.length - 1].charAt(0)).toUpperCase();
            }
            return nome.slice(0, 2).toUpperCase();
        }

        function atualizarIniciaisNoFallback() {
            if (!initialsEl || !fallback) return;
            var ini = iniciais(nomeInput ? nomeInput.value : '');
            initialsEl.textContent = ini;
            fallback.classList.toggle('has-initials', ini.length > 0);
        }

        function revokeObject() {
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
                objectUrl = null;
            }
        }

        function mostrarImagem(src) {
            if (!img || !fallback) return;
            img.removeAttribute('hidden');
            img.src = src;
            fallback.setAttribute('hidden', '');
        }

        function mostrarFallback() {
            if (!img || !fallback) return;
            img.setAttribute('hidden', '');
            img.removeAttribute('src');
            fallback.removeAttribute('hidden');
            atualizarIniciaisNoFallback();
        }

        function aplicarVisualAtual() {
            var remover = removerHidden && removerHidden.value === '1';
            if (fileInput && fileInput.files && fileInput.files[0]) {
                var f = fileInput.files[0];
                revokeObject();
                objectUrl = URL.createObjectURL(f);
                mostrarImagem(objectUrl);
                if (removerHidden) removerHidden.value = '0';
                if (btnLimpar) btnLimpar.hidden = false;
                showMsg('');
                return;
            }
            revokeObject();
            if (btnLimpar) btnLimpar.hidden = true;
            if (originalUrl && !remover) {
                mostrarImagem(originalUrl);
                showMsg('');
                return;
            }
            mostrarFallback();
        }

        function validarArquivo(file) {
            if (!file) return 'Nenhum arquivo selecionado.';
            if (!/^image\/(jpeg|png|webp)$/i.test(file.type)) {
                return 'Use uma imagem JPG, PNG ou WebP.';
            }
            if (file.size > maxBytes) {
                return 'Arquivo muito grande. Máximo 5 MB.';
            }
            return '';
        }

        function aoEscolherArquivo(file) {
            var err = validarArquivo(file);
            if (err) {
                showMsg(err);
                if (fileInput) fileInput.value = '';
                aplicarVisualAtual();
                return;
            }
            showMsg('');
            if (removerHidden) removerHidden.value = '0';
            aplicarVisualAtual();
        }

        if (fileInput) {
            fileInput.addEventListener('change', function () {
                var f = fileInput.files && fileInput.files[0];
                aoEscolherArquivo(f);
            });
        }

        if (btnAvatar && fileInput) {
            btnAvatar.addEventListener('click', function () {
                fileInput.click();
            });
        }

        if (btnLimpar && fileInput) {
            btnLimpar.addEventListener('click', function () {
                fileInput.value = '';
                revokeObject();
                aplicarVisualAtual();
                showMsg('');
            });
        }

        if (btnRemoverSalva && removerHidden) {
            btnRemoverSalva.addEventListener('click', function () {
                removerHidden.value = '1';
                if (fileInput) fileInput.value = '';
                revokeObject();
                aplicarVisualAtual();
                showMsg('A foto será removida ao salvar. Você pode escolher outra imagem antes de enviar.');
            });
        }

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(function (ev) {
            zone.addEventListener(ev, function (e) {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        var dragDepth = 0;
        zone.addEventListener('dragenter', function () {
            dragDepth++;
            zone.classList.add('is-dragging');
        });
        zone.addEventListener('dragover', function () {
            zone.classList.add('is-dragging');
        });
        zone.addEventListener('dragleave', function () {
            dragDepth = Math.max(0, dragDepth - 1);
            if (dragDepth === 0) zone.classList.remove('is-dragging');
        });
        zone.addEventListener('drop', function (e) {
            dragDepth = 0;
            zone.classList.remove('is-dragging');
            var dt = e.dataTransfer;
            if (!dt || !dt.files || !dt.files[0] || !fileInput) return;
            try {
                var bucket = new DataTransfer();
                bucket.items.add(dt.files[0]);
                fileInput.files = bucket.files;
            } catch (err) {
                return;
            }
            aoEscolherArquivo(dt.files[0]);
        });

        zone.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                if (fileInput) fileInput.click();
            }
        });

        if (nomeInput) {
            nomeInput.addEventListener('input', function () {
                if (fallback && !fallback.hasAttribute('hidden')) {
                    atualizarIniciaisNoFallback();
                }
            });
        }

        aplicarVisualAtual();
        atualizarIniciaisNoFallback();
    })();
    document.querySelectorAll('.editar-perfil-form .toggle-password').forEach(function (eye) {
        eye.style.cursor = 'pointer';
        eye.addEventListener('click', function () {
            var wrap = eye.closest('.inputForm');
            if (!wrap) return;
            var input = wrap.querySelector('input.input');
            if (!input) return;
            if (input.type !== 'password' && input.type !== 'text') return;
            input.type = input.type === 'password' ? 'text' : 'password';
            eye.classList.toggle('active');
        });
    });