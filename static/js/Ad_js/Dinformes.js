// ⚡ Buscar informes - CORREGIDO
document.getElementById('searchForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id_informe = document.getElementById('id_informe').value.trim();
    const fecha = document.getElementById('datePicker').value.trim(); // CORREGIDO: era 'date'

    console.log("🔍 Buscando:", { id_informe, fecha });

    if (!id_informe && !fecha)
        return alertaNinja('warning', 'Campos vacios', 'Debes ingresar un ID o una fecha.');

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
        console.error("❌ Error en busqueda:", err);
        alertaNinja('error', 'Error del servidor', 'No se pudo realizar la busqueda.');
    }
});

// 🧾 Descargar un informe especifico
function descargarInforme(id) {
    alertaNinja('info', 'Descargando informe', 'Tu archivo PDF se esta generando...');
    setTimeout(() => window.open(`/descargar_informe/${id}`, '_blank'), 800);
}

// 🕓 Descargar informes por rango - MEJORADO CON CALENDARIOS
async function descargarPorRango(tipo) {
    let fecha_inicio, fecha_fin;

    if (tipo === 'semana') {
        // Usar un datepicker que permita seleccionar rango
        const { value: rango } = await Swal.fire({
            title: '<span style="font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif; color:#fff;">Selecciona el rango de la semana</span>',
            html: `
                <div style="text-align: left; margin-bottom: 15px; margin-right: 100px;">
                    <label style="color: #fff; display: block; margin-bottom: 5px;">Fecha de inicio:</label>
                    <input type="date" id="inicio" class="swal2-input" style="background:#111; color:#fff; border:2px solid #e60000; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; width: 100%;">
                </div>
                <div style="text-align: left; margin-right: 100px;">
                    <label style="color: #fff; display: block; margin-bottom: 5px;">Fecha de fin:</label>
                    <input type="date" id="fin" class="swal2-input" style="background:#111; color:#fff; border:2px solid #e60000; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; width: 100%;">
                </div>
            `,
            background: '#000',
            color: '#fff',
            confirmButtonText: '<span style="font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif;">Descargar</span>',
            confirmButtonColor: '#e60000',
            cancelButtonText: '<span style="font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif;">Cancelar</span>',
            showCancelButton: true,
            buttonsStyling: false,
            didOpen: () => {
                // Establecer fechas por defecto (ultima semana) y activar flatpickr
                const hoy = new Date();
                const inicioSemana = new Date(hoy);
                inicioSemana.setDate(hoy.getDate() - 7);

                // Inicializar flatpickr en los inputs dentro del modal.
                // (Asumimos que flatpickr ya esta cargado en la pagina)
                try {
                    // Crear pickers con formato Y-m-d y localizacion en espanol
                    flatpickr('#inicio', {
                        dateFormat: 'Y-m-d',
                        locale: 'es',
                        maxDate: 'today',
                        defaultDate: inicioSemana.toISOString().split('T')[0],
                        allowInput: true
                    });

                    flatpickr('#fin', {
                        dateFormat: 'Y-m-d',
                        locale: 'es',
                        maxDate: 'today',
                        defaultDate: hoy.toISOString().split('T')[0],
                        allowInput: true
                    });
                } catch (e) {
                    // Si flatpickr no esta disponible, usar los inputs nativos como fallback
                    document.getElementById('inicio').value = inicioSemana.toISOString().split('T')[0];
                    document.getElementById('fin').value = hoy.toISOString().split('T')[0];
                }
            },
            didRender: () => {
                const btnConfirm = Swal.getConfirmButton();
                const btnCancel = Swal.getCancelButton();
                
                if (btnConfirm) {
                    btnConfirm.style.background = '#e60000';
                    btnConfirm.style.color = '#fff';
                    btnConfirm.style.fontWeight = 'bold';
                    btnConfirm.style.border = '2px solid #ff0000ff';
                    btnConfirm.style.borderRadius = '8px';
                    btnConfirm.style.padding = '8px 16px';
                    btnConfirm.style.transition = '0.3s';
                    btnConfirm.addEventListener('mouseenter', () => (btnConfirm.style.background = '#ff0000ff'));
                    btnConfirm.addEventListener('mouseleave', () => (btnConfirm.style.background = '#e60000'));
                }
                
                if (btnCancel) {
                    btnCancel.style.background = '#555';
                    btnCancel.style.color = '#fff';
                    btnCancel.style.border = '2px solid #777';
                    btnCancel.style.borderRadius = '8px';
                    btnCancel.style.padding = '8px 16px';
                }
            },
            preConfirm: () => {
                const inicio = document.getElementById('inicio').value;
                const fin = document.getElementById('fin').value;
                
                if (!inicio || !fin) {
                    Swal.showValidationMessage('Debes seleccionar ambas fechas');
                    return false;
                }
                
                if (new Date(inicio) > new Date(fin)) {
                    Swal.showValidationMessage('La fecha de inicio no puede ser mayor a la fecha de fin');
                    return false;
                }
                
                return { inicio, fin };
            }
        });
        
        if (!rango) return;
        fecha_inicio = `${rango.inicio}T00:00:00`;
        fecha_fin = `${rango.fin}T23:59:59`;

    } else if (tipo === 'mes') {
        // Usar un input HTML y activar flatpickr para mostrar un calendario de mes
        const { value: mes } = await Swal.fire({
            title: '<span style="font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif; color:#fff;">Selecciona el mes y año</span>',
            html: `
                <div style="text-align: left; margin-bottom: 15px; margin-right: 100px;">
                    <label style="color: #fff; display: block; margin-bottom: 5px;">Mes a descargar:</label>
                    <input type="text" id="mesInput" class="swal2-input" style="background:#111; color:#fff; border:2px solid #e60000; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; width: 100%;" placeholder="YYYY-MM">
                </div>
            `,
            background: '#000',
            color: '#fff',
            confirmButtonText: '<span style="font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif;">Descargar</span>',
            confirmButtonColor: '#e60000',
            cancelButtonText: '<span style="font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif;">Cancelar</span>',
            showCancelButton: true,
            buttonsStyling: false,
            didOpen: () => {
                // Inicializar flatpickr en el input del mes; si no esta disponible, usar input nativo 'month' como fallback
                try {
                    // Intentar usar flatpickr; si el plugin monthSelectPlugin esta disponible, lo usamos para una seleccion mas amigable
                    const opts = {
                        dateFormat: 'Y-m',
                        locale: 'es',
                        defaultDate: new Date(),
                        allowInput: true
                    };

                    // Si existe monthSelectPlugin, intentar incorporarlo
                    if (typeof monthSelectPlugin !== 'undefined') {
                        opts['plugins'] = [new monthSelectPlugin({ shorthand: true, dateFormat: 'Y-m' })];
                    }

                    flatpickr('#mesInput', opts);
                    // Si flatpickr inicializa, aseguramos que el valor por defecto sea YYYY-MM
                    const el = document.getElementById('mesInput');
                    if (el && !el.value) el.value = new Date().toISOString().slice(0, 7);
                } catch (e) {
                    // Fallback: usar input tipo month si flatpickr no esta cargado
                    try {
                        const input = document.getElementById('mesInput');
                        input.type = 'month';
                        input.value = new Date().toISOString().slice(0, 7);
                    } catch (err) {
                        // ultimo recurso: rellenar texto con YYYY-MM
                        const input = document.getElementById('mesInput');
                        if (input) input.value = new Date().toISOString().slice(0, 7);
                    }
                }
            },
            didRender: () => {
                const btnConfirm = Swal.getConfirmButton();
                const btnCancel = Swal.getCancelButton();
                
                if (btnConfirm) {
                    btnConfirm.style.background = '#e60000';
                    btnConfirm.style.color = '#fff';
                    btnConfirm.style.fontWeight = 'bold';
                    btnConfirm.style.border = '2px solid #ff0000ff';
                    btnConfirm.style.borderRadius = '8px';
                    btnConfirm.style.padding = '8px 16px';
                    btnConfirm.style.transition = '0.3s';
                    btnConfirm.addEventListener('mouseenter', () => (btnConfirm.style.background = '#ff0000ff'));
                    btnConfirm.addEventListener('mouseleave', () => (btnConfirm.style.background = '#e60000'));
                }
                
                if (btnCancel) {
                    btnCancel.style.background = '#555';
                    btnCancel.style.color = '#fff';
                    btnCancel.style.border = '2px solid #777';
                    btnCancel.style.borderRadius = '8px';
                    btnCancel.style.padding = '8px 16px';
                }
            },
            preConfirm: () => {
                const val = document.getElementById('mesInput').value;
                if (!val) {
                    Swal.showValidationMessage('Debes seleccionar un mes');
                    return false;
                }
                // Normalizar a YYYY-MM (si se selecciono una fecha completa, tomar los primeros 7 caracteres)
                const m = val.toString().slice(0, 7);
                const parts = m.split('-');
                if (parts.length !== 2 || parts[0].length !== 4) {
                    Swal.showValidationMessage('Formato de mes invalido');
                    return false;
                }
                return m;
            }
        });

        if (!mes) return;
        const [year, month] = mes.split('-');
        const ultimoDia = new Date(year, month, 0).getDate();

        fecha_inicio = `${mes}-01T00:00:00`;
        fecha_fin = `${year}-${month}-${ultimoDia.toString().padStart(2, '0')}T23:59:59`;

    } else if (tipo === 'anio') {
        // Usar input number para año
        const { value: anio } = await Swal.fire({
            title: '<span style="font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif; color:#fff;">Selecciona el año</span>',
            input: 'number',
            inputLabel: 'Año a descargar',
            inputAttributes: { 
                min: 2020, 
                max: 2030,
                step: 1
            },
            inputValue: new Date().getFullYear(),
            background: '#000',
            color: '#fff',
            confirmButtonText: '<span style="font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif;">Descargar</span>',
            confirmButtonColor: '#e60000',
            cancelButtonText: '<span style="font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif;">Cancelar</span>',
            showCancelButton: true,
            buttonsStyling: false,
            didRender: () => {
                const btnConfirm = Swal.getConfirmButton();
                const btnCancel = Swal.getCancelButton();
                
                if (btnConfirm) {
                    btnConfirm.style.background = '#e60000';
                    btnConfirm.style.color = '#fff';
                    btnConfirm.style.fontWeight = 'bold';
                    btnConfirm.style.border = '2px solid #ff0000ff';
                    btnConfirm.style.borderRadius = '8px';
                    btnConfirm.style.padding = '8px 16px';
                    btnConfirm.style.transition = '0.3s';
                    btnConfirm.addEventListener('mouseenter', () => (btnConfirm.style.background = '#ff0000ff'));
                    btnConfirm.addEventListener('mouseleave', () => (btnConfirm.style.background = '#e60000'));
                }
                
                if (btnCancel) {
                    btnCancel.style.background = '#555';
                    btnCancel.style.color = '#fff';
                    btnCancel.style.border = '2px solid #777';
                    btnCancel.style.borderRadius = '8px';
                    btnCancel.style.padding = '8px 16px';
                }
            },
            preConfirm: (value) => {
                if (!value || value < 2020 || value > 2030) {
                    Swal.showValidationMessage('Por favor ingresa un año valido entre 2020 y 2030');
                    return false;
                }
                return value;
            }
        });
        
        if (!anio) return;
        fecha_inicio = `${anio}-01-01T00:00:00`;
        fecha_fin = `${anio}-12-31T23:59:59`;
    }

    if (!fecha_inicio || !fecha_fin) {
        return;
    }

    alertaNinja('info', 'Generando informe', 'Por favor espera mientras se crea el PDF...');

    try {
        const res = await fetch('/descargar_informes_rango', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                tipo: tipo,
                fecha_inicio: fecha_inicio,
                fecha_fin: fecha_fin 
            })
        });
        
        if (!res.ok) {
            const errorText = await res.text();
            console.error("❌ Error del servidor:", errorText);
            throw new Error(`Error del servidor: ${res.status}`);
        }
        
        // Verificar si la respuesta es un PDF
        const contentType = res.headers.get('content-type');
        if (contentType && contentType.includes('application/pdf')) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `informe_${tipo}_${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            alertaNinja('success', 'Exito', `Informe ${tipo} descargado correctamente.`);
        } else {
            // Si no es PDF, puede ser un error en JSON
            const errorData = await res.json();
            console.error("❌ Error del servidor:", errorData);
            alertaNinja('error', 'Error', errorData.msg || 'No se pudo generar el informe.');
        }
        
    } catch (error) {
        console.error("❌ Error al descargar:", error);
        alertaNinja('error', 'Error', 'No se pudo generar o descargar el informe.');
    }
};
// Reemplazar la funcion de generar informe diario
$('#genDayBtn').click(() => {
    Swal.fire({
        title: '¿Generar informe diario consolidado?',
        text: 'Se creara un unico informe con todos los pedidos de hoy.',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Si, generar',
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
                    alertaNinja('success', 'Exito', data.msg);
                    // Actualizar la vista con el nuevo informe
                    await actualizarVistaDespuesDeGenerar();
                    // Descargar automaticamente el informe recien creado
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
                        alertaNinja('warning', 'Atencion', data.msg);
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

// 🔍 Buscar automaticamente al seleccionar fecha
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
        alertaNinja('error', 'Error', 'No se pudo realizar la busqueda por fecha.');
    }
}
// 📋 Cargar ultimo informe automaticamente al iniciar la pagina
document.addEventListener('DOMContentLoaded', function() {
    console.log("🔄 Cargando ultimo informe...");
    cargarUltimoInforme();
});

// 🔄 Funcion para cargar el ultimo informe
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
                        <p><span>Fecha de creacion:</span> ${new Date(inf.fecha_creacion).toLocaleString('es-CO')}</p>
                        <p><span>Tipo:</span> ${inf.tipo === 'diario_consolidado' ? 'Informe Diario Consolidado' : 'Individual'}</p>
                        <button class="download-button" onclick="descargarInforme(${inf.id_informe})">
                            Descargar PDF
                        </button>
                    </div>
                </div>
            `;
        } else {
            resultBox.innerHTML = '<p>No hay informes generados aun.</p>';
        }
    } catch (error) {
        console.error("❌ Error al cargar ultimo informe:", error);
        document.getElementById('resultEmpleado').innerHTML = '<p>Error al cargar informes.</p>';
    }
}

// 🔄 Funcion para actualizar la vista despues de generar un nuevo informe
async function actualizarVistaDespuesDeGenerar() {
    await cargarUltimoInforme();
}


// 📥 Botones de descarga
$('#downloadSemBtn').click(() => descargarPorRango('semana'));
$('#downloadMesBtn').click(() => descargarPorRango('mes'));
$('#downloadAnioBtn').click(() => descargarPorRango('anio'));

// Funcion de debug para probar la busqueda
window.probarBusqueda = async function(id) {
    console.log("🧪 Probando busqueda con ID:", id);
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