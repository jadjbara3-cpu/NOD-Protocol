# Secrets Management — NØD Protocol

## Policy (v1.0)

The NØD Protocol repository is **public and global**. Its security posture
is explicit:

1. **No credentials are ever committed.** Everything under `.secrets/` is
   excluded from version control (`.gitignore` rules: `.secrets/`,
   `*.token`, `*.env`).
2. **The reference implementation uses no secrets.** It is pure Python,
   stdlib-only, offline, and performs no network calls (see
   `docs/TECHNICAL-SPECIFICATION.md §10`).
3. **GitHub access tokens** — when provisioned — are stored exclusively in
   `.secrets/github.token` (never published) and used only for repository
   administration (create repo, push files, verify access).
4. **Rotation**: tokens are created with an expiry; when expired, a new
   token is generated and the old one deleted.
5. **No third-party services**: the project does not call any external API
   at runtime.

## Layout

```
.secrets/            ← git-ignored, never published
└── github.token     ← GitHub Personal Access Token (classic)
```

## Verification

Run from the project root:

```bash
git check-ignore .secrets/github.token   # must output the path (ignored)
git status --porcelain                   # must NOT list .secrets
```

---

*NØD Protocol — Secrets Management Policy v1.0 — August 2026*
