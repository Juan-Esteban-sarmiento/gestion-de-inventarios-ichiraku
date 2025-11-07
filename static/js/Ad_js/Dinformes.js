// ⚡ Buscar informes - CORREGIDO
document.getElementById('searchForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id_informe = document.getElementById('id_informe').value.trim();
    const fecha = document.getElementById('datePicker').value.trim(); // CORREGIDO: era 'date'

    console.log("🔍 Buscando:", { id_informe, fecha });

    if (!id_informe && !fecha)
        return alertaNinja('warning', 'Campos vacíos', 'Debes ingresar un ID o una fecha.');

    try {
        const res = await fetch('/buscar_informe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_informe, fecha })
        });
        
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        
        const data = await res.json();
        console.log("📊 Respuesta del servidor:", data);
        
        const resultBox = document.getElementById('resultEmpleado');

        if (data.success && data.informes && data.informes.length > 0) {
            resultBox.innerHTML = `
                <div class="download-container">
                ${data.informes.map(inf => `
                    <div class="informe-card">
                    <p><span>ID Informe</span>${inf.id_informe}</p>
                    <p><span>ID Pedido</span>${inf.id_inf_pedido}</p>
                    <p><span>Fecha</span>${new Date(inf.fecha_creacion).toLocaleString('es-CO')}</p>
                    <button class="download-button" onclick="descargarInforme(${inf.id_informe})">
                        Descargar PDF
                    </button>
                    </div>
                `).join('')}
                </div>
            `;
        } else {
            resultBox.innerHTML = `<p>No se encontraron informes</p>`;
            alertaNinja('info', 'Sin resultados', data.msg || 'No hay informes con esos datos.');
        }
    } catch (err) {
        console.error("❌ Error en búsqueda:", err);
        alertaNinja('error', 'Error del servidor', 'No se pudo realizar la búsqueda.');
    }
});

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
            inputValue: new Date().getFullYear(),
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
        fecha_inicio = anio.toString();
    }

    alertaNinja('info', 'Generando informe', 'Por favor espera mientras se crea el PDF...');

    try {
        const res = await fetch('/descargar_informes_rango', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tipo, fecha_inicio, fecha_fin })
        });
        
        if (!res.ok) throw new Error('Respuesta no válida');
        
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `informe_unificado_${tipo}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
    } catch (error) {
        console.error("❌ Error al descargar:", error);
        alertaNinja('error', 'Error', 'No se pudo generar o descargar el informe.');
    }
}

// Reemplazar la función de generar informe diario
$('#genDayBtn').click(() => {
    Swal.fire({
        title: '¿Generar informe diario consolidado?',
        text: 'Se creará un único informe con todos los pedidos de hoy.',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Sí, generar',
        cancelButtonText: 'Cancelar',
        background: '#000',
        color: '#fff',
        confirmButtonColor: '#e63900',
        cancelButtonColor: '#555'
    }).then(async (result) => {
        if (result.isConfirmed) {
            try {
                const response = await fetch('/generar_informe_diario', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alertaNinja('success', 'Éxito', data.msg);
                    // Actualizar la vista con el nuevo informe
                    await actualizarVistaDespuesDeGenerar();
                    // Descargar automáticamente el informe recién creado
                    if (data.informe_id) {
                        setTimeout(() => {
                            window.open(`/descargar_informe/${data.informe_id}`, '_blank');
                        }, 1000);
                    }
                } else {
                    // Si ya existe un informe, ofrecer descargarlo
                    if (data.informe_id) {
                        Swal.fire({
                            title: 'Informe ya existe',
                            text: data.msg,
                            icon: 'info',
                            showCancelButton: true,
                            confirmButtonText: 'Descargar',
                            cancelButtonText: 'Cancelar',
                            background: '#000',
                            color: '#fff',
                            confirmButtonColor: '#e63900'
                        }).then(async (result) => {
                            if (result.isConfirmed) {
                                window.open(`/descargar_informe/${data.informe_id}`, '_blank');
                            }
                            // Actualizar la vista de todos modos
                            await actualizarVistaDespuesDeGenerar();
                        });
                    } else {
                        alertaNinja('warning', 'Atención', data.msg);
                    }
                }
            } catch (error) {
                console.error('Error:', error);
                alertaNinja('error', 'Error', 'No se pudo generar el informe diario.');
            }
        }
    });
});

// 📅 Inicializar calendario Flatpickr
flatpickr("#datePicker", {
    dateFormat: "Y-m-d",
    locale: "es",
    maxDate: "today",
    onChange: async function(selectedDates, dateStr) {
        if (dateStr) {
            await buscarPorFecha(dateStr);
        }
    }
});

// 🔍 Buscar automáticamente al seleccionar fecha
async function buscarPorFecha(fecha) {
    const resultBox = document.getElementById('resultEmpleado');
    try {
        const res = await fetch('/buscar_informe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fecha })
        });
        const data = await res.json();

        if (data.success && data.informes?.length) {
            resultBox.innerHTML = `
                <div class="download-container">
                ${data.informes.map(inf => `
                    <div class="informe-card">
                    <p><span>ID Informe</span>${inf.id_informe}</p>
                    <p><span>ID Pedido</span>${inf.id_inf_pedido}</p>
                    <p><span>Fecha</span>${new Date(inf.fecha_creacion).toLocaleString('es-CO')}</p>
                    <button class="download-button" onclick="descargarInforme(${inf.id_informe})">
                        Descargar PDF
                    </button>
                    </div>
                `).join('')}
                </div>
            `;
        } else {
            resultBox.innerHTML = `<p>No se encontraron informes en esta fecha.</p>`;
            alertaNinja('info', 'Sin resultados', 'No hay informes registrados en esta fecha.');
        }
    } catch (error) {
        console.error("❌ Error al buscar informes por fecha:", error);
        alertaNinja('error', 'Error', 'No se pudo realizar la búsqueda por fecha.');
    }
}
// 📋 Cargar último informe automáticamente al iniciar la página
document.addEventListener('DOMContentLoaded', function() {
    console.log("🔄 Cargando último informe...");
    cargarUltimoInforme();
});

// 🔄 Función para cargar el último informe
async function cargarUltimoInforme() {
    try {
        const res = await fetch('/obtener_ultimo_informe');
        const data = await res.json();
        
        const resultBox = document.getElementById('resultEmpleado');
        
        if (data.success && data.informe) {
            const inf = data.informe;
            resultBox.innerHTML = `
                <div class="download-container">
                    <div class="informe-card">
                        <p><span>ID Informe:</span> ${inf.id_informe}</p>
                        <p><span>ID Pedido:</span> ${inf.id_inf_pedido || 'Consolidado'}</p>
                        <p><span>Fecha de creación:</span> ${new Date(inf.fecha_creacion).toLocaleString('es-CO')}</p>
                        <p><span>Tipo:</span> ${inf.tipo === 'diario_consolidado' ? 'Informe Diario Consolidado' : 'Individual'}</p>
                        <button class="download-button" onclick="descargarInforme(${inf.id_informe})">
                            Descargar PDF
                        </button>
                    </div>
                </div>
            `;
        } else {
            resultBox.innerHTML = '<p>No hay informes generados aún.</p>';
        }
    } catch (error) {
        console.error("❌ Error al cargar último informe:", error);
        document.getElementById('resultEmpleado').innerHTML = '<p>Error al cargar informes.</p>';
    }
}

// 🔄 Función para actualizar la vista después de generar un nuevo informe
async function actualizarVistaDespuesDeGenerar() {
    await cargarUltimoInforme();
}


// 📥 Botones de descarga
$('#downloadSemBtn').click(() => descargarPorRango('semana'));
$('#downloadMesBtn').click(() => descargarPorRango('mes'));
$('#downloadAnioBtn').click(() => descargarPorRango('anio'));

// Función de debug para probar la búsqueda
window.probarBusqueda = async function(id) {
    console.log("🧪 Probando búsqueda con ID:", id);
    try {
        const res = await fetch('/buscar_informe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_informe: id })
        });
        const data = await res.json();
        console.log("✅ Respuesta:", data);
        return data;
    } catch (error) {
        console.error("❌ Error:", error);
        return null;
    }
};