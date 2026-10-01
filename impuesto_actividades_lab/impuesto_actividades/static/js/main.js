// Arranque: llena los selectores, conecta las pestañas y reparte el trabajo a cada pantalla.
import {llamar} from "./api.js";
import {leerContexto} from "./contexto.js";
import {$, esc, mostrarAviso, ocultarAviso} from "./util.js";
import {iniciarPeriodos, cargarPeriodos, calcularVistaPrevia} from "./periodos.js";
import {iniciarCobro, cargarRecibos} from "./cobro.js";
import {iniciarTarifas, cargarTarifas} from "./tarifas.js";
import {cargarBitacora} from "./bitacora.js";

// Qué función carga los datos de cada pestaña
const CARGADORES = {
  periodos: cargarPeriodos,
  cobro: cargarRecibos,
  tarifas: cargarTarifas,
  bitacora: cargarBitacora,
};

function pestanaActual() {
  return document.querySelector(".tabs .on").dataset.tab;
}

function mostrarPestana(nombre) {
  document.querySelectorAll(".tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === nombre));
  document.querySelectorAll("main > section").forEach(s => (s.hidden = s.id !== "tab-" + nombre));
  ocultarAviso();
  CARGADORES[nombre]().catch(e => mostrarAviso(e.message));
}

async function llenarSelectores() {
  const d = await llamar("GET", "/api/init");

  $("#usuario").innerHTML = d.usuarios.map(u => `<option value="${esc(u.nombre)}">${esc(u.nombre)} (${u.rol})</option>`).join("");
  $("#cliente").innerHTML = `<option value="">Seleccione un cliente…</option>`
    + d.clientes.map(c => `<option value="${c.id}">${esc(c.codigo)} · ${esc(c.nombre)} [${c.tipo}]</option>`).join("");
  $("#producto").innerHTML = `<option value="">Seleccione comercio o industria…</option>`
    + d.productos.map(p => `<option value="${p.codigo}">${p.codigo} · ${p.actividad}</option>`).join("");

  // Fechas sugeridas
  const anio = new Date().getFullYear();
  $("#desde").value = `${anio + 1}-01-01`;
  $("#hasta").value = `${anio + 2}-01-01`;
  $("#c-desde").value = `${anio - 1}-01-01`;
  $("#c-hasta").value = `${anio}-01-01`;
  $("#t-vig").value = new Date().toISOString().slice(0, 10);
}

function cuandoCambiaClienteOProducto() {
  CARGADORES[pestanaActual()]().catch(e => mostrarAviso(e.message));
  calcularVistaPrevia();   // cambiar el producto descarta la tarifa anterior y recalcula
}

async function arrancar() {
  try {
    await llenarSelectores();
  } catch (error) {
    mostrarAviso(error.message);
  }
  iniciarPeriodos();
  iniciarCobro();
  iniciarTarifas();

  $(".tabs").addEventListener("click", e => e.target.dataset.tab && mostrarPestana(e.target.dataset.tab));
  $("#cliente").addEventListener("change", cuandoCambiaClienteOProducto);
  $("#producto").addEventListener("change", cuandoCambiaClienteOProducto);

  mostrarPestana("periodos");
}

arrancar();
