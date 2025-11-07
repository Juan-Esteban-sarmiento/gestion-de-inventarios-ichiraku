// 📅 Inicializar calendario Flatpickr
document.addEventListener('DOMContentLoaded', function() {
    flatpickr("#fechaInforme", {
        dateFormat: "Y-m-d",
        locale: "es",
        maxDate: "today",
        onChange: function(selectedDates, dateStr) {
            if (dateStr) {
                buscarPorFecha(dateStr);
            }
        }
    });
});

// 🔍 Buscar informes
async function buscarInforme() {
    const idInforme = document.getElementById('idInforme').value.trim();
    const fecha = document.getElementById('fechaInforme').value.trim();

    if (!idInforme && !fecha) {
        alertaNinja('warning', 'Campos vacíos', 'Debes ingresar un ID o una fecha.');
        return;
    }

    try {
        const res = await fetch('/buscar_informe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                id_informe: idInforme || null, 
                fecha: fecha || null 
            })
        });
        const data = await res.json();
        const resultBox = document.getElementById('resultadosBusqueda');

        if (data.success && data.informes && data.informes.length > 0) {
            let html = '<div class="download-container">';
            data.informes.forEach(inf => {
                html += `
                <div class="informe-card">
                    <p><span>ID Informe</span>${inf.id_informe}</p>
                    <p><span>ID Pedido</span>${inf.id_inf_pedido}</p>
                    <p><span>Fecha</span>${new Date(inf.fecha_creacion).toLocaleString('es-CO')}</p>
                    <button class="download-button" onclick="descargarInforme(${inf.id_informe})">
                        Descargar PDF
                    </button>
                </div>
                `;
            });
            html += '</div>';
            resultBox.innerHTML = html;
        } else {
            resultBox.innerHTML = '<p class="no-results">No se encontraron informes</p>';
            alertaNinja('info', 'Sin resultados', data.msg || 'No hay informes con esos datos.');
        }
    } catch (err) {
        console.error("❌ Error en búsqueda:", err);
        alertaNinja('error', 'Error del servidor', 'No se pudo realizar la búsqueda.');
    }
}

// 🔍 Buscar automáticamente al seleccionar fecha
async function buscarPorFecha(fecha) {
    const resultBox = document.getElementById('resultadosBusqueda');
    try {
        const res = await fetch('/buscar_informe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fecha })
        });
        const data = await res.json();

        if (data.success && data.informes && data.informes.length > 0) {
            let html = '<div class="download-container">';
            data.informes.forEach(inf => {
                html += `
                <div class="informe-card">
                    <p><span>ID Informe</span>${inf.id_informe}</p>
                    <p><span>ID Pedido</span>${inf.id_inf_pedido}</p>
                    <p><span>Fecha</span>${new Date(inf.fecha_creacion).toLocaleString('es-CO')}</p>
                    <button class="download-button" onclick="descargarInforme(${inf.id_informe})">
                        Descargar PDF
                    </button>
                </div>
                `;
            });
            html += '</div>';
            resultBox.innerHTML = html;
        } else {
            resultBox.innerHTML = '<p class="no-results">No se encontraron informes en esta fecha.</p>';
            alertaNinja('info', 'Sin resultados', 'No hay informes registrados en esta fecha.');
        }
    } catch (error) {
        console.error("❌ Error al buscar informes por fecha:", error);
        alertaNinja('error', 'Error', 'No se pudo realizar la búsqueda por fecha.');
    }
}

// 🧾 Descargar un informe específico
function descargarInforme(id) {
    alertaNinja('info', 'Descargando informe', 'Tu archivo PDF se está generando...');
    setTimeout(() => window.open(`/descargar_informe/${id}`, '_blank'), 800);
}

// 🕓 Descargar informes por rango
async function descargarPorRango(tipo) {
    let fecha_inicio, fecha_fin;

    if (tipo === 'semana') {
        const { value: rango } = await Swal.fire({
            title: '<span style="font-family:njnaruto; color:#fff;">Selecciona el rango de fechas</span>',
            html: `
                <input type="date" id="inicio" class="swal2-input" style="background:#111; color:#fff; border:2px solid #e60000; font-family:njnaruto;">
                <input type="date" id="fin" class="swal2-input" style="background:#111; color:#fff; border:2px solid #e60000; font-family:njnaruto;">
            `,
            background: '#000',
            color: '#fff',
            confirmButtonText: '<span style="font-family:njnaruto;">Descargar</span>',
            confirmButtonColor: '#e60000',
            buttonsStyling: false,
            didRender: () => {
                const btn = Swal.getConfirmButton();
                if (btn) {
                    btn.style.background = '#e60000';
                    btn.style.color = '#fff';
                    btn.style.fontWeight = 'bold';
                    btn.style.border = '2px solid #ff0000ff';
                    btn.style.borderRadius = '8px';
                    btn.style.padding = '8px 16px';
                    btn.style.transition = '0.3s';
                    btn.addEventListener('mouseenter', () => (btn.style.background = '#ff0000ff'));
                    btn.addEventListener('mouseleave', () => (btn.style.background = '#e60000'));
                }
            },
            preConfirm: () => ({
                inicio: document.getElementById('inicio').value,
                fin: document.getElementById('fin').value
            })
        });
        if (!rango?.inicio || !rango?.fin) return;
        fecha_inicio = `${rango.inicio}T00:00:00`;
        fecha_fin = `${rango.fin}T23:59:59`;

    } else if (tipo === 'mes') {
        const { value: mes } = await Swal.fire({
            title: '<span style="font-family:njnaruto; color:#fff;">Selecciona el mes</span>',
            input: 'month',
            inputLabel: 'Mes a descargar',
            background: '#000',
            color: '#fff',
            confirmButtonText: '<span style="font-family:njnaruto;">Descargar</span>',
            confirmButtonColor: '#e60000',
            buttonsStyling: false,
            didRender: () => {
                const btn = Swal.getConfirmButton();
                if (btn) {
                    btn.style.background = '#e60000';
                    btn.style.color = '#fff';
                    btn.style.fontWeight = 'bold';
                    btn.style.border = '2px solid #ff0000ff';
                    btn.style.borderRadius = '8px';
                    btn.style.padding = '8px 16px';
                    btn.style.transition = '0.3s';
                    btn.addEventListener('mouseenter', () => (btn.style.background = '#ff0000ff'));
                    btn.addEventListener('mouseleave', () => (btn.style.background = '#e60000'));
                }
            }
        });
        if (!mes) return;
        fecha_inicio = mes;

    } else if (tipo === 'anio') {
        const { value: anio } = await Swal.fire({
            title: '<span style="font-family:njnaruto; color:#fff;">Selecciona el año</span>',
            input: 'number',
            inputLabel: 'Año a descargar',
            inputAttributes: { min: 2000, max: 2100 },
            background: '#000',
            color: '#fff',
            confirmButtonText: '<span style="font-family:njnaruto;">Descargar</span>',
            confirmButtonColor: '#e60000',
            buttonsStyling: false,
            didRender: () => {
                const btn = Swal.getConfirmButton();
                if (btn) {
                    btn.style.background = '#e60000';
                    btn.style.color = '#fff';
                    btn.style.fontWeight = 'bold';
                    btn.style.border = '2px solid #ff0000ff';
                    btn.style.borderRadius = '8px';
                    btn.style.padding = '8px 16px';
                    btn.style.transition = '0.3s';
                    btn.addEventListener('mouseenter', () => (btn.style.background = '#ff0000ff'));
                    btn.addEventListener('mouseleave', () => (btn.style.background = '#e60000'));
                }
            }
        });
        if (!anio) return;
        fecha_inicio = anio;
    }

    alertaNinja('info', 'Generando informe', 'Por favor espera mientras se crea el PDF...');

    try {
        const res = await fetch('/descargar_informes_rango', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tipo, fecha_inicio, fecha_fin })
        });
        
        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `informe_unificado_${tipo}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            alertaNinja('success', 'Éxito', 'Informe descargado correctamente.');
        } else {
            throw new Error('Respuesta no válida');
        }
    } catch {
        alertaNinja('error', 'Error', 'No se pudo generar o descargar el informe.');
    }
}

// 🚀 Generar informe diario
function generarInformeDiario() {
    Swal.fire({
        title: '¿Generar informe diario?',
        text: 'Se crearán informes para los pedidos del día actual.',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Sí, generar',
        cancelButtonText: 'Cancelar',
        background: '#000',
        color: '#fff',
        confirmButtonColor: '#e63900',
        cancelButtonColor: '#555'
    }).then(result => {
        if (result.isConfirmed) {
            fetch('/generar_informe_diario', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alertaNinja('success', 'Éxito', data.msg).then(() => {
                        location.reload();
                    });
                } else {
                    alertaNinja('error', 'Error', data.msg);
                }
            })
            .catch(error => {
                alertaNinja('error', 'Error', 'Error al generar informe diario');
            });
        }
    });
}