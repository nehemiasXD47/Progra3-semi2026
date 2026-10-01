// Pantalla "Tarifas": ver la tabla tarifaria y agregar rangos.
import {llamar} from "./api.js";
import {leerContexto} from "./contexto.js";
import {$, dinero, numero, mostrarAviso} from "./util.js";

export async function cargarTarifas() {
  const producto = leerContexto().producto_codigo;
  const cuerpo = $("#tabla-tarifas tbody");
  if (!producto) {
    cuerpo.innerHTML = "";
    $("#t-huecos").innerHTML = `<p class="vacio">Seleccione un producto para ver su tabla tarifaria.</p>`;
    return;
  }

  const r = await llamar("GET", `/api/tarifas?producto_codigo=${producto}`);
  $("#t-huecos").innerHTML = r.huecos.map(h => `<div class="mini warn">
      Sin tarifa para balances de $${dinero(h.desde)} a $${dinero(h.hasta)}:
      el sistema los rechaza hasta configurar el rango.</div>`).join("");
  cuerpo.innerHTML = r.tarifas.map(t => `<tr><td>${t.version}</td>
      <td class="n">${dinero(t.desde)}</td><td class="n">${dinero(t.hasta)}</td>
      <td class="n">${dinero(t.precio_base)}</td><td class="n">${dinero(t.adicional)}</td>
      <td class="n">${numero(t.porcentaje)}</td><td>${t.vigente_desde}</td></tr>`).join("");
}

async function agregarTarifa(evento) {
  evento.preventDefault();
  const producto = leerContexto().producto_codigo;
  if (!producto) return mostrarAviso("Seleccione el producto al que pertenece la tarifa.");

  try {
    const r = await llamar("POST", "/api/tarifas", {
      producto_codigo: producto, desde: $("#t-desde").value, hasta: $("#t-hasta").value,
      precio_base: $("#t-base").value, adicional: $("#t-adic").value,
      porcentaje: $("#t-pct").value, vigente_desde: $("#t-vig").value,
    });
    mostrarAviso(r.mensaje, "ok");
    cargarTarifas();
  } catch (error) {
    mostrarAviso(error.message);
  }
}

export function iniciarTarifas() {
  $("#form-tarifa").addEventListener("submit", agregarTarifa);
}
