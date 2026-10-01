// Lee lo que el usuario eligió arriba: usuario, cliente y producto.
import {$} from "./util.js";

export function leerContexto() {
  return {
    usuario: $("#usuario").value,
    cliente_id: Number($("#cliente").value) || null,
    producto_codigo: Number($("#producto").value) || null,
  };
}
