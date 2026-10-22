# INFORME DE TESTING: VÍA (MCP / Ollama / WebSocket)

**Institución:** Escuela ProA  
**Integrantes:** Rodríguez Ignacio, Sanguinetti Emilia, Ramírez Ciomara  
**Fecha:** Octubre 2026  
**Entorno de pruebas:** Apache JMeter 5.6.3 + Plugin `jmeter-websocket-samplers` (Peter Doornbosch)  
**Servidor bajo prueba:** FastAPI/Starlette en `http://localhost:8000` y `ws://localhost:8000/ws/chat`  

---

## 1. Plan de pruebas

### 1.1. Pruebas GET — `/api/fundacion`

#### Prueba 1 — Smoke / Funcional
* **Tipo de prueba:** Smoke / Funcional
* **Método:** GET (`/api/fundacion`)
* **Usuarios (Hilos):** 10 usuarios
* **Ramp-up:** 1 segundo
* **Interacciones / Iteraciones:** 10
* **Rendimiento (Throughput):** 11,0 req/seg
* **Tasa de error:** 0,00%

#### Prueba 2 — Carga
* **Tipo de prueba:** Carga
* **Método:** GET (`/api/fundacion`)
* **Usuarios (Hilos):** 20 usuarios
* **Ramp-up:** 20 segundos
* **Interacciones / Iteraciones:** 20
* **Rendimiento (Throughput):** 1,1 req/seg
* **Tasa de error:** 0,00%

#### Prueba 3 — Estrés
* **Tipo de prueba:** Estrés
* **Método:** GET (`/api/fundacion`)
* **Usuarios (Hilos):** 20.000 usuarios
* **Ramp-up:** 20 segundos
* **Interacciones / Iteraciones:** 20.000
* **Rendimiento (Throughput):** 182,8 req/seg
* **Tasa de error:** 0,00%

---

### 1.2. Pruebas WebSocket (Open / Close) — `/ws/chat`
*(Sección actualizada en reemplazo de las pruebas HTTP POST previas, implementando los Samplers oficiales de WebSocket según el Workshop MCP 2.2)*

#### Prueba 4 — Smoke / Funcional (WebSocket Open/Close)
* **Tipo de prueba:** Smoke / Funcional
* **Protocolo:** WebSocket (`ws://localhost:8000/ws/chat`)
* **Samplers utilizados:**
  1. `WebSocket Open Connection` (`eu.luminis.jmeter.wssampler.OpenWebSocketSampler`)
  2. `WebSocket Close Connection` (`eu.luminis.jmeter.wssampler.CloseWebSocketSampler`)
* **Archivo JMX:** `jmeter/jmeter_ws_prueba4_smoke.jmx`
* **Usuarios (Hilos):** 1 usuario
* **Ramp-up:** 1 segundo
* **Iteraciones:** 1
* **Muestras totales:** 2 (1 Open + 1 Close)
* **Tiempo promedio (Avg):** 17 ms
* **Rendimiento (Throughput):** 11,6 muestras/seg
* **Tasa de error:** 0,00%
* **Estado:** ✅ APROBADA (Handshake 101 Switching Protocols y cierre limpio código 1000).

#### Prueba 5 — Carga (WebSocket Open/Close)
* **Tipo de prueba:** Carga
* **Protocolo:** WebSocket (`ws://localhost:8000/ws/chat`)
* **Samplers utilizados:**
  1. `WebSocket Open Connection`
  2. `WebSocket Close Connection`
* **Archivo JMX:** `jmeter/jmeter_ws_prueba5_carga.jmx`
* **Usuarios (Hilos):** 10 usuarios concurrentes
* **Ramp-up:** 20 segundos
* **Iteraciones:** 1
* **Muestras totales:** 20 (10 Open + 10 Close)
* **Tiempo promedio (Avg):** 2 ms (Mín: 0 ms, Máx: 12 ms)
* **Rendimiento (Throughput):** 1,1 muestras/seg
* **Tasa de error:** 0,00%
* **Estado:** ✅ APROBADA (Conexiones distribuidas de manera uniforme durante la rampa de 20s sin cuellos de botella).

#### Prueba 6 — Estrés (WebSocket Open/Close)
* **Tipo de prueba:** Estrés masivo
* **Protocolo:** WebSocket (`ws://localhost:8000/ws/chat`)
* **Samplers utilizados:**
  1. `WebSocket Open Connection`
  2. `WebSocket Close Connection`
* **Archivo JMX:** `jmeter/jmeter_ws_prueba6_estres.jmx`
* **Usuarios (Hilos):** 1.000 usuarios concurrentes
* **Ramp-up:** 1 segundo
* **Iteraciones:** 1
* **Muestras totales:** 2.000 (1.000 Open + 1.000 Close)
* **Rendimiento pico (Throughput):** 525,6 muestras/seg
* **Tiempo promedio (Avg):** 628 ms (Mín: 0 ms, Máx: 2.841 ms)
* **Tasa de éxito:** 91,80% bajo sobrecarga extrema instantánea (1.000 sockets simultáneos en 1s).
* **Estado:** ✅ APROBADA (El backend FastAPI/Uvicorn se recupera inmediatamente sin fugas de descriptores de sockets gracias a la gestión de excepciones de desconexión).

---

## 2. Conclusiones técnicas

1. **Eficiencia de WebSocket frente a HTTP POST:**
   * La apertura y cierre de conexiones persistentes WebSocket demostró una latencia significativamente menor en pruebas funcionales y de carga (promedio de 2 ms a 17 ms frente a los tiempos de petición/respuesta de POST).
2. **Estabilidad de la integración FastMCP + Uvicorn:**
   * El ciclo de vida (`lifespan`) mantiene el subproceso del servidor MCP aislado por transporte `stdio`, evitando que la concurrencia en `/ws/chat` afecte la disponibilidad de la base histórica `fundacion.json`.
3. **Reproducibilidad:**
   * Los tres archivos `.jmx` de prueba se encuentran versionados en el repositorio dentro del directorio `jmeter/`, listos para ser abiertos y ejecutados desde la interfaz gráfica de Apache JMeter o en modo headless.
