// Única función que habla con el servidor Python.

export async function llamar(metodo, ruta, cuerpo) {
  const respuesta = await fetch(ruta, {
    method: metodo,
    headers: {"Content-Type": "application/json"},
    body: cuerpo ? JSON.stringify(cuerpo) : undefined,
  });
  const datos = await respuesta.json().catch(() => ({error: "Respuesta inválida del servidor."}));
  if (!respuesta.ok) {
    const error = new Error(datos.error || "Error");
    error.datos = datos;
    throw error;
  }
  return datos;
}
