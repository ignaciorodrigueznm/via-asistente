# Spec 06 — Autenticación, Perfil de Usuario y Personalización en MongoDB

## Objetivo
Incorporar en MongoDB un sistema completo y persistente de usuarios para VÍA que incluya:
1. **Registro e Inicio de sesión**: Creación de cuentas con validación de credenciales, hashing seguro con `bcrypt` y generación/verificación de tokens JWT.
2. **Perfil de Usuario**: Consulta y actualización de datos personales (nombre de usuario, email, foto de perfil en Base64 o URL).
3. **Personalización del Asistente ("Personalizar AI")**: Configuración por usuario del tono (cercano, formal, académico), nombre preferido para dirigirse a él, nivel de detalle de respuestas y directivas personalizadas que se inyectan en el prompt del sistema.
4. **Historial de Conversaciones Pasadas**: Persistencia de sesiones de chat en MongoDB (`conversaciones`) asociadas al usuario, permitiendo listar chats anteriores, consultar mensajes históricos y retomar conversaciones.

## Colecciones y Esquemas en MongoDB

### 1. Colección `usuarios`
```json
{
  "_id": ObjectId,
  "username": "nacho_historian",
  "email": "nacho@example.com",
  "password_hash": "$2b$12$...",
  "nombre": "Ignacio Rodríguez",
  "foto_perfil": "data:image/png;base64,... o URL",
  "rol": "usuario", // "usuario" | "admin"
  "preferencias_ai": {
    "tono": "cercano", // "cercano" | "formal" | "academico"
    "nombre_asistente": "VÍA",
    "nombre_usuario_preferido": "Nacho",
    "directivas_extra": "Priorizar fechas exactas y citar siempre el historiador",
    "modelo_preferido": "llama3.2"
  },
  "creado": ISODate,
  "actualizado": ISODate
}
```
**Índices requeridos:**
- `username`: Único (`unique=True`)
- `email`: Único (`unique=True`)

### 2. Colección `conversaciones`
```json
{
  "_id": ObjectId,
  "id": "conv_a1b2c3d4",
  "user_id": ObjectId,
  "titulo": "Debate sobre el origen de 1900",
  "libro_slug": "fundacion-las-varillas",
  "mensajes": [
    {
      "rol": "user",
      "contenido": "¿Qué dice la teoría de 1900?",
      "fecha": ISODate
    },
    {
      "rol": "assistant",
      "contenido": "La postura de 1900...",
      "fuentes": [{"libro": "fundacion-las-varillas", "fragmento_id": "teoria_1900_ferrocarril"}],
      "fecha": ISODate
    }
  ],
  "creado": ISODate,
  "actualizado": ISODate
}
```
**Índices requeridos:**
- `id`: Único (`unique=True`)
- `user_id + actualizado`: Compuesto (`[("user_id", 1), ("actualizado", -1)]`)

---

## Contrato de Endpoints a Implementar

### Autenticación (`/api/auth/*`)
- `POST /api/auth/register`:
  - Entrada: `{username, email, password, nombre?}`
  - Validación con Pydantic: formato de email, username alfanumérico $\ge 3$ caracteres, contraseña $\ge 6$ caracteres.
  - Salida: `{token, usuario: {id, username, email, nombre, foto_perfil, preferencias_ai}}`
- `POST /api/auth/login`:
  - Entrada: `{identificador, password}` (identificador puede ser username o email).
  - Salida: `{token, usuario: {...}}`
- `GET /api/auth/me`:
  - Header: `Authorization: Bearer <token>`
  - Salida: Perfil completo del usuario actual y sus preferencias de AI.

### Perfil y Personalización (`/api/usuario/*`)
- `PUT /api/usuario/perfil`:
  - Header: `Authorization: Bearer <token>`
  - Entrada: `{nombre?, foto_perfil?}`
  - Salida: Perfil actualizado.
- `PUT /api/usuario/preferencias-ai`:
  - Header: `Authorization: Bearer <token>`
  - Entrada: `{tono?, nombre_usuario_preferido?, directivas_extra?, modelo_preferido?}`
  - Salida: Preferencias de AI actualizadas.

### Conversaciones Pasadas (`/api/conversaciones/*`)
- `GET /api/conversaciones`:
  - Header: `Authorization: Bearer <token>`
  - Devuelve lista de conversaciones del usuario ordenadas por última actualización: `[{id, titulo, libro_slug, actualizado, total_mensajes}]`.
- `GET /api/conversaciones/{id}`:
  - Header: `Authorization: Bearer <token>`
  - Devuelve el historial completo de mensajes de la conversación.
- `POST /api/conversaciones`:
  - Header: `Authorization: Bearer <token>`
  - Crea o guarda mensajes en una conversación.
- `DELETE /api/conversaciones/{id}`:
  - Header: `Authorization: Bearer <token>`
  - Elimina una conversación del usuario.

---

## Plan de Pruebas Unitarias
1. `tests/test_auth.py`:
   - Registro de usuario con hash seguro (verificar que la contraseña nunca se guarda en texto plano).
   - Rechazo de username o email duplicados (409 Conflict).
   - Login correcto devuelve JWT firmado válido; login con contraseña errónea devuelve 401.
   - Endpoint `/api/auth/me` con y sin token.
   - Actualización de foto de perfil y nombre.
   - Actualización y persistencia de "Personalizar AI".
2. `tests/test_conversaciones.py`:
   - Creación y persistencia de mensajes de chat en MongoDB.
   - Listado de conversaciones aisladas por usuario (un usuario no puede ver las de otro).
   - Carga y borrado de conversaciones pasadas.
