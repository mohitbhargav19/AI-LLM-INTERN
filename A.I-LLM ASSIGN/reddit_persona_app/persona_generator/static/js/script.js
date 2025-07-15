document.addEventListener('DOMContentLoaded', function() {

    // =========================================================
    // 1. Hamburger Menu Toggle Functionality
    // =========================================================
    const hamburger = document.getElementById('hamburger');
    const navUl = document.querySelector('nav ul');

    if (hamburger && navUl) {
        hamburger.addEventListener('click', function() {
            navUl.classList.toggle('open'); // Toggle 'open' class on the ul
        });

        // Optional: Close menu when a link is clicked (useful for single-page sites)
        navUl.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navUl.classList.remove('open');
            });
        });
    }

    // =========================================================
    // 2. Persona Generation Form Handling (AJAX)
    // =========================================================
    const personaForm = document.getElementById('persona-form');
    const statusMessage = document.getElementById('status-message');
    const loadingIndicator = document.getElementById('loading-indicator');

    if (personaForm) {
        personaForm.addEventListener('submit', async function(event) {
            event.preventDefault(); // Prevent default form submission

            statusMessage.textContent = ''; // Clear previous messages
            statusMessage.classList.remove('success', 'error');
            loadingIndicator.classList.remove('is-hidden'); // Show loading spinner

            const formData = new FormData(personaForm);
            const redditUrl = formData.get('reddit_url');

            try {
                const response = await fetch(personaForm.action, {
                    method: 'POST',
                    body: formData,
                    // Django's CSRF token is automatically included by FormData if it's in the form
                });

                const data = await response.json();

                if (response.ok) { // Check if response status is 2xx
                    statusMessage.textContent = data.message || `Persona for u/${data.username} generated successfully! Redirecting...`;
                    statusMessage.classList.add('success');
                    // Redirect to the detail page after a short delay
                    setTimeout(() => {
                        window.location.href = `/persona/${data.persona_id}/`;
                    }, 1500);
                } else {
                    statusMessage.textContent = data.message || 'An error occurred during persona generation.';
                    statusMessage.classList.add('error');
                }
            } catch (error) {
                console.error('Fetch error:', error);
                statusMessage.textContent = 'Network error or server unreachable.';
                statusMessage.classList.add('error');
            } finally {
                loadingIndicator.classList.add('is-hidden'); // Hide loading spinner
            }
        });
    }

    // =========================================================
    // 3. Citations Toggle on Persona Detail Page
    // =========================================================
    document.querySelectorAll('.toggle-citations-btn').forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.dataset.target; // Get the ID from data-target attribute
            const citationsList = document.getElementById(targetId);

            if (citationsList) {
                citationsList.classList.toggle('is-hidden');
                if (citationsList.classList.contains('is-hidden')) {
                    this.textContent = `Show Citations (${this.textContent.match(/\((\d+)\)/)[1]})`; // Restore original count
                } else {
                    this.textContent = 'Hide Citations';
                }
            }
        });
    });

    // =========================================================
    // 4. Anti-Copying Measures (Basic Deterrents)
    // =========================================================

    // Disable Right-Click Context Menu
    document.addEventListener('contextmenu', function(event) {
        event.preventDefault();
    });

    // Disable Text Selection
    document.addEventListener('selectstart', function(event) {
        event.preventDefault();
    });

    // Basic Developer Tools Detection (More aggressive & less reliable)
    function checkDevToolsSize() {
        const threshold = 160;
        if (window.outerWidth - window.innerWidth > threshold ||
            window.outerHeight - window.innerHeight > threshold) {
            console.warn("Developer tools are open! Content protection activated.");
            document.body.style.userSelect = 'none';
            document.body.style.pointerEvents = 'none';
            document.body.style.opacity = '0.5';
        } else {
            document.body.style.userSelect = '';
            document.body.style.pointerEvents = '';
            document.body.style.opacity = '1';
        }
    }

    checkDevToolsSize();
    window.addEventListener('resize', checkDevToolsSize);

    // More aggressive (but often unreliable) keybind detection
    document.onkeydown = function(e) {
        if (e.keyCode == 123 ||
            (e.ctrlKey && e.shiftKey && (e.keyCode == 73 || e.keyCode == 74)) ||
            (e.ctrlKey && e.keyCode == 85)) {
            console.warn("Developer tools keybind detected! Action prevented.");
            e.preventDefault();
            return false;
        }
    };
});