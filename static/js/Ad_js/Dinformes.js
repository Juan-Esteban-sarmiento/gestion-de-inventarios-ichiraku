// ⚡ Buscar informes
document.getElementById('searchForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id_informe = document.getElementById('id_informe').value.trim();
    const fecha = document.getElementById('datePicker').value.trim();

    if (!id_informe && !fecha)
        return alertaNinja('warning', 'Campos vacíos', 'Debes ingresar un ID o una fecha para buscar.');

    try {
        const res = await fetch('/buscar_informe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_informe, fecha })
        });

        const data = await res.json();
        const resultBox = document.getElementById('resultEmpleado');

        if (data.success && data.informes && data.informes.length > 0) {
            resultBox.innerHTML = `
                <div class="download-container">
                ${data.informes.map(inf => `
                    <div class="informe-card">
                        <p><span>ID Informe</span> ${inf.id_informe}</p>
                        <p><span>ID Pedido</span> ${inf.id_inf_pedido || 'Consolidado'}</p>
                        <p><span>Fecha</span> ${new Date(inf.fecha_creacion).toLocaleString('es-CO')}</p>
                        <button class="download-button" onclick="descargarInforme(${inf.id_informe})">
                            Descargar PDF
                        </button>
                    </div>
                `).join('')}
                </div>
            `;
        } else {
            resultBox.innerHTML = `<p style="text-align:center; color:#666; padding:20px;">No se hallaron resultados.</p>`;
            alertaNinja('info', 'Sin resultados', 'No hay informes con esos datos.');
        }
    } catch (err) { alertaNinja('error', 'Error', 'No se pudo realizar la búsqueda.'); }
});

// 🧾 Descargar informe
function descargarInforme(id) {
    alertaNinja('success', 'Descarga Iniciada', 'Tu archivo PDF se está generando...');
    setTimeout(() => window.open(`/descargar_informe/${id}`, '_blank'), 800);
}

// 🕓 Descargar por rango (Usa alertaNinjaFire para mantener el estilo)
async function descargarPorRango(tipo) {
    let fecha_inicio, fecha_fin;

    if (tipo === 'semana') {
        const res = await alertaNinjaFire({
            title: 'Seleccionar Semana',
            html: `
                <div style="text-align:left; gap:10px; display:flex; flex-direction:column;">
                    <label style="color:#aaa; font-size:11px; text-transform:uppercase;">Desde:</label>
                    <input type="date" id="inicio" class="swal2-input ninja-swal-input">
                    <label style="color:#aaa; font-size:11px; text-transform:uppercase; margin-top:10px;">Hasta:</label>
                    <input type="date" id="fin" class="swal2-input ninja-swal-input">
                </div>
            `,
            showCancelButton: true,
            confirmButtonText: 'GENERAR SEMANAL',
            cancelButtonText: 'VOLVER',
            didOpen: () => {
                const hoy = new Date();
                const inicioSem = new Date(hoy); inicioSem.setDate(hoy.getDate() - 7);
                flatpickr('#inicio', { locale: 'es', defaultDate: inicioSem });
                flatpickr('#fin', { locale: 'es', defaultDate: hoy });
            },
            preConfirm: () => {
                const i = document.getElementById('inicio').value;
                const f = document.getElementById('fin').value;
                if (!i || !f) { Swal.showValidationMessage('Ambas fechas son obligatorias'); return false; }
                if (new Date(i) > new Date(f)) { Swal.showValidationMessage('Fecha inicio inválida'); return false; }
                return { i, f };
            }
        });
        if (!res.isConfirmed) return;
        fecha_inicio = `${res.value.i}T00:00:00`; fecha_fin = `${res.value.f}T23:59:59`;

    } else if (tipo === 'mes') {
        const res = await alertaNinjaFire({
            title: 'Seleccionar Mes',
            html: `
                <input type="month" id="mesInput" class="swal2-input ninja-swal-input">
            `,
            showCancelButton: true,
            confirmButtonText: 'GENERAR MENSUAL',
            cancelButtonText: 'VOLVER',
            preConfirm: () => {
                const val = document.getElementById('mesInput').value;
                if (!val) { Swal.showValidationMessage('Debes elegir un mes'); return false; }
                return val;
            }
        });
        if (!res.isConfirmed) return;
        const [y, m] = res.value.split('-');
        const last = new Date(y, m, 0).getDate();
        fecha_inicio = `${res.value}-01T00:00:00`;
        fecha_fin = `${y}-${m}-${last.toString().padStart(2, '0')}T23:59:59`;

    } else if (tipo === 'anio') {
        const res = await alertaNinjaFire({
            title: 'Seleccionar Año',
            input: 'number',
            inputAttributes: { min: 2020, max: 2030 },
            inputValue: new Date().getFullYear(),
            showCancelButton: true,
            confirmButtonText: 'GENERAR ANUAL',
            cancelButtonText: 'VOLVER'
        });
        if (!res.isConfirmed) return;
        fecha_inicio = `${res.value}-01-01T00:00:00`; fecha_fin = `${res.value}-12-31T23:59:59`;
    }

    alertaNinja('info', 'Generando PDF', 'Por favor espera un momento...');
    ejecutarDescargaRango(tipo, fecha_inicio, fecha_fin);
}

// 🌐 Helper para la descarga real
async function ejecutarDescargaRango(tipo, inicio, fin) {
    try {
        const res = await fetch('/descargar_informes_rango', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tipo, fecha_inicio: inicio, fecha_fin: fin })
        });
        if (res.headers.get('content-type').includes('application/pdf')) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url;
            a.download = `reporte_${tipo}_ichiraku.pdf`;
            a.click();
            alertaNinja('success', '¡Completado!', 'El reporte se ha descargado.');
        } else {
            const data = await res.json();
            alertaNinja('warning', 'Sin datos', data.msg);
        }
    } catch (e) { alertaNinja('error', 'Error', 'Fallo al procesar el reporte.'); }
}

// 🔥 Informe Diario Consolidado
$('#genDayBtn').click(async () => {
    const confirm = await alertaNinjaFire({
        icon: 'question',
        title: 'Informe Diario',
        text: '¿Generar el reporte consolidado de ventas de hoy?',
        showCancelButton: true,
        confirmButtonText: 'SÍ, GENERAR',
        cancelButtonText: 'CANCELAR'
    });

    if (confirm.isConfirmed) {
        try {
            const response = await fetch('/generar_informe_diario', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            if (data.success) {
                alertaNinja('success', '¡Éxito!', data.msg);
                await cargarUltimoInforme();
                if (data.informe_id) window.open(`/descargar_informe/${data.informe_id}`, '_blank');
            } else if (data.informe_id) {
                const retry = await alertaNinjaFire({
                    icon: 'info',
                    title: 'Ya existe',
                    text: 'Ya hay un informe de hoy. ¿Deseas descargarlo?',
                    showCancelButton: true,
                    confirmButtonText: 'DESCARGAR',
                    cancelButtonText: 'CERRAR'
                });
                if (retry.isConfirmed) window.open(`/descargar_informe/${data.informe_id}`, '_blank');
            } else { alertaNinja('warning', 'Aviso', data.msg); }
        } catch (e) { alertaNinja('error', 'Error', 'No se pudo conectar.'); }
    }
});

// 📅 Calendario Flatpickr Sidebar
flatpickr("#datePicker", {
    dateFormat: "Y-m-d",
    locale: "es",
    maxDate: "today",
    onChange: (d, str) => { if (str) buscarPorFecha(str); }
});

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
            resultBox.innerHTML = `<div class="download-container">${data.informes.map(inf => `
                <div class="informe-card">
                    <p><span>ID Informe</span> ${inf.id_informe}</p>
                    <p><span>Fecha</span> ${new Date(inf.fecha_creacion).toLocaleString('es-CO')}</p>
                    <button class="download-button" onclick="descargarInforme(${inf.id_informe})">Bajar PDF</button>
                </div>`).join('')}</div>`;
        } else { resultBox.innerHTML = `<p style="text-align:center; color:#666;">No hay reportes esta fecha.</p>`; }
    } catch (e) { alertaNinja('error', 'Error', 'Fallo en búsqueda.'); }
}

async function cargarUltimoInforme() {
    try {
        const res = await fetch('/obtener_ultimo_informe');
        const data = await res.json();
        const box = document.getElementById('resultEmpleado');
        if (data.success && data.informe) {
            const inf = data.informe;
            box.innerHTML = `
                <div class="download-container">
                    <div class="informe-card">
                        <p><span>ID Informe:</span> ${inf.id_informe}</p>
                        <p><span>Fecha:</span> ${new Date(inf.fecha_creacion).toLocaleString('es-CO')}</p>
                        <p><span>Tipo:</span> ${inf.tipo === 'diario_consolidado' ? 'Consolidado' : 'Individual'}</p>
                        <button class="download-button" onclick="descargarInforme(${inf.id_informe})">DESCARGAR PDF</button>
                    </div>
                </div>`;
        } else { box.innerHTML = '<p style="text-align:center; color:#666;">No hay reportes generados.</p>'; }
    } catch (e) { console.error(e); }
}

document.addEventListener('DOMContentLoaded', cargarUltimoInforme);
$('#downloadSemBtn').click(() => descargarPorRango('semana'));
$('#downloadMesBtn').click(() => descargarPorRango('mes'));
$('#downloadAnioBtn').click(() => descargarPorRango('anio'));