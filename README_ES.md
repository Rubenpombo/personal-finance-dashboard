# Sistema de Gestión Patrimonial (Finanzas Personales)

Un dashboard financiero **privado, local y moderno** diseñado para tener control total sobre tu patrimonio, ahorro e inversiones. Tus datos son tuyos y viven exclusivamente en tu ordenador.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)

---

## 🚀 Guía de Inicio

### 1. Instalación
```bash
# 1. Clona el repositorio
git clone https://github.com/tu-usuario/finanzas-personales.git
cd finanzas-personales

# 2. Crea un entorno virtual e instala dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Prepara tus datos (Ver sección Estructura CSV abajo)
# Crea la carpeta data/ y tus archivos CSV base.

# 4. Arranca la aplicación
./run.sh
```
Abre tu navegador en `http://localhost:8501`.

---

## 📐 Estructura de Archivos CSV (Configuración)

Al empezar, crea estos archivos en la carpeta `/data`. Asegúrate de respetar los **encabezados exactos**.

### 1. Configuración de Patrimonio
**`data/activos.csv`** (Tu catálogo de productos)
| Columna | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `id` | Identificador único (Clave para todo). | `SP500_ETF` |
| `nombre` | Nombre legible. | `Vanguard S&P 500 UCITS ETF` |
| `isin` | ISIN (fondos) o 'CASH' (dinero). | `IE00B3XXRP09` |
| `tipo` | `Efectivo`, `Renta Variable`, `Renta Fija`. | `Renta Variable` |
| `fuente` | `quefondos` (automático) o `manual`. | `quefondos` |

**`data/saldo_inicial.csv`** (Tu punto de partida)
| Columna | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `id_activo` | Debe coincidir con el `id` de activos.csv. | `BBVA_CASH` |
| `participaciones` | Cantidad de títulos o dinero total. | `2500.50` |
| `precio_medio_compra` | Coste medio histórico (pon `1` para efectivo). | `1` |

**`data/aportaciones.csv`** (Tus movimientos de inversión)
| Columna | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `fecha` | Fecha del movimiento (YYYY-MM-DD). | `2026-02-15` |
| `tipo` | `COMPRA`, `VENTA` o `AJUSTE_VALOR`. | `COMPRA` |
| `id_activo` | ID del activo afectado. | `MSCI_WORLD` |
| `cantidad_dinero` | Dinero total invertido/recibido. | `1000` |
| `titulos` | Número de participaciones. | `10.5` |
| `precio_titulo` | Precio por participación. | `95.23` |

---

### 2. Configuración de Ahorro (Flujo)
**`data/ingresos.csv`**
| Columna | Ejemplo |
| :--- | :--- |
| `fecha` | `2026-01-30` |
| `cantidad` | `2100.50` |
| `concepto` | `Nómina Enero` |
| `categoria` | `Salario` |

**`data/gastos_variables.csv`** (Gastos del día a día)
| Columna | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `fecha` | Fecha del gasto. | `2026-02-05` |
| `cantidad` | Importe. | `55.20` |
| `categoria` | Agrupador para gráficos. | `Supermercado` |
| `concepto` | Detalle. | `Mercadona` |
| `extraordinario` | `NO` (habitual) o `SÍ` (imprevisto/anual). | `NO` |

**`data/gastos_recurrentes.csv`** (Fijos mensuales automáticos)
| Columna | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `dia` | Día del mes que se cobra. | `5` |
| `cantidad` | Importe fijo. | `12.99` |
| `categoria` | Categoría. | `Suscripciones` |
| `concepto` | Nombre. | `Netflix` |

---

## 📂 Archivos Automáticos (No tocar)
El sistema generará o sobrescribirá estos archivos por su cuenta:
*   `data/cartera.csv`: El resultado calculado de tu patrimonio actual.
*   `data/precios_historicos.csv`: Historial de precios descargados de internet.

---

## ✅ Características Clave
*   **Privacidad Total:** Funciona 100% offline. Ningún dato sale de tu máquina.
*   **Seguimiento Automático:** Actualización de precios de fondos vía internet (opcional).
*   **Análisis de Salud:** Cálculo de "Runway" (meses de libertad) y Tasa de Ahorro basado en gastos reales.
*   **Escenarios:** Proyecciones a futuro (Pesimista/Realista/Optimista) para ayudarte a planificar.

---

## 🧠 Herramientas Inteligentes

Este programa incluye varias funcionalidades avanzadas para automatizar y mejorar la gestión financiera:

*   **Motor de Reconstrucción de Cartera:** Olvida mantener la cartera a mano. El sistema reconstruye tu posición actual procesando cronológicamente cada compra, venta y ajuste desde el saldo inicial.
*   **Actualizador de Precios Automático:** Scraper integrado que consulta fuentes financieras (QueFondos) para obtener el valor liquidativo de tus fondos mediante el ISIN.
*   **Gestor de Gastos Recurrentes:** Calcula automáticamente tus gastos fijos (Netflix, alquiler, seguros) proyectándolos en el tiempo para que el flujo de caja sea siempre realista.
*   **Prorrateo Inteligente de Gastos Extraordinarios:** No dejes que un seguro anual arruine tus gráficos de un mes. El sistema detecta gastos extraordinarios y los prorratea para mostrarte tu capacidad de ahorro real.
*   **Proyecciones Multiescenario:** Algoritmo de previsión que combina tu flujo de caja neto con el rendimiento esperado de tus inversiones para proyectar tu patrimonio a 6 meses y a cierre de año.
*   **Visualización Avanzada con ECharts:** Gráficos dinámicos tipo *Sunburst* para ver la jerarquía de tu patrimonio y gráficos de área para distinguir el capital invertido de la plusvalía real.
