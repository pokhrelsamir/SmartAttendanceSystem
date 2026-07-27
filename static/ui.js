(function () {
    function ensureToastStack() {
        let stack = document.querySelector('.toast-stack');
        if (!stack) {
            stack = document.createElement('div');
            stack.className = 'toast-stack';
            document.body.appendChild(stack);
        }
        return stack;
    }

    function toast(message, type = 'info') {
        const stack = ensureToastStack();
        const item = document.createElement('div');
        item.className = `toast ${type}`;
        item.textContent = message;
        stack.appendChild(item);

        window.setTimeout(() => {
            item.style.opacity = '0';
            item.style.transform = 'translateY(10px)';
            window.setTimeout(() => item.remove(), 180);
        }, 3200);
    }

    function confirmAction({ title = 'Confirm action', message = 'Do you want to continue?', confirmText = 'Continue', cancelText = 'Cancel' } = {}) {
        return new Promise(resolve => {
            const backdrop = document.createElement('div');
            backdrop.className = 'dialog-backdrop';
            backdrop.innerHTML = `
                <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="confirmTitle">
                    <h2 id="confirmTitle">${title}</h2>
                    <p>${message}</p>
                    <div class="dialog-actions">
                        <button type="button" class="button secondary" data-cancel>${cancelText}</button>
                        <button type="button" class="button" data-confirm>${confirmText}</button>
                    </div>
                </div>
            `;
            document.body.appendChild(backdrop);

            const finish = value => {
                backdrop.classList.remove('is-open');
                window.setTimeout(() => {
                    backdrop.remove();
                    resolve(value);
                }, 180);
            };

            backdrop.querySelector('[data-cancel]').addEventListener('click', () => finish(false));
            backdrop.querySelector('[data-confirm]').addEventListener('click', () => finish(true));
            backdrop.addEventListener('click', event => {
                if (event.target === backdrop) finish(false);
            });
            document.addEventListener('keydown', function escapeHandler(event) {
                if (event.key === 'Escape') {
                    document.removeEventListener('keydown', escapeHandler);
                    finish(false);
                }
            });

            requestAnimationFrame(() => backdrop.classList.add('is-open'));
            backdrop.querySelector('[data-confirm]').focus();
        });
    }

    function wireConfirmableLinks() {
        document.querySelectorAll('[data-confirm-link]').forEach(link => {
            link.addEventListener('click', async event => {
                event.preventDefault();
                const approved = await confirmAction({
                    title: link.dataset.confirmTitle || 'Open page?',
                    message: link.dataset.confirmMessage || 'This will take you to the selected page.',
                    confirmText: link.dataset.confirmText || 'Open'
                });

                if (approved) {
                    toast(link.dataset.confirmedMessage || 'Opening...');
                    window.location.href = link.href;
                }
            });
        });
    }

    function wireConfirmableForms() {
        document.querySelectorAll('form[data-confirm-form]').forEach(form => {
            form.addEventListener('submit', async event => {
                event.preventDefault();
                const approved = await confirmAction({
                    title: form.dataset.confirmTitle || 'Submit form?',
                    message: form.dataset.confirmMessage || 'Please confirm before continuing.',
                    confirmText: form.dataset.confirmText || 'Submit'
                });

                if (approved) {
                    toast(form.dataset.confirmedMessage || 'Submitting...');
                    form.submit();
                }
            });
        });
    }

    window.AppUI = {
        confirmAction,
        toast,
    };

    document.addEventListener('DOMContentLoaded', () => {
        wireConfirmableLinks();
        wireConfirmableForms();
    });
})();
