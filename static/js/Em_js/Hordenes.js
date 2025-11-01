document.addEventListener("DOMContentLoaded", () => {
  const filtros = {
    fecha: document.getElementById('buscarFecha'),
    categoria: document.getElementById('buscarCategoria'),
    producto: document.getElementById('buscarProducto'),
    cantidad: document.getElementById('buscarCantidad'),
    unidad: document.getElementById('buscarUnidad')
  };

  const filas = document.querySelectorAll('.order-row');

  // 🔹 Filtrado instantáneo
  Object.values(filtros).forEach(input => {
    input.addEventListener('input', filtrarTabla);
    input.addEventListener('change', filtrarTabla);
  });

  function filtrarTabla() {
    const fFecha = filtros.fecha.value.toLowerCase();
    const fCat = filtros.categoria.value.toLowerCase();
    const fProd = filtros.producto.value.toLowerCase();
    const fCant = filtros.cantidad.value.trim();
    const fUni = filtros.unidad.value.toLowerCase();

    filas.forEach(fila => {
      const fecha = fila.querySelector('.col-fecha').textContent.toLowerCase();
      const cat = fila.querySelector('.col-categoria').textContent.toLowerCase();
      const prod = fila.querySelector('.col-producto').textContent.toLowerCase();
      const cant = fila.querySelector('.col-cantidad').textContent.trim();
      const uni = fila.querySelector('.col-unidad').textContent.toLowerCase();

      const visible =
        (!fFecha || fecha.includes(fFecha)) &&
        (!fCat || cat.includes(fCat)) &&
        (!fProd || prod.includes(fProd)) &&
        (!fCant || cant === fCant) &&
        (!fUni || uni.includes(fUni));

      fila.style.display = visible ? "grid" : "none";
    });
  }

  // 🔹 Búsqueda avanzada (cuando se presiona Enter)
  const form = document.getElementById("formBuscar");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    form.submit(); // deja que Flask haga la búsqueda avanzada
  });
});
