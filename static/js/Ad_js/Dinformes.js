// ⚡ Buscar informes
document.getElementById('searchForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id_informe = document.getElementById('id_informe').value.trim();
    const fecha = document.getElementById('datePicker').value.trim();

    if (!id_informe && !fecha)
        return alertaNinja('warning', 'Campos vacios', 'Debes ingresar un ID o una fecha para buscar.');

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
                <div class="informe-card-wrapper" style="max-width: none; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; width: 100%;">
                ${data.informes.map(inf => `
                    <div class="informe-card">
                        <div class="card-header">
                            <span class="report-id-badge">ID #${inf.id_informe}</span>
                            <span class="report-type-badge">${mapTipoInforme(inf.tipo, !!inf.id_inf_pedido)}</span>
                        </div>
                        <div class="card-body">
                            <div class="info-row">
                                <label>Fecha de creacion:</label>
                                <span>${new Date(inf.fecha_creacion).toLocaleString('es-CO')}</span>
                            </div>
                            <div class="info-row">
                                <label>Referencia:</label>
                                <span>${inf.id_inf_pedido ? 'Pedido #' + inf.id_inf_pedido : 'Cierre Diario'}</span>
                            </div>
                        </div>
                        <button class="download-button main-download" onclick="descargarInforme(${inf.id_informe})">
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
    } catch (err) { alertaNinja('error', 'Error', 'No se pudo realizar la busqueda.'); }
});

function descargarInforme(id) {
    alertaNinja('success', 'Descarga Iniciada', 'Tu archivo PDF se esta generando...');
    setTimeout(() => window.open(`/descargar_informe/${id}`, '_blank'), 800);
}

// 📊 Generar Reporte de Inventario (Vendido vs Merma) con validacion
async function generarReporteInventario() {
    const form = document.getElementById('inventoryReportForm');
    const localSelect = form.querySelector('select[name="id_local"]');
    const periodoSelect = form.querySelector('select[name="periodo"]');
    const fechaInput = form.querySelector('input[name="fecha"]');

    // Validaciones con alertas premium
    if (!localSelect.value) {
        alertaNinja('warning', 'LOCAL REQUERIDO', 'Debes seleccionar un local para generar el reporte.');
        localSelect.focus();
        return;
    }

    if (!fechaInput.value) {
        alertaNinja('warning', 'FECHA REQUERIDA', 'Debes seleccionar una fecha base para el reporte.');
        fechaInput.focus();
        return;
    }

    // Confirmacion antes de generar
    const confirmar = await confirmarNinja(
        'GENERAR REPORTE?',
        `Se generara el reporte de inventario (${periodoSelect.value}) para el local seleccionado.`
    );

    if (!confirmar.isConfirmed) return;

    // Mostrar loading
    alertaNinjaFire({
        title: 'Generando Reporte...',
        text: 'Por favor espera mientras se procesa tu informe.',
        allowOutsideClick: false,
        didOpen: () => { Swal.showLoading(); }
    });

    try {
        const formData = new FormData(form);
        const res = await fetch('/generar_reporte_personalizado', {
            method: 'POST',
            body: formData
        });

        if (res.ok && res.headers.get('content-type')?.includes('application/pdf')) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Informe_Inventario_${periodoSelect.value}_${fechaInput.value}.pdf`;
            a.click();
            window.URL.revokeObjectURL(url);
            Swal.close();
            alertaNinja('success', 'REPORTE GENERADO', 'El informe PDF se ha descargado correctamente.');
        } else {
            Swal.close();
            try {
                const data = await res.json();
                alertaNinja('warning', 'SIN DATOS', data.msg || 'No se pudo generar el reporte.');
            } catch {
                alertaNinja('warning', 'SIN DATOS', 'No se pudo generar el reporte. Verifica los datos ingresados.');
            }
        }
    } catch (err) {
        Swal.close();
        console.error('Error generando reporte:', err);
        alertaNinja('error', 'ERROR', 'No se pudo conectar con el servidor para generar el reporte.');
    }
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
                if (new Date(i) > new Date(f)) { Swal.showValidationMessage('Fecha inicio invalida'); return false; }
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
            title: 'Seleccionar Ano',
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
            alertaNinja('success', 'COMPLETADO', 'El reporte se ha descargado.');
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
        text: 'Generar el reporte consolidado de ventas de hoy?',
        showCancelButton: true,
        confirmButtonText: 'GENERAR',
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
                alertaNinja('success', 'EXITO', data.msg);
                await cargarUltimoInforme();
                if (data.informe_id) window.open(`/descargar_informe/${data.informe_id}`, '_blank');
            } else if (data.informe_id) {
                const retry = await alertaNinjaFire({
                    icon: 'info',
                    title: 'Ya existe',
                    text: 'Ya hay un informe de hoy. Deseas descargarlo?',
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
            resultBox.innerHTML = `
                <div class="informe-card-wrapper" style="max-width: none; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; width: 100%;">
                ${data.informes.map(inf => `
                    <div class="informe-card">
                        <div class="card-header">
                            <span class="report-id-badge">ID #${inf.id_informe}</span>
                            <span class="report-type-badge">${mapTipoInforme(inf.tipo, !!inf.id_inf_pedido)}</span>
                        </div>
                        <div class="card-body">
                            <div class="info-row">
                                <label>Fecha:</label>
                                <span>${new Date(inf.fecha_creacion).toLocaleString('es-CO')}</span>
                            </div>
                        </div>
                        <button class="download-button main-download" onclick="descargarInforme(${inf.id_informe})">Descargar PDF</button>
                    </div>`).join('')}</div>`;
        } else { resultBox.innerHTML = `<div class="empty-reports"><p>No hay reportes para esta fecha.</p></div>`; }
    } catch (e) { alertaNinja('error', 'Error', 'Fallo en busqueda.'); }
}

async function cargarUltimoInforme() {
    try {
        const res = await fetch('/obtener_ultimo_informe');
        const data = await res.json();
        const box = document.getElementById('resultEmpleado');
        if (data.success && data.informe) {
            const inf = data.informe;
            box.innerHTML = `
                <div class="informe-card-wrapper">
                    <div class="informe-card">
                        <div class="card-header">
                            <span class="report-id-badge">ID #${inf.id_informe}</span>
                            <span class="report-type-badge">${mapTipoInforme(inf.tipo, !!inf.id_inf_pedido)}</span>
                        </div>
                        <div class="card-body">
                            <div class="info-row">
                                <label>Ultimo reporte generado:</label>
                                <span>${new Date(inf.fecha_creacion).toLocaleString('es-CO')}</span>
                            </div>
                        </div>
                        <button class="download-button main-download" onclick="descargarInforme(${inf.id_informe})">DESCARGAR ULTIMO PDF</button>
                    </div>
                </div>`;
        } else { box.innerHTML = '<div class="empty-reports"><p>No hay reportes generados recientemente.</p></div>'; }
    } catch (e) { console.error(e); }
}

function mapTipoInforme(tipo, hasPedido) {
    if (tipo === 'diario_consolidado') return 'Consolidado Diario';
    if (tipo === 'inventario_premium') return 'Premium (Inventario)';
    if (tipo === 'consolidado_semana') return 'Consolidado Semanal';
    if (tipo === 'consolidado_mes') return 'Consolidado Mensual';
    if (tipo === 'consolidado_anio') return 'Consolidado Anual';
    if (hasPedido) return 'Reporte Pedido';
    return 'Informe Individual';
}

document.addEventListener('DOMContentLoaded', cargarUltimoInforme);
$('#downloadSemBtn').click(() => descargarPorRango('semana'));
$('#downloadMesBtn').click(() => descargarPorRango('mes'));
$('#downloadAnioBtn').click(() => descargarPorRango('anio'));