# Reference: pnpm + Cloudflare for ALPS sites

## Why builds fail (the gotcha in full)

ALPS sites are Astro + `@astrojs/cloudflare`, deployed via **Cloudflare Workers Builds** (the `cloudflare-workers-and-pages[bot]` Git integration — build logs live only in the Cloudflare dashboard, not GitHub). Native deps `esbuild`, `sharp`, `workerd` have install scripts.

Observed across pnpm majors (lockfile is `lockfileVersion 9.0`):

| pnpm | clean `pnpm install` | result |
|------|----------------------|--------|
| 9.x  | errors `packages field missing or empty` if a `pnpm-workspace.yaml` without `packages:` exists | deploy fails |
| 10.15.1 | exits 0, builds native deps | **works** |
| 11.x | `ERR_PNPM_IGNORED_BUILDS`, exit 1, allow-list NOT honored | deploy fails |

`pnpm build` runs a pre-step deps check that itself runs `pnpm install`, so a non-zero install fails the build before `astro build` runs.

## The fix that sticks (committed)

Add to `package.json`:

```json
"packageManager": "pnpm@10.15.1"
```

Cloudflare honours `packageManager` via corepack, so CI uses the working version. Do **not** rely on `pnpm-workspace.yaml: onlyBuiltDependencies` — it is read by `pnpm config` but not applied during install on pnpm 11, and the file itself breaks pnpm 9.

If you find a `pnpm-workspace.yaml` that only contains `onlyBuiltDependencies` (no `packages:`), delete it and add the pin.

## Local builds

`pnpm approve-builds --all` after install makes a LOCAL build succeed (it runs the scripts + records approval) but does nothing for CI. Always also set the `packageManager` pin so the deploy works. Use `npx -y pnpm@10.15.1` and a shared `--store-dir` so local matches CI and installs are fast.

## Verifying a deploy

- Find the live domain in `wrangler.jsonc` → `routes[].pattern` (custom_domain).
- The homepage `index.html` is prerendered; most other routes are SSR (the build log printing "file not created, response body was empty" for them is normal, not an error).
- Poll with `scripts/poll_live.sh`. Choose a marker that ONLY your change introduces; generic strings (a speaker's name that also appears in a schedule) give false positives.

## Merge convention

Squash merges (`gh pr merge <n> --squash --delete-branch`); `main` history reads `Title (#N)`. The local post-merge checkout sometimes errors because pnpm regenerated a dirty `pnpm-workspace.yaml` stub — the remote merge already succeeded; verify with `gh pr view`.
