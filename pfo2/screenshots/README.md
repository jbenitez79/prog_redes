# Evidencias Visuales de Pruebas (PFO 2)

En este directorio se almacenan las capturas de pantalla que acreditan el funcionamiento correcto del sistema según los requisitos del trabajo práctico:

1. **`01_registro_consola.png`**:
   - Registro exitoso de un nuevo usuario enviando `POST /registro` con `usuario` y `contraseña`.
2. **`02_contrasena_hasheada_sqlite.png`**:
   - Inspección directa en SQLite (`tareas.db`) demostrando que las contraseñas están almacenadas exclusivamente como hashes criptográficos irreversibles y con *salt*.
3. **`03_login_exitoso.png`**:
   - Autenticación correcta a través de `POST /login` y despliegue del menú de gestión de tareas.
4. **`04_endpoint_tareas_html.png`**:
   - Visualización del **HTML de bienvenida** en el navegador web al acceder a `GET /tareas`.
5. **`05_tests_automatizados.png`**:
   - Ejecución de la suite completa con `python -m unittest test_api.py -v` con los 7 tests pasando con éxito (`OK`).

*Las capturas fueron generadas y pueden regenerarse en cualquier momento mediante `python generar_capturas.py`.*
