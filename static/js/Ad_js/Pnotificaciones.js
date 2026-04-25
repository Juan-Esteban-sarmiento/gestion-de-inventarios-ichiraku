let currentPage = 1;

document.getElementById('btn-load-more')?.addEventListener('click', function() {
    currentPage++;
    const btn = this;
    const container = document.getElementById('load-more-container');
    
    btn.disabled = true;
    btn.textContent = 'Cargando...';

    fetch(`/get_notificaciones_paginadas?page=${currentPage}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const list = document.getElementById('notifications-list');
                
                if (data.notificaciones.length > 0) {
                    data.notificaciones.forEach(noti => {
                        const item = document.createElement('div');
                        item.className = `notification-item ${noti.tipo === 'prioritaria' ? 'prioritaria' : ''}`;
                        item.setAttribute('data-id', noti.id_notificaciones);
                        
                        // Formatear fecha simple (AAAA-MM-DD)
                        const fechaSimple = noti.fecha ? noti.fecha.substring(0, 10) : '';
                        
                        item.innerHTML = `
                            <img src="/static/image/campana.png" class="icon-left" alt="Campana">
                            <span class="notification-text">
                                ${noti.mensaje} <br>
                                <small>${fechaSimple}</small>
                            </span>
                        `;
                        list.appendChild(item);
                    });
                }

                if (!data.has_more) {
                    container.style.display = 'none';
                } else {
                    btn.disabled = false;
                    btn.textContent = 'Cargar mas avisos';
                }
            } else {
                Swal.fire('Error', 'No se pudieron cargar mas avisos', 'error');
                btn.disabled = false;
                btn.textContent = 'Cargar mas avisos';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            btn.disabled = false;
            btn.textContent = 'Cargar mas avisos';
        });
});

document.addEventListener('click', function(e) {
    const item = e.target.closest('.notification-item');
    if (!item) return;

    const id = item.getAttribute('data-id');

    // Boton Prioritaria (si se llegara a habilitar en el futuro)
    if (e.target.classList.contains('btn-prioritaria')) {
        fetch(`/marcar_prioritaria/${id}`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    item.classList.add('prioritaria');
                    Swal.fire('Listo!', 'Notificacion marcada como prioritaria', 'success');
                }
            });
    }
});
