document.addEventListener('click', function(e){
    const item = e.target.closest('.notification-item');
    if(!item) return;

    const id = item.getAttribute('data-id');

    // Botón Prioritaria
    if(e.target.classList.contains('btn-prioritaria')){
        fetch(`/marcar_prioritaria/${id}`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if(data.success){
                    item.classList.remove('resuelta');
                    item.classList.add('prioritaria');
                    Swal.fire('¡Listo!', 'Notificación marcada como prioritaria', 'success');
                }
            });
    }

    // Botón Resuelta
    if(e.target.classList.contains('btn-resuelta')){
        fetch(`/marcar_leido/${id}`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if(data.success){
                    item.classList.remove('prioritaria');
                    item.classList.add('resuelta');
                    item.querySelector('.notification-buttons').innerHTML = `<span class="check-icon">✔</span>`;
                    Swal.fire('¡Listo!', 'Notificación marcada como resuelta', 'success');
                }
            });
    }
});
