# NOTES

## Approach

I turned the prototype into something a team can develop on and operate, working in **small, stacked pull requests** (one concern each) so every change is reviewable in isolation. I went deep on **developer experience** and **performance**, behind a **test safety net**, and scoped production-readiness as clearly identified next work rather than doing everything shallowly.

A guiding rule: **preserve exact observable behavior.** Where the prototype has surprising behavior, I treated it as intentional, pinned it with a test, and filed it as an issue — I did not silently change semantics.

## What I did (and why)

**Developer experience.** The database connection now comes from environment variables (`django-environ`) with an `.env.example`; a fresh checkout no longer needs source edits. The toolchain is pinned (uv + Python 3.14) so `uv sync` builds the environment reproducibly.

**A safety net, first.** Before touching behavior I wrote a Django `TestCase` suite (`manage.py test`) that locks the exact response of all eight endpoints — including several intentional quirks (view_count incrementing on every read, drafts readable by id, the `create_post` unknown-tag 500 with a partial write, the duplicate-email 500, empty search matching everything, user counts including unpublished content). These are preserved on purpose and filed as open issues, so the refactor can prove it changed nothing.

**Performance.** I removed the N+1 access on authors, tags and comment authors (`select_related` / `prefetch_related`); query counts are now constant and asserted by tests. I added a partial index on published posts by recency, an email-lookup index, a `(post, created_at)` comment index, and partial GIN trigram indexes on title/body (keeping exact `ILIKE` semantics).

The most useful finding, from `EXPLAIN` on the seeded 100k/500k dataset: **on an unbounded list an index cannot help** — the planner reads ~90% of the table — so the real fix is *bounding* the query. With `LIMIT 20` the same list drops from ~42 ms (sequential scan + on-disk sort) to ~0.6 ms (index scan). Trigram search turns a ~213 ms scan into ~1–5 ms for selective terms.

**API evolution without breaking clients.** Rather than change the existing endpoints (the front/mobile depend on their shape), I added a versioned `/api/v2/` for the three list endpoints with django-ninja `LimitOffset` pagination (`?limit=&offset=`, default 20 / max 100) and a `{items, count}` envelope. The query logic lives in a small use-case layer with a deterministic total order (`-created_at, -id`). On real data a v2 page returns in ~13–80 ms instead of materializing ~90k rows.

## What I deliberately didn't do

- **Fix the functional bugs.** The brief frames the quirks as intentional; I preserved and documented them rather than changing semantics. Fixing them is a product decision (the issues are ready).
- **Containerize / pick a deploy target / add observability.** This is the highest-signal remaining work; I scoped this round to DX + performance to go deep, not broad.
- **Full-text search (`tsvector`).** It changes match semantics; trigram keeps the exact `ILIKE` behavior, which was the constraint.
- **Reshape the domain model.** Not required for the performance work.

## What I'd do next (with another day)

- **Production readiness:** a multi-stage Docker image + gunicorn/uvicorn, a settings split with 12-factor config, `/health` live/ready probes, structured logging, `CONN_MAX_AGE`, and a real deploy manifest (Helm chart / K8s).
- **Observability:** Prometheus metrics + request IDs, ready for Grafana/Loki.
- **Cursor pagination** on the v2 endpoints to drop the `count(*)` cost on very large result sets.
- **Security hardening:** move `SECRET_KEY` to the environment, default `DEBUG=False`, and set real `ALLOWED_HOSTS`.

## Running it

```sh
uv sync
cp .env.example .env      # point it at a local Postgres 16
uv run python manage.py migrate
uv run python manage.py seed        # ~100k posts / ~500k comments
uv run python manage.py runserver   # docs at /api/docs
uv run python manage.py test        # the safety net
```
