// static/app.js

document.addEventListener('DOMContentLoaded', function () {
    const qs = (sel, el = document) => el.querySelector(sel);
    const qsa = (sel, el = document) => el.querySelectorAll(sel);

    // --- Sidebar Menu Logic (from PucrsCorp) ---
    qsa('.sidebar-nav .has-submenu > a').forEach(link => {
        link.addEventListener('click', function(e) {
            // Prevent link from navigating if it's just for toggling
            if (this.getAttribute('href') === '#') {
                e.preventDefault();
            }

            const parentLi = this.closest('.has-submenu');
            const submenu = parentLi.querySelector('.submenu');
            const arrowIcon = this.querySelector('.arrow-icon');

            if (submenu) {
                // Toggle active classes
                parentLi.classList.toggle('active');
                submenu.classList.toggle('open');
                arrowIcon?.classList.toggle('open');
            }
        });
    });


    // --- Back to Top Button ---
    const backToTopBtn = qs('#back-to-top-btn');
    if (backToTopBtn) {
        const mainContent = qs('.main-content');
        mainContent?.addEventListener('scroll', () => {
            if (mainContent.scrollTop > 300) {
                backToTopBtn.classList.add('visible');
            } else {
                backToTopBtn.classList.remove('visible');
            }
        });

        backToTopBtn.addEventListener('click', () => {
            mainContent.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }
});

// Helper function for debouncing
function debounce(func, delay = 250) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}