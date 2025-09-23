function eliminarProducto(id) {
    Swal.fire({
        title: '<span style="font-family: njnaruto; font-size: 2rem;">ESTAS SEGURO</span>',
        html: '<span style="font-family: njnaruto; font-size: 1.2rem;">ESTA ACCION ELIMINARA AL PRODUCTO</span>',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#e60000',
        cancelButtonColor: '#888',
        confirmButtonText: '<span style="font-family: njnaruto;">Si eliminar</span>',
        cancelButtonText: '<span style="font-family: njnaruto;">Cancelar</span>',
        background: '#000',
        color: '#fff',
        customClass: {
            popup: 'swal2-border-radius',
            title: 'swal2-title-custom',
            confirmButton: 'swal2-confirm-custom',
            cancelButton: 'swal2-cancel-custom'
        }
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(`/eliminar_producto/${id}`, {
                method: 'DELETE'
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    Swal.fire({
                        icon: 'success',
                        title: '<span style="font-family: njnaruto;">Producto eliminado</span>',
                        text: 'El registro fue eliminado correctamente',
                        confirmButtonColor: '#e60000',
                        background: '#000',
                        color: '#fff',
                        customClass: {
                            title: 'swal2-title-custom',
                            confirmButton: 'swal2-confirm-custom'
                        }
                    });
                    document.getElementById("buscarProducto").dispatchEvent(new Event("input")); // refresca lista
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: '<span style="font-family: njnaruto;">Error</span>',
                        text: data.msg,
                        confirmButtonColor: '#e60000',
                        background: '#000',
                        color: '#fff',
                        customClass: {
                            title: 'swal2-title-custom',
                            confirmButton: 'swal2-confirm-custom'
                        }
                    });
                }
            });
        }
    });
}
