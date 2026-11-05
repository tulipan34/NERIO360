# NERIO360 · Inmobiliaria

Proyecto web en **Python Flask + JavaScript + PostgreSQL** para uso local en Windows y posterior publicación en AWS. Interfaz responsive en español y precios en pesos colombianos (COP).

## Funcionalidades

- `/`: catálogo público con filtros por texto, ciudad y precio máximo; solo propiedades disponibles.
- `/propiedad/ID`: fotos, características, descripción y mapa con Leaflet/OpenStreetMap. Los mapas requieren internet.
- Encuesta de interés: nombre, correo, teléfono, presupuesto, nivel de interés, mensaje y fecha de visita preferida; incluye casilla de autorización.
- `/admin/login`: acceso privado de administrador.
- `/admin`: agregar/editar inmuebles y fotos, retirar del catálogo, consultar interesados, programar citas y cambiar sus estados.
- `/health`: comprobación básica de disponibilidad del proceso.
- Fotos almacenadas en `static/uploads` (Docker: volumen persistente).

No incluye viviendas reales ni credenciales activas: créalas tú mismo desde el administrador. No se envían correos o mensajes de WhatsApp automáticamente. Las citas se confirman desde el panel; la empresa debe contactar personalmente al cliente.

## OPCIÓN A — Windows: Flask en VS Code + PostgreSQL en Docker Desktop (recomendada para aprender)

**Requisitos:** Python 3.11 o 3.12, Docker Desktop con Docker Compose, VS Code y acceso a internet para instalar paquetes. En PowerShell, situado en esta carpeta:

1. `Copy-Item .env.example .env`
2. Abre `.env` y cambia **DB_PASSWORD**, **DATABASE_URL** (la misma contraseña que `DB_PASSWORD`), **SECRET_KEY**, **ADMIN_EMAIL** y **ADMIN_PASSWORD**. Las contraseñas de ejemplo son inseguras: cámbialas antes de seguir. Evita caracteres especiales de URL en DB_PASSWORD o aplica codificación de URL a la contraseña en DATABASE_URL.
3. `docker compose -f compose.local.yml up -d`
4. `py -3.12 -m venv .venv` (o `py -m venv .venv` si no tienes Python 3.12)
5. `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
6. `.\.venv\Scripts\python.exe -m flask --app app init-db`
7. `.\.venv\Scripts\python.exe -m flask --app app run --debug`
8. Abre **http://127.0.0.1:5000/** y **http://127.0.0.1:5000/admin/login**. Entra con `ADMIN_EMAIL` y `ADMIN_PASSWORD` del `.env`.

Para detener Flask presiona Ctrl+C. Para detener la base de datos: `docker compose -f compose.local.yml down` (no agregues `-v`, ya que elimina los datos del volumen).

Si usas PostgreSQL instalado en Windows en lugar de Docker, crea manualmente base de datos `nerio360` y usuario `nerio` con su contraseña; configura `DATABASE_URL` y omite el paso 3.

## OPCIÓN B — Windows: aplicación y PostgreSQL en Docker Desktop

1. Copia `.env.example` a `.env` y cambia credenciales. La configuración del servicio web toma DB_PASSWORD y crea la URL interna automáticamente.
2. `docker compose up -d --build`
3. `docker compose exec web flask --app app init-db`
4. Abre **http://127.0.0.1:8000/** y **http://127.0.0.1:8000/admin/login**.
5. Comprueba con `docker compose ps` y `docker compose logs -f web`.

IMPORTANTE: No ejecutes las opciones A y B simultáneamente: son configuraciones alternativas del mismo proyecto.

## Publicación posterior en AWS

En una instancia EC2 Linux con Docker Engine y Docker Compose, sube esta carpeta, configura `.env` con contraseñas seguras y ejecuta los comandos de la opción B. La configuración de Docker vincula el puerto 8000 solo a localhost; añade un proxy inverso HTTPS (Nginx/Caddy o ALB) para exponer 443. En el security group, permite SSH 22 **solo desde tu IP**, HTTPS 443 y HTTP 80 si lo necesitas para el certificado. **No expongas 5432 ni 8000 públicamente.** Una vez que HTTPS funcione, establece `COOKIE_SECURE=1` en `.env` y reinicia los contenedores. Cambia `FLASK_DEBUG=0`.

Para producción seria, considera RDS PostgreSQL privado, S3 para fotografías, copias de seguridad, rate limiting, monitoreo, protección de datos y avisos de privacidad. El código no está todavía desplegado ni validado en un servidor AWS real.

## Notas y limitaciones

- La URL del mapa muestra las coordenadas facilitadas por administración; publica solo ubicaciones cuya difusión esté autorizada.
- Retirar una propiedad la marca como `vendida` sin borrar interesados y citas anteriores; puedes editar el estado después.
- La protección incluye hash de contraseñas, sesión HTTPOnly, token CSRF para formularios, comprobación de extensión/contenido de fotos y tamaño máximo de solicitud de 8 MB. Antes de recibir tráfico público real, agrega controles antispam, limitación de intentos, correo de confirmación, política de tratamiento de datos e infraestructura segura.
- Si cambias ADMIN_PASSWORD después de iniciar la base, el comando `init-db` **no cambia** la contraseña de un administrador ya existente.
- Configura la zona horaria del servidor para gestionar correctamente las citas. Las citas se guardan como fecha/hora ingresada por el administrador sin zona horaria.
