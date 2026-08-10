# ES

Se establecen varios milestones para la refactorización del proyecto, siendo cada milestone o fase un PR distinto.

Approach defensivo. Cuando se encuentra un bug, se asume que fue dejado ahí intencionalmente por un dev por alguna razón. Se revisa el git log y se determina si fue ese el caso, si fue dejado por un agente o es un bug real.

Los bugs que se encuentren se registran como issue de github para posterior trabajo.

- Se aplican buenas prácticas de seguridad en settings.py, moviendo la config de debug, secret key y credenciales de la db a variables de entorno. No he tocado ALLOWED_HOSTS.
- Para los endpoints existentes, se crean tests usando la suite nativa de Django para asegurar que la funcionalidad se mantiene luego del refactor.
- Se realizan optimizaciones básicas para evitar issues de queries N+1 y se agregan los índices correspondientes a la db sobre las columnas que reciben mayor número de queries.
- Se asume que un frontend web o mobile consume los endpoints, por lo tanto se mantiene la estructura de respuesta de los mismos y se creará una nueva versión de API para que el frontend se migre. Una de las mejoras que cambia estructura es que se agrega paginación a los endpoints.
- Mientras no ocurra lo del punto anterior, la versión actual pasa a deprecado, se agrega un limit 20 a la respuesta y para mitigar una query que ejecuta un ILIKE en la db (y asegurar que mantenga la funcionalidad), se agrega un índice GIN con trigrama. Se agregan tests para medir el impacto en rendimiento.
- Se agrega una nueva versión de endpoints con paginación, se mantiene contrato del path url.
- Los casos de uso y lógica de negocio se lleva a un archivo usecase, cada versión de api tendrá uno propio, por lo tanto el código de cada versión de api es completamente independiente y no tiene dependencia lógica en relación a la versión anterior. Usando una herramienta de monitoreo se puede medir el uso y adoption rate de cada versión, cuando una se deje de usar o cuando se cumpla un periodo de tiempo establecido por el negocio, se puede eliminar de forma segura el código completo de la versión en cuestión.
- El último PR #15 los 8 bugs que venían heredados de v1 en v2.
- Se agrega Dockerfile, no lo revisé tan exhaustivamente porque el scope está creciendo mucho.
- Yo eliminaría django ninja, es suficiente con lo que ya trae django y puede quedar mejor ordenado, es más fácil mantener algo leyendo el manual de django que el de django y además el de ninja, no reinventar la rueda.
- No agregué gihub action que corre tests en cada pr/commit.
- Todos los PR los reviso antes de mezclar.

Usé agents para escribir el código, incluiré el plan inicial que después iteré, no incluiré toda la conversación porque lo encuentro invasivo y también tengo mi set de prompts, skills, subagents que incluyen todo mi flujo de trabajo (Context harvesting, research, abrir PRs, code reviews, responder CR de otros agents, documentar, etc) que he trabajado por mi cuenta e iterado con el paso de los años; esto es parte de mi sello por como se ha ido reinventando el rubro con los LLM.

El cómo decidí resolver los problemas del proyecto es fruto de la larga experiencia que tengo trabajando en startups y haciendo que los productos escalen tanto a nivel de negocio como para que los equipos de devs puedan mantenerlos.

## EN

Multiple milestones are established for the project refactoring, with each milestone or phase being a separate PR.

Defensive approach. When a bug is found, it is assumed that it was intentionally left there by a developer for some reason. The git log is reviewed to determine if that was the case, if it was left by an agent, or if it is a real bug.

Bugs that are found are registered as GitHub issues for subsequent work.

- Good security practices are applied in settings.py, moving debug config, secret key, and database credentials to environment variables. I have not touched ALLOWED_HOSTS.
- For existing endpoints, tests are created using Django's native test suite to ensure functionality is maintained after the refactor.
- Basic optimizations are performed to avoid N+1 query issues and corresponding indexes are added to the database on columns that receive the highest number of queries.
- It is assumed that a web or mobile frontend consumes the endpoints, therefore the response structure of them is maintained and a new API version will be created for the frontend to migrate to. One of the improvements that changes structure is the addition of pagination to the endpoints.
- Until the above happens, the current version becomes deprecated, a limit of 20 is added to the response, and to mitigate a query that executes an ILIKE on the database (and ensure it maintains functionality), a GIN index with trigrams is added. Tests are added to measure the performance impact.
- A new version of endpoints with pagination is added, maintaining URL path contract.
- Use cases and business logic are moved to a usecase file, each API version will have its own, therefore the code of each API version is completely independent and has no logical dependency in relation to the previous version. Using a monitoring tool, the usage and adoption rate of each version can be measured; when one is no longer used or when an established time period passes (defined by business), the complete code of that version can be safely removed.
- The last PR #15 fixed the 8 bugs that were inherited from v1 in v2.
- Dockerfile is added, I did not review it as exhaustively because scope is growing significantly.
- Added healthcheck for k8.
- I would remove django-ninja, Django's built-in features are sufficient and can be better organized, it is easier to maintain by reading the Django manual than both Django and Ninja manuals, no need to reinvent the wheel.
- I did not add GitHub Actions that run tests on each PR/commit.

I used agents to write the code, I will include the initial plan that I later iterated, I will not include the entire conversation because I find it invasive (Specially when the model does something I don't want), and I also have my own set of prompts, skills, and subagents that include my entire workflow (context harvesting, research, opening PRs, code reviews, responding to CRs from other agents, documenting, etc.) that I have worked on independently and iterated over the years; this is part of my signature in how the field has been reinventing itself with LLMs.

The way I decided to solve the project's problems is the result of long experience working in startups and making sure products scale at both the business level and allow dev teams to maintain them.


# Running it

```sh
uv sync
cp .env.example .env      # point it at a local Postgres 16
uv run python manage.py migrate
uv run python manage.py seed        # ~100k posts / ~500k comments
uv run python manage.py runserver   # docs at /api/docs
uv run python manage.py test        # the tests
```

# Original plan

Plan — Fintual `backend-devops-interview`

## Context

Take-home de entrevista (vacante Senior Backend/Infra, Fintual). El README pide convertir el prototipo en algo operable por un equipo en 3 ejes: **DX, performance, production readiness** (profundidad > amplitud).

Estrategia dada por el usuario:
- **Refactor que preserva comportamiento exacto** en los endpoints existentes, protegido por una red de tests (`manage.py test` + `TestCase`). Esos tests no se modifican después del refactor.
- La performance se resuelve **de forma aditiva**: se agrega un **endpoint nuevo versionado** con `limit` + query optimizada, para **no romper el front/app mobile**. Patrón: **use case + tests + nueva versión del endpoint**.
- Los **bugs se preservan** (se asumen intencionales): se fijan con tests y se reportan al final; **no se tocan**. Provenance vía `git log`. Al final se arreglarán en la versión final de los endpoints.
- Las **malas prácticas** (SECRET_KEY expuesta, DEBUG, etc.) se arreglan **solo tras evaluación/aprobación** del usuario y este manifiesta auditar por su cuenta y mencionar cuáles mover a .env.
- Correr contra el **Postgres existente** del usuario (sin docker en el setup, sin contaminar el Python del sistema). Credenciales parametrizadas vía `.env`, **mínimo necesario**.

Entorno verificado (read-only):
- `uv` tiene CPython **3.14.2** → `uv sync` crea `.venv`; `mise` NO se necesita; Python 3.12 del sistema intacto.
- Postgres **16.8** corriendo (contenedor OrbStack pgvector/pg16) en `127.0.0.1:5432`. `backend_devops_interview` **existe y está vacía**. Rol dev `testuser` es **superuser** (permite crear el rol del proyecto). `pg_trgm` disponible (1.6, sin instalar).
- Git: **un solo commit squashed** `b74e8ed` por Rodrigo Basoalto `<basoalto@fintual.com>`, sin trailer de co-autor AI → bugs plantados por un humano de Fintual (el README confirma que la lentitud es intencional).

## Bugs a PRESERVAR (fijar con test, no arreglar en v1, si en v2)
1. `GET /posts/{id}` incrementa `view_count` en cada lectura + `save()` completo bumpea `updated_at` (`api.py:67-68`).
2. `get_post` no filtra `is_published` → drafts legibles por id (`api.py:66`).
3. `create_post` con slug de tag inexistente → `Tag.DoesNotExist` (500) y **Post ya persistido** (escritura parcial, no atómico) (`api.py:100-102`).
4. `find_user_by_email` con emails duplicados → `MultipleObjectsReturned` (500); `email` no es unique (`api.py:116`, `models.py:7`).
5. `search q=""` retorna todo lo publicado; `q` ausente → 422 (`api.py:49-51`).
6. `_user_detail` cuenta posts/comments **incluyendo no publicados** (`api.py:133-134`).
7. `create_comment` permitido sobre posts no publicados (`api.py:108`).
8. Sin tie-break en `created_at` igual → orden no determinista (`api.py:44,53,60,77`). Se **documenta**, no se fija (flaky).

## Malas prácticas (reporte final, arreglar solo con aprobación)
SECRET_KEY commiteada, `DEBUG=True`, `ALLOWED_HOSTS=["*"]`, credenciales hardcodeadas (estas sí se mueven a `.env` ahora, por pedido explícito). CSRF y `TIME_ZONE` NO son defectos reales aquí (django-ninja sin auth desactiva CSRF a propósito; `TIME_ZONE` es cosmético con `USE_TZ=True`).

---

## Workflow incremental (stacked PRs + issues)
- Fork del usuario (`Freyja-Folkvangr/backend-devops-interview`) como `origin`; `fintual-oss` como `upstream`. El README prohíbe PRs contra el repo original → todos los PRs van al fork. (Ya creado por el usuario; SSH `git@github.com:Freyja-Folkvangr/backend-devops-interview.git`.)
- Una rama por fase, **apilada sobre la anterior** (kebab-case, sin prefijos): `setup-env` → `test-safety-net` → `perf-optimization` → `paginated-endpoint-v2` → `docs-notes-report`.
- Cada fase: commits pequeños incrementales → abrir PR con base = main (P0 con base `main`). Asignar a Freyja-Folkvangr; comentario con mermaid donde aporte valor. Convenciones de `~/.claude/CLAUDE.md`.
- Los 8 bugs preservados → **un issue por bug en el fork** (Phase 1), quedan **ABIERTOS** (intencionales). NO usar `Fixes/Closes #N`; referenciar con `Refs #N` desde el test/PR que los fija.

## Phase 0 — Entorno + fork (rama `setup-env`, PR base `main`)
- Fork ya creado. Reconfigurar remotes: `git remote rename origin upstream` + `git remote add origin git@github.com:Freyja-Folkvangr/backend-devops-interview.git` + `git fetch origin`; verificar issues habilitados en el fork.
- Crear rama `setup-env` desde `main`.
- `uv sync` → `.venv` (3.14.2). Verificar `uv run python -V`.
- Rol DB del proyecto: conectado como `testuser` (superuser) → `CREATE ROLE <bdi_admin> LOGIN SUPERUSER PASSWORD '<generada>'`; `ALTER DATABASE backend_devops_interview OWNER TO <bdi_admin>`. Superuser (full admin, por instrucción) también habilita que `manage.py test` cree la test DB y `CREATE EXTENSION pg_trgm` ahí.
- Agregar dep `django-environ`. Crear `.env` (gitignored) con `DB_NAME/DB_HOST/DB_PORT/DB_USERNAME/DB_PASSWORD` del rol nuevo; crear `.env.example` commiteado (sin secretos).
- Parametrizar `core/settings.py` `DATABASES` vía `env()` (`ENGINE=django.db.backends.postgresql`), con los valores actuales como fallback → comportamiento sin cambios si falta `.env`. SECRET_KEY/DEBUG quedan igual (su env-ificación es fix de mala práctica, gated).
- `.gitignore`: agregar `.env`, `CLAUDE.md`, `wiki/`, y el doc privado de cumplimiento.
- `uv run python manage.py migrate` → `uv run python manage.py seed` (necesario para verificar perf/EXPLAIN; un perfil de seed pequeño es mejora DX opcional).
- Archivos: `pyproject.toml`, `core/settings.py`, `.env`(nuevo, ignorado), `.env.example`(nuevo), `.gitignore`.

## Phase 1 — Red de tests + issues de bugs (rama `test-safety-net` sobre `setup-env`, PR base `setup-env`)
- Un solo runner: reescribir `blog/tests/` como clases `django.test.TestCase`; migrar los 3 smoke tests pytest existentes a `TestCase` para que `manage.py test` corra todo.
- Fijar el comportamiento EXACTO de los 8 endpoints, **incluyendo los bugs** (siguen verdes tras el refactor porque se preserva el comportamiento):
  - list/search/by-tag: solo publicados, `-created_at`, vacío=`[]`, shape JSON exacto; `search q=""` → todo publicado; `q` ausente → 422; slug desconocido → 404.
  - get_post: `view_count` incrementa por GET (assert explícito); draft legible por id; comments asc; id desconocido → 404.
  - create_post: autor desconocido → 404; **tag desconocido → `Tag.DoesNotExist`** (`assertRaises`); Post huérfano persiste (assert `.exists()`).
  - create_comment: permitido en post no publicado; post/autor desconocido → 404.
  - find_user_by_email: **email duplicado → `MultipleObjectsReturned`** (`assertRaises`); `email` ausente → 422; desconocido → 404.
  - `_user_detail`: counts incluyen no publicados (assert con draft presente).
  - Orden de rutas: `/posts/search` y `/users/find` resuelven como estáticas.
- Guardas de conteo: `assertNumQueries` como **techo del target** (post-optimización), aterrizadas **junto al commit de Phase 2** (NO fijar el N+1 previo, que la regla "no modificar tests" luego prohibiría corregir). Los pins de comportamiento no llevan assert de queries.
- Archivos: `blog/tests/test_posts.py`, `test_comments.py`, nuevo `test_users.py`, nuevo `test_behavior_pins.py`.
- Verificar: `uv run python manage.py test` verde sobre el código ACTUAL (sin refactor).
- Crear **8 issues en el fork** (uno por bug de "Bugs a PRESERVAR"), abiertos: file:line + comportamiento observado + provenance (commit único de Fintual, sin firma AI) + "preservado, fijado por test X" ("documentado" para #8). `Refs #N` desde cada test; NUNCA `Fixes`.
- Commits incrementales → PR (base `setup-env`).

## Phase 2 — Optimización que preserva salida (rama `perf-optimization` sobre `test-safety-net`, PR base `test-safety-net`)
- Eliminar N+1: `select_related("author").prefetch_related("tags")` en list/search/by-tag; en get_post `Prefetch("comments")` + `select_related("author")` en comments. Salida idéntica → tests congelados verdes; aquí se agregan los techos `assertNumQueries`.
- Migración de índices (agregar SOLO los realmente faltantes; los FK ya están indexados por Django — verificar con `\d` antes):
  - `Post.created_at` btree; `Post.is_published` parcial `WHERE is_published`; `User.email` btree; `Comment(post_id, created_at)` compuesto. Todo output-preserving (vía `Meta.indexes` + migración).
- DESCARTAR el "combinar los dos COUNT" (un solo aggregate = JOIN cartesiano, counts erróneos); se dejan los dos `.count()` indexados.
- Dejar `view_count` como está (bug preservado); NO usar `F()`/`update_fields` (cambiaría `updated_at` o requeriría `refresh_from_db`); en get_post solo se optimiza el N+1 de comments.
- Búsqueda pg_trgm (OPCIONAL, "se verá"): si se aprueba, `TrigramExtension()` (`CREATE EXTENSION pg_trgm`; rol superuser lo permite en dev + test DB) + `GinIndex(OpClass(..., 'gin_trgm_ops'))` en `title` y `body`, parcial `WHERE is_published`. Mantiene semántica `ILIKE '%q%'` (solo ayuda a términos ≥3 chars).
- Archivos: `blog/api.py`, `blog/models.py`, nuevo `blog/migrations/0002_indexes.py` (+ opcional `0003_search_trgm.py`).
- Verificar: `manage.py test` verde (prueba preservación) + caída de `assertNumQueries`; EXPLAIN ANALYZE opcional sobre DB sembrada.
- Commits incrementales (N+1, índices, [trgm opcional] por separado) → PR (base `test-safety-net`); comentario mermaid del flujo de queries antes/después.

## Phase 3 — Endpoint paginado nuevo (rama `paginated-endpoint-v2` sobre `perf-optimization`, PR base `perf-optimization`)
- Capa use case: `blog/usecases.py` (o `selectors.py`) con la query de posts optimizada y paginada: `limit` (+ offset), select_related/prefetch, orden total determinista `-created_at, -id`.
- Endpoint nuevo versionado que NO toca el existente (front/mobile a salvo): router v2 en `/api/v2/` → `GET /api/v2/posts?limit=&offset=` con contrato acotado. `/api/posts` intacto.
- Tests del use case + endpoint nuevo (respeta `limit`, orden determinista, shape). Estos sí pueden evolucionar (cubren lo nuevo).
- Alcance: profundizar primero en la lista de posts (README "depth > breadth"); replicar patrón a search/by-tag es opcional.
- Archivos: nuevo `blog/usecases.py`, `blog/api_v2.py` (o extender router), `core/urls.py`, nuevo `blog/tests/test_v2_posts.py`.
- Verificar: endpoint nuevo retorna ≤`limit` ordenado; `/api/posts` idéntico byte-a-byte (tests congelados verdes).
- Commits incrementales (use case → tests → endpoint) → PR (base `perf-optimization`); comentario mermaid del contrato v1 vs v2.

## Phase 4 — Reporte, wiki, entregables <redacted>

## Verificación end-to-end
- `uv run python manage.py test` verde antes de Phase 2 y después de Phases 2–3 (comportamiento preservado).
- N+1 eliminado: techos `assertNumQueries`; EXPLAIN ANALYZE opcional sobre 100k/500k mostrando uso de índices (created_at/is_published/email + trgm en search).
- `/api/v2/posts` acotado + ordenado; `/api/posts` idéntico (diff de una respuesta antes/después).
- DB accesible vía rol de `.env`; `manage.py test` crea/dropea `test_backend_devops_interview` (rol superuser).
