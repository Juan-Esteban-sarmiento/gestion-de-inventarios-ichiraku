document.getElementById('registerProductForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData();
    formData.append("nombre", document.getElementById('nombreProducto').value);
    formData.append("categoria", document.getElementById('categoriaProducto').value);
    formData.append("unidad", document.getElementById('unidadProducto').value);
    formData.append("serial", document.getElementById('serialProducto').value);

    const fotoFile = document.getElementById('fotoProducto').files[0];
    if (fotoFile) {
        formData.append("foto", fotoFile);
    }

    const response = await fetch('/registrar_producto', {
        method: 'POST',
        body: formData
    });

    const data = await response.json();
    document.getElementById('registerMsg').innerText = data.msg;

    if (data.success) {
        document.getElementById('registerProductForm').reset();
        document.getElementById('previewFotoProducto').style.display = "none";
        setTimeout(() => window.location.reload(), 1000);
    }
});

// Vista previa de la foto antes de registrar

document.getElementById('fotoProducto').addEventListener('change', function() {
    const file = this.files[0];
    const preview = document.getElementById('previewFotoProducto');

    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = "block";
        };
        reader.readAsDataURL(file);
    } else {
        preview.src = "";
        preview.style.display = "none";
    }
});
