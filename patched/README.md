# patched/ — fix overlay

Contains **only the files the fix changes**, at the same paths they occupy
under `orchestrator/` and `analyzer/`. **The folder is the diff**.

```bash
docker compose -f docker-compose.yml -f docker-compose.patched.yml up --build
```

Layers:

- **Layer 1 — registry integrity** → `patched/orchestrator/src/registry.ts`
  validates `registry.json` against `patched/registry/manifest.json`
  (fail-closed).
- **Layer 2 — output provenance** → the orchestrator HMAC-signs the payload
  (`patched/orchestrator/src/provenance.ts`) and the analyzer requires a
  valid HMAC **and** an authorized `selected_tool`
  (`patched/analyzer/src/validate.ts`).

HMAC answers *who produced the message and whether it was modified in
transit*. It does not claim the content is semantically safe. That is why
layer 2 also checks the manifest: an authentic result from an unauthorized
tool is rejected.

The `diff` between `orchestrator/src/index.ts` / `registry.ts` and their
`patched/` counterparts is what `EXPLANATION.md` §5 shows.

`orchestrator/src/provenance.ts` and `analyzer/src/validate.ts` are unused
placeholders so Docker Desktop can overlay the patched files onto the
read-only `src/` bind-mount. The vulnerable entrypoints do not import them.

The defense matrix with toggleable defenses lives in
`experiments/06-defense-matrix/`, not as flags inside the vulnerable code.
