document.addEventListener('click', function(e) {
    const item = e.target.closest('.notification-item');
    if (!item) return;

    const id = item.getAttribute('data-id');

    // Botón Prioritaria
    if (e.target.classList.contains('btn-prioritaria')) {
        fetch(`/marcar_prioritaria/${id}`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    item.classList.add('prioritaria');
                    Swal.fire('¡Listo!', 'Notificación marcada como prioritaria', 'success');
                }
            });
    }
});
