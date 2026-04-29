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
        forgotForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const email = document.getElementById('resetEmail').value;
            
            if (!email) {
                alert('Por favor, informe seu e-mail.');
                return;
            }

            const submitBtn = forgotForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Enviando...';
            submitBtn.disabled = true;

            const successDiv = document.getElementById('forgotSuccess');

            try {
                const response = await fetch('/esqueceu_senha', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: `email=${encodeURIComponent(email)}`
                });

                const data = await response.json();
                
                if (data.success) {
                    // Mostrar mensagem de sucesso
                    successDiv.style.display = 'block';
                    successDiv.style.backgroundColor = '#d4edda';
                    successDiv.style.color = '#155724';
                    successDiv.innerHTML = `
                        <p>${data.message}</p>
                        ${data.link ? `<p style="margin-top: 10px; word-break: break-all;">
                            <strong>Link de teste:</strong><br>
                            <a href="${data.link}" target="_blank" style="color: #155724;">${data.link}</a>
                        </p>` : ''}
                        <p style="margin-top: 10px; font-size: 12px;">Em produção, o link seria enviado por e-mail.</p>
                    `;
                    
                    // Limpar o campo de email
                    document.getElementById('resetEmail').value = '';
                    
                    // Resetar botão
                    submitBtn.textContent = originalText;
                    submitBtn.disabled = false;
                    
                    // Opcional: voltar para o login após 5 segundos
                    setTimeout(() => {
                        showLogin();
                        successDiv.style.display = 'none';
                    }, 5000);
                } else if (data.erro) {
                    successDiv.style.display = 'block';
                    successDiv.style.backgroundColor = '#f8d7da';
                    successDiv.style.color = '#721c24';
                    successDiv.innerHTML = `<p>${data.erro}</p>`;
                    submitBtn.textContent = originalText;
                    submitBtn.disabled = false;
                }
            } catch (error) {
                console.error('Erro:', error);
                successDiv.style.display = 'block';
                successDiv.style.backgroundColor = '#f8d7da';
                successDiv.style.color = '#721c24';
                successDiv.innerHTML = `<p>Erro ao processar solicitação. Tente novamente.</p>`;
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        });
    }

    // ================= RESET SENHA (para o formulário de redefinição) =================
    const resetPasswordForm = document.querySelector('#resetPasswordScreen form');
    if (resetPasswordForm) {
        resetPasswordForm.addEventListener('submit', function (e) {
            const novaSenha = resetPasswordForm.querySelector('input[name="nova_senha"]');
            const confirmarSenha = resetPasswordForm.querySelector('input[name="confirmar_senha"]');
            
            if (novaSenha.value.length < 6) {
                e.preventDefault();
                alert('A senha deve ter no mínimo 6 caracteres');
                return;
            }
            
            if (novaSenha.value !== confirmarSenha.value) {
                e.preventDefault();
                alert('As senhas não conferem');
                return;
            }
        });
    }

    // ================= VERIFICAR SE TEM TOKEN NA URL =================
    function checkTokenInUrl() {
        // Verificar se veio da rota /redefinir_senha/<token>
        if (window.location.pathname.includes('/redefinir_senha/')) {
            const tokenFromPath = window.location.pathname.split('/redefinir_senha/')[1];
            if (tokenFromPath) {
                // Definir o action do formulário
                const resetForm = document.querySelector('#resetPasswordScreen form');
                if (resetForm) {
                    resetForm.action = `/redefinir_senha/${tokenFromPath}`;
                }
                showResetPassword();
            }
        }
    }

    // ================= MOSTRAR / OCULTAR SENHA =================
    document.querySelectorAll('.toggle-password').forEach(icon => {
        icon.addEventListener('click', function () {
            const input = this.parentElement.querySelector('input');
            if (input.type === 'password') {
                input.type = 'text';
                this.classList.add('active');
            } else {
                input.type = 'password';
                this.classList.remove('active');
            }
        });
    });

    // ================= MENU DROPDOWN DO USUÁRIO =================
    const userTrigger = document.getElementById('userTrigger');
    const dropdown = document.getElementById('dropdownMenu');

    if (userTrigger && dropdown) {
        userTrigger.addEventListener('click', function (e) {
            e.stopPropagation();
            dropdown.classList.toggle('active');
        });

        dropdown.addEventListener('click', function (e) {
            e.stopPropagation();
        });

        document.addEventListener('click', function () {
            dropdown.classList.remove('active');
        });
    }

    // ================= FUNÇÕES DOS MODAIS =================
    function abrirModalDetalhes(produto) {
        const modal = document.getElementById('modalDetalhes');
        if (!modal) return;
        
        document.getElementById('modalDetalhesNome').textContent = produto.nome;
        document.getElementById('modalDetalhesDescricao').textContent = produto.descricao;
        document.getElementById('modalDetalhesPreco').textContent = `R$ ${typeof produto.preco === 'number' ? produto.preco.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : produto.preco_formatado}`;
        document.getElementById('modalDetalhesCategoria').textContent = produto.categoria;
        document.getElementById('modalDetalhesVendedor').textContent = produto.vendedor || 'TechTrade';
        
        const imagem = document.getElementById('modalDetalhesImagem');
        imagem.src = produto.imagem;
        imagem.onerror = () => { imagem.src = 'https://via.placeholder.com/300x200?text=Sem+Imagem'; };
        
        const comprarBtn = document.getElementById('modalComprarBtn');
        comprarBtn.onclick = () => {
            fecharModalDetalhes();
            abrirModalCompra(produto);
        };
        
        produtoSelecionado = produto;
        modal.classList.add('active');
    }

    function fecharModalDetalhes() {
        const modal = document.getElementById('modalDetalhes');
        if (modal) modal.classList.remove('active');
    }

    function abrirModalCompra(produto) {
        const modal = document.getElementById('modalCompra');
        if (!modal) return;
        
        document.getElementById('modalCompraNome').textContent = produto.nome;
        document.getElementById('modalCompraPreco').textContent = `R$ ${typeof produto.preco === 'number' ? produto.preco.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : produto.preco_formatado}`;
        
        const imagem = document.getElementById('modalCompraImagem');
        imagem.src = produto.imagem;
        imagem.onerror = () => { imagem.src = 'https://via.placeholder.com/80x80?text=Sem+Imagem'; };
        
        produtoSelecionado = produto;
        modal.classList.add('active');
    }

    function fecharModalCompra() {
        const modal = document.getElementById('modalCompra');
        if (modal) modal.classList.remove('active');
    }

    // ================= CARREGAR PRODUTOS DA API =================
    let todosProdutos = [];
    let produtosFiltrados = [];
    let categoriasUnicas = new Set();
    let produtoSelecionado = null;

    async function carregarProdutosHome() {
        const grid = document.getElementById("produtosGrid");
        if (!grid) return;

        try {
            grid.innerHTML = '<div class="loading-spinner">Carregando produtos...</div>';
            
            const resposta = await fetch("/techtrade/produtos/registros");
            if (!resposta.ok) throw new Error("Erro ao carregar produtos");
            
            const data = await resposta.json();
            
            todosProdutos = (data.json_produtos || []).map(p => ({
                id: p.id_produto,
                nome: p.nome,
                preco: p.preco,
                preco_formatado: p.preco_formatado || p.preco.toFixed(2).replace('.', ','),
                imagem: p.imagem || 'https://via.placeholder.com/300x200?text=Sem+Imagem',
                descricao: p.descricao || "Produto de alta qualidade",
                categoria: p.categoria || "Outros",
                vendedor: p.criado_por || "TechTrade"
            }));
            
            produtosFiltrados = [...todosProdutos];
            
            categoriasUnicas.clear();
            todosProdutos.forEach(p => {
                if (p.categoria) categoriasUnicas.add(p.categoria);
            });
            
            atualizarFiltroCategorias();
            renderizarProdutosHome();
            
        } catch (erro) {
            grid.innerHTML = `<p class="text-danger">Erro ao carregar produtos. Tente novamente mais tarde.</p>`;
        }
    }

    function atualizarFiltroCategorias() {
        const select = document.getElementById("categoryFilter");
        if (!select) return;
        
        while (select.options.length > 1) {
            select.remove(1);
        }
        
        Array.from(categoriasUnicas).sort().forEach(categoria => {
            const option = document.createElement("option");
            option.value = categoria.toLowerCase();
            option.textContent = categoria;
            select.appendChild(option);
        });
    }

    function renderizarProdutosHome() {
        const grid = document.getElementById("produtosGrid");
        const noResults = document.getElementById("noResults");
        const productCount = document.getElementById("productCount");
        
        if (!grid) return;
        
        if (produtosFiltrados.length === 0) {
            grid.style.display = 'none';
            if (noResults) noResults.style.display = 'block';
            if (productCount) productCount.textContent = '0';
            return;
        }
        
        grid.style.display = 'grid';
        if (noResults) noResults.style.display = 'none';
        if (productCount) productCount.textContent = produtosFiltrados.length;
        
        grid.innerHTML = produtosFiltrados.map(produto => `
            <div class="produto-card" data-id="${produto.id}">
                <img src="${produto.imagem}" alt="${produto.nome}" class="produto-imagem" loading="lazy" onerror="this.src='https://via.placeholder.com/300x200?text=Sem+Imagem'">
                <div class="produto-info">
                    <span class="produto-categoria">${produto.categoria}</span>
                    <h3 class="produto-nome">${produto.nome}</h3>
                    <p class="produto-descricao">${produto.descricao.substring(0, 80)}${produto.descricao.length > 80 ? '...' : ''}</p>
                    <div class="produto-preco">
                        R$ ${typeof produto.preco === 'number' ? produto.preco.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : produto.preco_formatado}
                    </div>
                    <div class="produto-actions">
                        <button class="btn-detalhes" onclick='verDetalhesProdutoHome(${JSON.stringify(produto).replace(/'/g, "&#39;")})'>
                            Ver detalhes
                        </button>
                        <button class="btn-comprar" onclick='abrirModalCompra(${JSON.stringify(produto).replace(/'/g, "&#39;")})'>
                            Comprar
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    window.verDetalhesProdutoHome = function(produto) {
        if (typeof produto === 'string') {
            produto = JSON.parse(produto.replace(/&#39;/g, "'"));
        }
        abrirModalDetalhes(produto);
    };

    window.abrirModalCompra = abrirModalCompra;

    function filtrarProdutosHome() {
        const searchTerm = document.getElementById('searchInput')?.value.toLowerCase() || '';
        const category = document.getElementById('categoryFilter')?.value || 'todos';
        
        produtosFiltrados = todosProdutos.filter(produto => {
            const matchSearch = produto.nome.toLowerCase().includes(searchTerm) || 
                               produto.descricao.toLowerCase().includes(searchTerm);
            const matchCategory = category === 'todos' || produto.categoria.toLowerCase() === category;
            return matchSearch && matchCategory;
        });
        
        renderizarProdutosHome();
    }

    function limparFiltrosHome() {
        const searchInput = document.getElementById('searchInput');
        const categoryFilter = document.getElementById('categoryFilter');
        
        if (searchInput) searchInput.value = '';
        if (categoryFilter) categoryFilter.value = 'todos';
        
        produtosFiltrados = [...todosProdutos];
        renderizarProdutosHome();
    }

    // ================= FECHAR MODAIS CLICANDO FORA =================
    document.addEventListener('click', function(event) {
        const modalDetalhes = document.getElementById('modalDetalhes');
        const modalCompra = document.getElementById('modalCompra');
        
        if (event.target === modalDetalhes) {
            fecharModalDetalhes();
        }
        
        if (event.target === modalCompra) {
            fecharModalCompra();
        }
    });

    // ================= FECHAR MODAIS COM TECLA ESC =================
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            fecharModalDetalhes();
            fecharModalCompra();
        }
    });

    // ================= INICIALIZAÇÃO PRINCIPAL =================
    checkTokenInUrl();
    carregarProdutosHome();
    
    const searchInput = document.getElementById('searchInput');
    const categoryFilter = document.getElementById('categoryFilter');
    const clearBtn = document.getElementById('clearFilterBtn');
    
    if (searchInput) {
        searchInput.addEventListener('input', filtrarProdutosHome);
    }
    
    if (categoryFilter) {
        categoryFilter.addEventListener('change', filtrarProdutosHome);
    }
    
    if (clearBtn) {
        clearBtn.addEventListener('click', limparFiltrosHome);
    }
    
    const menuMobile = document.getElementById('menuMobile');
    const navLinks = document.querySelector('.nav-links');
    
    if (menuMobile && navLinks) {
        menuMobile.addEventListener('click', () => {
            menuMobile.classList.toggle('active');
            navLinks.classList.toggle('active');
        });
    }
});