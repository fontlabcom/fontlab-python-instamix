---
this_file: AGENTS.md
---

# Instamix contributor guide

Instamix bootstraps Python packages and deploys FontLab extensions. Its embedded
runtime uses only the standard library and optional PythonQt. Keep Remopy imports
lazy and external to ordinary embedded imports. FontLab 9 currently uses Python
3.11; discover the actual host version, platform and architecture before choosing
an interpreter or package target. Never execute FontLab's sys.executable as Python.

Read README, PLAN, TODO, WORK and CHANGELOG before changes. Preserve canonical
editable checkouts and owner work; implement in isolated successors. Exclusions,
pauses, native admission rules and publication holds in the workspace guide apply.
Use graph impact before symbol edits, then confirm incomplete results against
current source and structural ast-grep searches. Isolated graph work requires
both GITNEXUS_HOME and GITNEXUS_STORAGE_PATH in task-owned locations.

Run focused regression checks while implementing and `bash test.sh` for the
complete changed source. Host checks must explicitly select arm64 Python 3.11
on Apple Silicon; a version-only request can choose x86_64. Keep the unchanged
80% coverage gate for complete changed production modules. Build wheel and sdist
with `uv build`; verify installed metadata, licences and import origins separately.
Docs use fly-january 0.2.1 with FontLab chrome in `src_docs/mkdocs.yml`.
Install the hashed `src_docs/requirements.txt` in a Python 3.13 environment,
then run `sh src_docs/build.sh` and `python -m unittest discover -s tests_docs -v`.

For authorized releases, `./publish.sh` dispatches `release.yml` after the local
release build. The workflow uploads to PyPI through Trusted Publishing in the
`pypi` environment.

Installation failures must preserve existing packages and owner-modified files.
Keep extension/library/ledger containment and explicit target propagation coherent.
A timeout leaves process or native mutation outcomes uncertain; never replay by
inference. Native checks use the workspace's serialized fl-native.sh guard. Do not
recreate a missing guard, restart FontLab, or claim mocks establish native behavior.

After each important reviewed round, refresh actual upstream main and owner/worktree
attachments. Compose the exact reviewed residual delta in a fresh isolated successor
from origin/main, preserving both sides' intent. Run the full suite, lint, required
docs checks and graph change analysis on the combined result; obtain independent
merge review before the controller commits. Push through installed pre-push gates
without bypass, verify actual remote SHA and exact-commit CI, and reconcile again
if upstream advances. Keep source integration, release assets, ordinary installation
and native acceptance distinct. Never force-push or rewrite published history.

Record verified completed work in CHANGELOG. Keep PLAN future-facing and TODO flat,
unchecked and limited to remaining work or verification. Preserve failed receipts
and existing history. Installation reports print through the shared message helper;
do not reintroduce modal dialogs into unattended installation.
