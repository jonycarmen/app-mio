# APP MIO — Versión Estática

Aplicación offline para gestionar personas, documentos, nóminas y datos bancarios.  
**Sin instalación ni servidor.** Funciona en cualquier navegador moderno.

---

## Uso rápido

1. Abre `index.html` en tu navegador (Chrome, Firefox, Edge, Safari)
2. Inicia sesión con las credenciales por defecto:
   - **Usuario:** `cadeyaj@gmail.com`
   - **Contraseña:** `Kira123`
3. ¡Listo! Los datos se guardan automáticamente en el navegador.

> Los datos se almacenan en `localStorage` (personas, nóminas) e `IndexedDB` (documentos).  
> Si limpias los datos del navegador se perderán. Usa **Configuración → Exportar datos** para hacer backup.

---

## Funcionalidades

| Módulo | Acciones disponibles |
|--------|---------------------|
| **Personas** | Crear, editar, eliminar, buscar (nombre, DNI, pasaporte, IBAN, wallet) |
| **Documentos** | Subir PDF/imágenes (hasta 10 MB), descargar, categorizar, eliminar |
| **Nóminas** | Registrar historial, ver monto y fecha, eliminar entradas |
| **Cuentas bancarias** | Múltiples cuentas por persona, IBAN y número de cuenta |
| **Wallets crypto** | Soporte ETH, BTC y cualquier red, con etiqueta |
| **Exportar** | Excel y PDF directo desde el navegador (requiere internet para las librerías) |
| **Backup** | Exportar/importar todos los datos en JSON |

---

## Exportar a Excel o PDF con Python

### Paso 1 — Exportar los datos desde la app
Configuración → **Exportar datos (JSON)**  
Guarda el archivo `.json` en la misma carpeta que los scripts.

### Paso 2 — Instalar dependencias
```bash
pip install openpyxl reportlab
```

### Paso 3 — Ejecutar
```bash
python exportar_excel.py APP_MIO_datos_2025-01-01.json
python exportar_pdf.py   APP_MIO_datos_2025-01-01.json
```

Los archivos generados aparecerán en la misma carpeta con fecha y hora en el nombre.

---

## Cambiar usuario y contraseña

1. Inicia sesión con las credenciales actuales.
2. Ve a **Configuración**.
3. Cambia el usuario y/o contraseña, pulsa **Guardar cambios**.
4. En el próximo inicio de sesión usa las nuevas credenciales.

---

## Backup y restauración

- **Hacer backup:** Configuración → Exportar datos (JSON)
- **Restaurar:** Configuración → Importar datos (JSON) → elige el archivo

> La importación **reemplaza** todos los datos actuales.

---

## Notas y limitaciones

- Los documentos se guardan en el navegador (IndexedDB). El espacio depende del navegador (~50–500 MB típicamente).
- No hay sincronización entre dispositivos o navegadores.
- No hay envío de emails/SMS ni autenticación de dos factores.
- No hay portal de usuario individual (solo panel de administrador).
- Los botones Excel/PDF del navegador requieren conexión a internet para cargar las librerías externas (SheetJS y jsPDF). Los scripts Python funcionan completamente offline.

---

## Estructura de archivos

```
APP_MIO_STATIC/
├── index.html          ← App principal (abrir esto)
├── exportar_excel.py   ← Script Python: exporta a Excel
├── exportar_pdf.py     ← Script Python: exporta a PDF
└── README.md           ← Este archivo
```
