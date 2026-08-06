# Production Checklist

Use this checklist for every v1.0.0 deployment. Record evidence outside the repository without including secrets.

## Build and supply chain

- [ ] Release source is reviewed and CI is green.
- [ ] Python is 3.12 and pinned dependencies install successfully.
- [ ] `pip check`, Ruff formatting, Ruff lint, and all tests pass.
- [ ] Docker image builds from the multi-stage Dockerfile.
- [ ] Image digest and release tag are recorded.
- [ ] Dependency and base-image vulnerability review is complete.

## Configuration and secrets

- [ ] `.env` is untracked, access-controlled, and absent from the image.
- [ ] Only approved providers are enabled.
- [ ] Keys are scoped, rotated, and stored through the deployment secret mechanism.
- [ ] Provider models, timeouts, retries, token limits, priorities, and costs are reviewed.
- [ ] SQL/CSV roots and Website Reader allowlist are least privilege.

## Network and security

- [ ] API and dashboard publish only to `127.0.0.1`.
- [ ] No direct public or untrusted network exposure exists.
- [ ] Outbound destinations are restricted to approved providers.
- [ ] Container runs non-root with dropped capabilities, read-only root, and no-new-privileges.
- [ ] Logs and monitoring snapshots contain no secrets or request content.

## Runtime validation

- [ ] `docker compose config --quiet` succeeds.
- [ ] Both containers become healthy.
- [ ] `/health` returns `status=ok`.
- [ ] `/ready` returns `ready=true`.
- [ ] All seven tools and all three provider slots appear in the operational snapshot.
- [ ] Dashboard health returns `ok` and the dashboard loads.
- [ ] `python scripts/verify_release.py` passes.

## Operations and recovery

- [ ] Persistent data volume and backup policy are approved.
- [ ] Resource limits are set by the hosting platform.
- [ ] Log retention, alerting, and incident ownership are defined externally.
- [ ] Previous image, configuration backup, and rollback procedure are available.
- [ ] Known limitations and provider terms are accepted by the owner.
