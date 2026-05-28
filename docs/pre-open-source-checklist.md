# Pre-Open-Source Checklist

## Final tree review

- [ ] Review the final public file tree for lab-specific or internal-only content
- [ ] Confirm files like `AGENTS.md`, docs, examples, and local config placeholders are acceptable for public release
- [ ] Confirm `config.json` points at the intended public Docker image before the first release
- [ ] Confirm README install examples use a release tag rather than a moving branch
- [ ] Confirm third-party notices are accurate for bundled upstream-derived code
- [ ] Run the local release preflight on the public tree
- [ ] Confirm GitHub Actions pass on `master`
- [ ] Confirm tag workflow publishes the GitHub release and GHCR image

Example:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\release_check.ps1
```

```bash
bash scripts/release_check.sh
```

Use `-SkipDocker` on PowerShell or `--skip-docker` on Bash only when Docker is unavailable and CI will do the Docker validation.

## Optional safety backup

- [ ] Create a backup branch before rewriting history
- [ ] Push the backup branch to origin if you want a private recovery point

Example:

```powershell
git branch backup/pre-public-master
git push origin backup/pre-public-master
```

## Rewrite `master` to one clean commit

- [ ] Create a new orphan branch from the final merged tree
- [ ] Commit the full tree as a single fresh `Initial commit`
- [ ] Replace `master` with that orphan branch
- [ ] Force-push the rewritten `master`

Example:

```powershell
git checkout --orphan public-reset
git add -A
git commit -m "Initial commit"
git branch -D master
git branch -m master
git push -f origin master
```

## Post-rewrite cleanup

- [ ] Verify `master` now shows a single clean commit
- [ ] Delete no-longer-needed private or feature branches from origin
- [ ] Delete any no-longer-needed local backup branches
- [ ] Re-check the GitHub repo settings before making the repository public

Example:

```powershell
git push origin --delete <branch-name>
```
