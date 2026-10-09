# Cómo colaborar

1. **Issue:** cada tarea principal tiene un issue en GitHub (pestaña Issues → New issue).
2. **Rama:** se trabaja en una rama con el número del issue, por ejemplo `3-exploracion-redda`.
   En VS Code: clic en el nombre de la rama abajo a la izquierda → *Create new branch*.
3. **Commits:** mensajes cortos que digan qué cambió, por ejemplo `Agregar exploración de REDDA`.
4. **Pull request:** al terminar, subir la rama (*Publish Branch*) y abrir un pull request en GitHub que diga `Closes #3`.
5. **Revisión:** otro integrante revisa y aprueba el pull request antes de hacer merge a `main`.

Reglas:
- No subir datos grandes: solo `data/sample/`.
- No subir `config/config.yaml` ni credenciales.
- Correr `pytest` antes de abrir el pull request.
