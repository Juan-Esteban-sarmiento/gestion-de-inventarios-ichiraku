// 🥷 Alerta Ninja reutilizable
function alertaNinja(icon, title, text) {
  Swal.fire({
    icon: icon,
    title: `<span style="font-family:njnaruto;">${title}</span>`,
    text: text || '',
    background: '#000',
    color: '#fff',
    confirmButtonColor: '#e63900',
    confirmButtonText: '<span style="font-family:njnaruto;">Aceptar</span>',
    customClass: {
      popup: 'swal2-border-radius',
      title: 'swal2-title-custom',
      confirmButton: 'swal2-confirm-custom'
    }
  });
}

// ⚡ Buscar informes por ID o fecha
document.getElementById('searchForm').addEventListener('submit', async function (e) {
  e.preventDefault();

  const id_informe = document.getElementById('id_informe').value.trim();
  const fecha = document.getElementById('date').value.trim();

  if (!id_informe && !fecha) {
    alertaNinja('warning', 'Campos vacíos', 'Debes ingresar un ID o una fecha.');
    return;
  }

  try {
    const response = await fetch('/buscar_informe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_informe, fecha })
    });

    const data = await response.json();
    const resultBox = document.getElementById('resultEmpleado');

    if (data.success && data.informes && data.informes.length > 0) {
      resultBox.innerHTML = data.informes.map(inf => `
        <div class="producto-card">
          <div style="display:flex; align-items:center; justify-content:space-between; padding:10px;">
            <div style="text-align:left;">
              <p><strong>ID Informe:</strong> ${inf.id_informe}</p>
              <p><strong>ID Pedido:</strong> ${inf.id_inf_pedido}</p>
              <p><strong>Fecha:</strong> ${new Date(inf.fecha_creacion).toLocaleString()}</p>
            </div>
            <button class="download-button" onclick="descargarInforme(${inf.id_informe})">
              Descargar PDF
            </button>
          </div>
        </div>
      `).join("");
    } else {
      resultBox.innerHTML = `<p>No se encontraron informes</p>`;
      alertaNinja('info', 'Sin resultados', data.msg || 'No hay informes con esos datos.');
    }

  } catch (err) {
    console.error("❌ Error en búsqueda:", err);
    alertaNinja('error', 'Error del servidor', 'No se pudo realizar la búsqueda.');
  }
});

// 🧾 Descargar informe
function descargarInforme(id) {
  alertaNinja('info', 'Descargando informe', 'Tu archivo PDF se está generando...');
  setTimeout(() => {
    window.open(`/descargar_informe/${id}`, '_blank');
  }, 1000);
}

// 📊 Generar informe semanal
document.getElementById('genSemBtn').addEventListener('click', async () => {
  try {
    const res = await fetch('/generar_informe_semanal', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      alertaNinja('success', 'Informe semanal', data.msg);
    } else {
      alertaNinja('warning', 'Atención', data.msg);
    }
  } catch (err) {
    console.error("❌ Error semanal:", err);
    alertaNinja('error', 'Error del servidor', 'No se pudo generar el informe semanal.');
  }
});

// 📆 Generar informe mensual
document.getElementById('genMesBtn').addEventListener('click', async () => {
  try {
    const res = await fetch('/generar_informe_mensual', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      alertaNinja('success', 'Informe mensual', data.msg);
    } else {
      alertaNinja('warning', 'Atención', data.msg);
    }
  } catch (err) {
    console.error("❌ Error mensual:", err);
    alertaNinja('error', 'Error del servidor', 'No se pudo generar el informe mensual.');
  }
});

// 🪄 Descargar el primer resultado de búsqueda directamente
document.getElementById('downloadBtn').addEventListener('click', () => {
  const match = document.getElementById('resultEmpleado').innerHTML.match(/descargarInforme\((\d+)\)/);
  if (match) {
    descargarInforme(match[1]);
  } else {
    alertaNinja('info', 'Sin selección', 'Primero busca y selecciona un informe.');
  }
});
