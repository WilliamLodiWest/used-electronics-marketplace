// Menu Mobile
document.addEventListener('DOMContentLoaded', function() {
    const menuMobile = document.getElementById('menuMobile');
    const navLinks = document.querySelector('.nav-links');
    
    if (menuMobile && navLinks) {
        menuMobile.addEventListener('click', function() {
            navLinks.classList.toggle('active');
            menuMobile.classList.toggle('active');
        });
    }
    
    // Scroll suave para âncoras
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Fechar menu mobile ao clicar em um link
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', function() {
            if (navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
                menuMobile.classList.remove('active');
            }
        });
    });
});