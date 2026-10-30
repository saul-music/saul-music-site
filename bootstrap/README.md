# Bootstrap del sitio

`gcp.sh` deja listo en GCP todo lo que el pipeline necesita y Terraform aún no crea (D56). Es
idempotente: puede correrse de nuevo sin efectos. El script basta para recrear el entorno desde cero.

```bash
DRY_RUN=1 bootstrap/gcp.sh   # solo muestra qué haría
bootstrap/gcp.sh             # ejecuta
```

Usa las credenciales de `~/.config/gcloud-saul` (variable `CLOUDSDK_CONFIG`), nunca las de otra
cuenta. Crea en `saulapp-music`, región `southamerica-west1`:

- APIs de Cloud Run, Artifact Registry, IAM, STS y Resource Manager.
- Repo de imágenes `musicsite` (tags inmutables).
- Service accounts `musicsite-deployer` (CI) y `musicsite-runtime` (Cloud Run, **sin roles**: el sitio
  no accede a datos).
- Proveedor WIF `github-musicsite` en el pool `github`, restringido a este repo y a la rama `main`.

**Paso manual en GitHub (una vez):** crear la variable de repositorio `GCP_WIF_PROVIDER` con el valor
que imprime el script al final (no es un secreto):
`gh variable set GCP_WIF_PROVIDER --body "<valor>"`.

**No hace:** cambios de políticas de organización (la excepción que permite servicios públicos ya
existe en el proyecto), dominio propio ni nada de datos.
