/* Ad_Recetarios.js */

document.addEventListener('DOMContentLoaded', () => {
    const ingredientsList = document.getElementById('ingredientsList');
    const btnAddIngredient = document.getElementById('btnAddIngredient');
    const registerRecipeForm = document.getElementById('registerRecipeForm');
    const fotoReceta = document.getElementById('fotoReceta');
    const previewFotoReceta = document.getElementById('previewFotoReceta');

    let availableProducts = [];

    // Fetch available products for ingredient selection
    const loadProducts = async () => {
        try {
            const response = await fetch('/get_productos_receta');
            const data = await response.json();
            if (data.success) {
                availableProducts = data.productos;
                // Add initial empty row
                addIngredientRow();
            }
        } catch (error) {
            console.error("Error loading products:", error);
        }
    };

    const UNIT_GROUPS = {
        'kg': 'mass', 'g': 'mass', 'lb': 'mass', 'oz': 'mass',
        'lt': 'volume', 'ml': 'volume', 'cda': 'volume', 'cdta': 'volume',
        'und': 'count'
    };

    const UNIT_OPTIONS = {
        'mass': [
            { v: 'kg', t: 'Kilogramo' }, { v: 'g', t: 'Gramo' },
            { v: 'lb', t: 'Libra' }, { v: 'oz', t: 'Onza' }, { v: 'und', t: 'Unidad' }
        ],
        'volume': [
            { v: 'lt', t: 'Litro' }, { v: 'ml', t: 'Mililitro' },
            { v: 'cda', t: 'Cucharada' }, { v: 'cdta', t: 'Cucharadita' }, { v: 'und', t: 'Unidad' }
        ],
        'count': [
            { v: 'und', t: 'Unidad' }
        ],
        'all': [
            { v: 'und', t: 'Unidad' }, { v: 'kg', t: 'Kilogramo' }, { v: 'g', t: 'Gramo' },
            { v: 'lt', t: 'Litro' }, { v: 'ml', t: 'Mililitro' }, { v: 'lb', t: 'Libra' },
            { v: 'oz', t: 'Onza' }, { v: 'cda', t: 'Cucharada' }, { v: 'cdta', t: 'Cucharadita' }
        ]
    };

    const addIngredientRow = () => {
        const row = document.createElement('div');
        row.className = 'ingredient-row';

        let productOptions = '<option value="">Seleccione ingrediente</option>';
        availableProducts.forEach(p => {
            productOptions += `<option value="${p.id_producto}" data-unit="${p.unidad}">${p.nombre}</option>`;
        });

        row.innerHTML = `
            <select class="product-select" required>
                ${productOptions}
            </select>
            <input type="number" class="qty-input" placeholder="Cant" min="0" step="0.01" required>
            <select class="unit-select" required disabled>
                <option value="">--</option>
            </select>
            <button type="button" class="btn-remove">&times;</button>
        `;

        const productSelect = row.querySelector('.product-select');
        const unitSelect = row.querySelector('.unit-select');

        productSelect.addEventListener('change', (e) => {
            const selectedOption = e.target.options[e.target.selectedIndex];
            const defaultUnit = selectedOption.getAttribute('data-unit')?.toLowerCase();

            if (!defaultUnit) {
                unitSelect.innerHTML = '<option value="">--</option>';
                unitSelect.disabled = true;
                return;
            }

            const group = UNIT_GROUPS[defaultUnit] || 'all';
            const options = UNIT_OPTIONS[group];

            unitSelect.innerHTML = options.map(opt => `<option value="${opt.v}">${opt.t}</option>`).join('');
            unitSelect.disabled = false;

            // Auto-select match
            Array.from(unitSelect.options).forEach(opt => {
                if (opt.value === defaultUnit) unitSelect.value = opt.value;
            });
        });

        row.querySelector('.btn-remove').addEventListener('click', () => {
            if (ingredientsList.children.length > 1) {
                row.remove();
            } else {
                alertaNinja("Debe haber al menos un ingrediente.", "error");
            }
        });

        ingredientsList.appendChild(row);
    };

    btnAddIngredient.addEventListener('click', addIngredientRow);

    // Photo preview
    fotoReceta.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                previewFotoReceta.src = event.target.result;
                previewFotoReceta.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    });

    registerRecipeForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const nombre = document.getElementById('nombreReceta').value.trim();
        const descripcion = document.getElementById('descripcionReceta').value.trim();
        const foto = fotoReceta.files[0];

        if (!nombre) {
            alertaNinja("El nombre de la receta es obligatorio.", "error");
            return;
        }

        const ingredientRows = document.querySelectorAll('.ingredient-row');
        const ingredientes = [];
        let valid = true;

        ingredientRows.forEach(row => {
            const id_producto = row.querySelector('.product-select').value;
            const cantidad = row.querySelector('.qty-input').value;
            const unidad = row.querySelector('.unit-select').value;

            if (!id_producto || !cantidad || !unidad) {
                valid = false;
            } else {
                ingredientes.push({ id_producto, cantidad, unidad });
            }
        });

        if (!valid || ingredientes.length === 0) {
            alertaNinja("Por favor complete todos los campos de ingredientes.", "error");
            return;
        }

        const formData = new FormData();
        formData.append('nombre', nombre);
        formData.append('descripcion', descripcion);
        if (foto) formData.append('foto', foto);
        formData.append('ingredientes', JSON.stringify(ingredientes));

        try {
            Swal.fire({
                title: 'Guardando receta...',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); }
            });

            const response = await fetch('/registrar_receta', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            Swal.close();

            if (data.success) {
                alertaNinja(data.msg, "success");
                setTimeout(() => window.location.reload(), 1500);
            } else {
                alertaNinja(data.msg, "error");
            }
        } catch (error) {
            Swal.close();
            console.error("Error submitting recipe:", error);
            alertaNinja("Error en la conexión con el servidor.", "error");
        }
    });

    loadProducts();
});
