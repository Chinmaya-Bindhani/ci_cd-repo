# Agent Pipeline — Cost, Debugging, Deploy

## Run it
```bash
pip install -r requirements.txt

python pipeline.py
python broken_pipeline.py --runs 40
python broken_pipeline.py --runs 60 --concurrent
python debug_trace.py --runs 150
python fixed_pipeline.py --runs 200 --concurrent

pytest -v
ruff check .
```

## What's in here
- `pipeline.py` — NaiveAgent vs OptimizedAgent token comparision.
- `broken_pipeline.py` — 4-step agent with 3 bugs: timeout, malformed output, race condition.
- `debug_trace.py` — captures logs and bisects failures to responisble step.
- `fixed_pipeline.py` — same pipeline with bugs fixed.
- `tests/test_pipeline.py` — pytest suite.
- `.github/workflows/ci-cd.yml` — runs tests on push, deploys staging on merge to main.
- `deploy.sh` / `rollback.sh` — deploy and rollback scripts.

## Secrets
All secrets (`STAGING_DEPLOY_ROLE_ARN`, `STAGING_APP_SECRET_KEY`,
`STAGING_DATABASE_URL`) are GitHub Actions env secrets scoped to
staging, not repo-wide. Cloud auth uses OIDC role assumption, no static AWS key stored.

## If a deploy breaks production
```bash
./rollback.sh production
```
Roll back first, diagnose after. Verify via health check + error dashboard.
"# ci_cd-repo" 
