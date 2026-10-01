// Funciones de apoyo compartidas por todas las pantallas.

export const $ = selector => document.querySelector(selector);

// Evita que texto con < > & se interprete como HTML
export function esc(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, c =>
    ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
}

// 1234.5 -> "1,234.50"
export function dinero(valor) {
  if (valor == null) return "—";
  return Number(valor).toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

// Números sin forzar 2 decimales (porcentajes, meses, bloques)
export function numero(valor) {
  if (valor == null) return "—";
  return Number(valor).toLocaleString("en-US", {maximumFractionDigits: 6});
}

// Mensaje arriba de la pantalla: tipo = "ok" | "err" | "warn"
let temporizador = null;
export function mostrarAviso(mensaje, tipo = "err") {
  const caja = $("#aviso");
  caja.textContent = mensaje;
  caja.className = "aviso " + tipo;
  caja.hidden = false;
  clearTimeout(temporizador);
  if (tipo === "ok") temporizador = setTimeout(() => (caja.hidden = true), 6000);
}

export function ocultarAviso() {
  $("#aviso").hidden = true;
}

// Ventana de confirmación. Devuelve true si el usuario acepta.
export function confirmar(titulo, html) {
  return new Promise(resolver => {
    const ventana = $("#dlg");
    $("#dlg-t").textContent = titulo;
    $("#dlg-b").innerHTML = html;
    ventana.returnValue = "";
    ventana.onclose = () => resolver(ventana.returnValue === "si");
    ventana.showModal();
  });
}
