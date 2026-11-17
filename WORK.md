---
this_file: WORK.md
---
# Issue 256 implementation review

## 2026-11-17 — Manifest entry point

Baseline: controller reported 154 tests passing. Added direct selection of
manifest.fontlabextj (case-insensitive), routing to the containing .fontlabext
folder. Wrong filenames and manifests outside extension folders refuse before
creating deployment folders. Folder basename still controls {} substitution;
manifest ID still controls the Library/ledger identity, preserving existing behavior.
CLI and lazy public exports already forward to extension.install; bootstrap
folder calls remain compatible. Tests cover those boundaries and CLI installation.

Graph impact was attempted with task-owned GITNEXUS_HOME and
GITNEXUS_STORAGE_PATH; GitNexus 1.6.12 returned “No indexed repositories found”.
Graph risk remains unresolved. Current ast-grep callers: CLI cmd_ext_install,
bootstrap.install_project and tests; public __init__ lazily exports the function.
No global registry setup, graph indexing or edits were performed.

Full test.sh: 161 passed under ordinary CPython 3.14.10. No FontLab install,
native run, remote delivery, or cross-platform acceptance is claimed. Independent
review and controller verification remain required. See TODO for remaining work.

### Independent review revision

Changed the new parent-identity regression to use matching folder/manifest IDs;
it now verifies the requested parent basename substitution without cementing the
existing mismatch defect. Added mismatch refusal, CSV RECORD parsing, generated
file upgrade rollback and draft plugin wrapping to PLAN/TODO. Production scope
is unchanged. Controller reports isolated graph indexing completed; its graph
checks supersede the initial missing-index limitation when recorded separately.

Verification: `bash test.sh tests/test_extension.py tests/test_bootstrap_cli.py`
passed 45 tests in 0.29s; `git diff --check` passed. Independent re-review remains.


## 2026-11-17 — Public API data defaults

The three public extension functions now resolve `data=None` at their entry
boundaries through `env.data_dir()`. Existing explicit positional paths and lazy
exports are preserved. README now includes listing and explicit folder selection.
Four regression cases reproduced the missing-argument failure before the fix,
then passed: folder/manifest/archive install-list-uninstall round trips through
public exports, plus an explicit data folder overriding FONTLAB_DATA_DIR.

Focused: 4 passed (0.15s). Full `bash test.sh`: 165 passed (0.44s), ordinary
CPython; `git diff --check` passed. Existing reviewed manifest-entry edits remain.
Pre-edit isolated GitNexus impact: LOW/exact for all three functions, with CLI,
bootstrap and launcher callers confirmed by ast-grep. Combined detect-changes:
6 files, 12 symbols, 3 affected processes, MEDIUM. Its existing index omits the
new tests and installed signature from that summary, so source/test checks supply
that evidence; no complete graph coverage is claimed. Only task-owned graph home
and storage were used. Separate review/controller gates remain before delivery.
No native, installed, release, or cross-platform verification was performed.


## 2026-11-17 — Validation before writes

Moved wrap.make_folder's existing manifest.parse call before output-path creation
and copying. install_folder now rejects folder/manifest identity mismatches before
ledger access or writes and plans destinations before ensure_folders. Extension
suffixes remain case-insensitive; the reverse-domain namespace must match exactly.
This supersedes the initial entry-point note about preserving mismatched IDs.

Baseline: 165 passed (0.42s). Initial regressions: 23 failed, 3 passed (0.53s),
confirming unsafe writes and missing refusal. The mismatch tests were then
strengthened to use the ID of an existing installation and a renamed source.
Focused final check: 75 passed (0.80s). Full bash test.sh: 191 passed (0.50s).
Snapshots check file bytes, directory membership and link targets before/after
invalid metadata, mismatched identities and invalid plans, with new and existing
data/output directories. Existing bootstrap/editable and mixed-case suffix tests
pass. git diff --check passed.

Pre-edit GitNexus impact was LOW/exact for both make_folder and install_folder.
Callers: cli.cmd_wrap, extension.install and bootstrap._install_checkout, with
CLI/bootstrap consumers upstream; ast-grep confirmed direct calls. Both
GITNEXUS_HOME and GITNEXUS_STORAGE_PATH used the task-owned sibling graph folder.
No dependencies, exports or config changed. Independent review and controller
verification remain required. Destination symlink containment and generated-file
rollback are separate pending rounds. No native run, installation, delivery or
cross-platform verification was performed.

Combined graph change analysis: HIGH risk, 7 files, 16 symbols, 8 affected
flows, including earlier reviewed API edits. Re-ran with --limit 100 to retain
all returned symbols in .superpowers/sdd/PLAN/task-3-graph.txt. The existing
index/diff analysis omits the new untracked regression file; passing source-level
tests supply that evidence, not complete graph coverage. No commit attempted.
Diff inspection found no new placeholders, skipped tests or unfinished branches.


## 2026-11-17 — Destination containment

Moved the existing resolved-parent containment check into env, retaining the
extension.inside entry point. Preflight standard directories, planned placement
parents, Library/staging paths and ledger record/temp/log leaves before writes
or old install removal. Placement and ledger writers recheck their paths.
Source declarations reject absolute/traversing paths before joining while
editable bootstrap source links remain supported. No dependencies or exports changed.

Baseline: 191 passed (0.56s). New regressions first produced 12 failures and
10 passes (0.23s). Focused combined tests passed 71 cases (0.44s). Final
full-suite results are in .superpowers/sdd/PLAN/task-4-report.md. External
sentinels, prior install snapshots and Library staging leaves are checked.
Positives include symlinked data roots/internal directories, editable source and
final package links, copy mode, and ordinary placement rollback.

Scoped GitNexus impacts cover installation, planning, placement and ledger
paths; exact plan impact is HIGH through bootstrap/migration callers. Combined
change analysis reports HIGH, 9 files, 32 symbols and 13 processes, including
previous rounds. The index omits untracked tests; graph results do not replace
source-level checks. All graph state used the controller's task-owned sibling
home/storage. Independent review and controller gates remain before delivery.

Generated-file rollback is deliberately deferred; existing callbacks and pip
operations are not made transactional. Checks do not prevent concurrent path
substitution. Native, installed, cross-platform and release behavior remain
unverified. No commit, push, native call or installation was performed.


## Task 4 independent review revision — uninstall preflight

Review found uninstall removed deployments/Library before ledger.remove rejected
a linked log or temporary record. Added ledger.check_paths at uninstall entry
inside its existing LedgerError translation, before any mutation. Two regressions
first failed whole-tree preservation (2 failed, 34 deselected in 0.16s), then
passed with the one-line fix. Snapshots cover Library, deployments, ledger bytes
and links; external sentinel bytes remain unchanged.

`bash test.sh tests/test_destination_containment.py tests/test_extension.py`:
71 passed in 0.31s. `git diff --check` passed. Scoped uninstall impact is LOW/exact
with CLI/launch callers; combined graph HIGH remains acknowledged. Evidence:
.superpowers/sdd/PLAN/task-4-fix1-{impact,callers,graph}.txt. No duplicate coverage
run: controller's prior coverage evidence remains separate. No native/install/
commit operations. Writer stopped for independent re-review.

## 2026-11-17 — Shared Python environment

Added explicit host target facts, verified architecture-qualified venv creation,
owned `.pth` sharing of canonical packages, local uv reuse, bounded subprocesses,
lazy `install_packages`, option-spec refusal and CSV RECORD removal. Existing
package list/remove APIs accept matching explicit targets. CLI delegates inherit
provider behavior; remote forwarding is separate work.

Full suite: 249 passed on ordinary Python 3.14 (1.01s) and actual arm64 Python
3.11 (1.16s). Real offline wheel installation/import through both venv startup
and direct canonical-path insertion passed. Targeted Ruff and diff checks passed.
Complete changed-module coverage: 86–96%; receipt and commands are in
`.superpowers/sdd/PLAN/task-5-report.md` and `task5-coverage.txt`.

Pre-edit site_packages HIGH hub risk and combined CRITICAL graph result remain
explicit: 14 files, 54 symbols, 22 processes, including prior rounds. New symbols
and untracked tests are not fully represented by the existing index. Writer
stopped for independent review. No native/user installation, commit or push.
Windows, embedded runtime, remopy integration and release checks remain open.

## Task 5 independent review revision 1

Read `task-5-review.md` and reproduced both findings: 4 failing regressions
(three download escape variants and the live-version manifest route), with
2 positive controls passing. `dest.target_root` now obtains its relative package
path from `env.site_packages`; the historical SITE_PACKAGES constant remains
compatibility-only. A mocked embedded 3.12 extension test installs both an explicit
site-packages rule and python.packages into the same canonical directory and
checks requirements' uv --target agrees. Standalone fallback remains 3.11.
Existing explicit `env.Target` package APIs are unchanged; remote execution of
extension operations must still occur in the discovered host context.

`uv.download` now checks destination and temporary parents through the shared
containment provider before filesystem writes, refuses linked destinations and
linked/occupied temporary leaves, and extracts payload before creating folders.
The guard covers both ensure's download fallback and CLI forced downloads because
it lives in download itself. Checksum-valid injected archives verify unchanged
whole scratch snapshots and external sentinels for escaping python/uv parents
and uv.tmp links; a symlinked data root continues to work.

Validation: focused tests 65 passed in 0.38s; full test.sh 255 passed in 0.88s.
The full run is justified by changing the destination provider used by all
extension/migration callers. Targeted Ruff and diff checks passed. Scoped impact
for target_root and download was LOW/exact; combined graph remains CRITICAL
with prior rounds included (`task5-fix1-graph.txt`). The same documented stale
index/new-test coverage limits remain. No new native/Windows claims. Controller's
separate uharfbuzz scratch proof is not writer-run evidence.

Writer stopped for independent re-review. No commits, installs or native calls.

## 2026-11-17 — Generated-file upgrade rollback

Bootstrap builds metadata and uninstall launchers in scratch storage before legacy
migration or installation. The existing placement path deploys those artifacts.
Upgrade snapshots preserve actual unchanged installed copy bytes, including old
records without source fields. Library and snapshots survive until the ledger
commits; ledger record, temporary file and log bytes are restored on failure.
Shared launcher parent directories remain unowned in the saved record but tracked
for rollback. Modified launchers refuse without loss, unrelated stale metadata is
preserved, and dependency failure still commits requires_failed before re-raising.

Baseline: 255 passed in 1.02s. Initial new regressions: 11 failed in 0.20s.
Final coverage run: 268 passed in 3.09s, x86_64 Python 3.11.16; bootstrap and extension
complete-module coverage both 92%. Thirteen failure/preservation cases pass.
Targeted Ruff and git diff --check pass. Original reproduction now reports old
metadata restored and new metadata absent. Test-only archive caching fixes the
previously recorded gzip timestamp nondeterminism; no production download change.

Scoped removal-helper HIGH risk and combined CRITICAL graph risk are explicit.
The removal helper's code/API is unchanged; installers, CLI, bootstrap and
uninstall are its consumers. Graph commands use both isolated environment paths.
CLI output displays only a subset even with --limit 100; this is not a complete
graph proof. Receipts and remaining checks: .superpowers/sdd/PLAN/task-6-report.md.
No commits, push, native run or user-folder installation. Independent review is
next; native/Windows behavior, concurrent writers and process-death recovery are
not qualified. Dependency side effects are not rolled back.

## Task 6 review revision 1 — ledger permissions

Reproduced the independent review finding with record/log permissions 0600 and
an existing temporary record at 0640. Failure after completed ledger replacement
or log append widened the record mode and recreated the temporary file with the
wrong mode: four cases failed (copy/editable for each failure), nine passed.

Ledger snapshots now retain permission bits alongside bytes and restore both for
record, temporary record and log. No other transaction behavior changed. The
strengthened focused suite passes all 13 tests in 0.34s; targeted Ruff and
`git diff --check` pass. Evidence: task6-fix1-before.txt, task6-fix1-tests.txt and
task6-fix1-impact.txt in the task evidence folder. install_folder impact was
rechecked with both owned graph environment variables before the production edit.

Limit: removed/recreated deployment directories still use default permissions;
the tests compare directory membership, not custom directory modes. File modes
and ledger permission bits are covered; complete directory-mode preservation is
not claimed. No broad suite, native run, installation, commit or push was repeated.
Writer stopped for independent re-review.

## Task 6 review revision 2 — recreated directory permissions

The fix-1 directory-mode limitation is superseded: rollback now snapshots tracked
directory permission bits and reapplies them after restoring all descendants,
children before parents. Only directories absent immediately before restoration
receive chmod; surviving user-populated directories retain their modes without
being touched. There is no persistent ledger schema change or new abstraction.

Snapshot tests now compare directory modes as well as file modes, bytes, links
and membership. A tracked metadata directory is chmod 0700 before each failed
upgrade. Eight placement/ledger/temp/log cases failed before this fix (copy and
editable); the five other existing cases passed. Two further tests verify that
user-populated metadata directories survive unchanged and are not chmod'd.

Focused suite: 15 passed in 0.40s. Targeted Ruff and git diff --check pass.
Receipts: task6-fix2-before.txt, task6-fix2-tests.txt and task6-fix2-impact.txt.
The install_folder impact was refreshed before production edits using both owned
graph environment variables. Previous broader coverage is retained, not rerun.
No native calls, live installation, commits or pushes. Writer stopped for review.

## 2026-11-17 — Remote CLI target routing

Added optional lazy Remopy routing for env, package/extension install/list/remove
and venv. Short host calls discover facts, verify an owned nonce and invalidate
caches; providers run locally with explicit target facts. Extension manifest
rules, package sources, requirements and standard folders share the host version.
Existing local defaults remain compatible. Conflicting data overrides, foreign OS,
malformed facts and remote hooks refuse; timeout is not retried, and refresh
failure reports the already completed operation separately.

Baseline 270 passed. Full coverage run: 295 passed in 7.37s; complete changed
modules CLI 89%, dest 100%, env 91%, extension 93%, remote 97%. Focused remote
transport/nonce/target/timeout cases use fake Remopy and scratch files, including
an external provider delayed beyond five seconds. Native/Windows, remote hooks
and released installation remain unverified. Task evidence:
.superpowers/sdd/PLAN/task-7-report.md. No native calls, install, commit or push.

## 2026-11-17 — Standalone bootstrap and multi-extension ZIP

The root single-file installer and generated project installers share one packaged
stdlib bootstrap. A compatible validated wheel preserves real distribution
metadata, RECORD and licence. Stage before replacing the package and metadata;
restore previous paths and links when download, digest, placement or import fails.
Keep recovery bytes when restoration itself fails. Discover live Python version,
refuse escaping site-packages parents and leave source checkout links untouched.
Root self-install now installs a wheel; offline sibling source requires a built
wheel in dist. Existing explicit bootstrap project installation remains editable.
A .fontlabext stub has two executable lines and requires installed Instamix.
CLI pack accepts several existing extension folders; preflight every manifest,
identity and duplicate before staging a temporary ZIP and replacing its output.

Focused checks: 84 passed (0.49s). Full test.sh: 307 passed (6.67s).
Six selected regressions failed against an isolated HEAD preimage (0.11s),
recorded in .superpowers/sdd/PLAN/task-8-preimage-red.txt. git diff --check passed.
uv build produced genuine dev sdist and wheel-from-sdist. Isolated single-file
installation of that wheel proves matching module/distribution version, installed
origin, no mandatory dependencies, generated stub from installed resources,
byte-exact installed wheel members and source licence equality. Receipt:
../issue256-artifacts-task8-20261117/task8-artifacts.json.

Scoped pre-edit GitNexus impacts: make_zip, stub.write and cli.parser LOW/exact;
callers cmd_wrap/cmd_stub/main confirmed structurally. Existing aggregate graph
risk remains separately controller-owned; controller runs frozen graph analysis.
No native, Windows, publication or owner user-folder installation was performed.
Independent review and controller acceptance remain. See task-8-report.md.

## Review fix round 1 — frozen

Addressed both findings in task-8-review.md. make_zip now compares namespace
exactly while allowing mixed-case .fontlabext suffixes; duplicate detection stays
case-insensitive. Regression proves uppercase namespace refusal preserves prior
archive and a mixed-case suffix archive installs.

Added one small required_api check shared by installed-copy reuse and protected
new-wheel import: legacy module, callable gui.message, and callable
bootstrap.install_project for the project entry. Root entry does not require the
project API. Missing/non-callable APIs cause fallback for a reused copy; an
incomplete new wheel restores prior package and metadata before reporting failure.
All three generated template copies remain coherent. Fixture wheel now includes
the actual GUI API and a separate isolated interpreter executes the standalone
file's real entry block, including its success message. Reused project API
refusal and failed-wheel restoration have direct regression coverage.

Red: 2 failed, 14 passed (0.36s), task-8-fix1-red.txt. Focused final: 88 passed
(0.51s), comprising standalone/ZIP, parity and bootstrap CLI checks.
git diff --check passed. Previous full-suite 307 and built-artifact hashes bind
the initial round; these source/API changes have not been rebuilt into those
artifacts or rerun through a full suite. Controller/reviewer own final gates.

Pre-edit graph recheck make_zip LOW/exact. Template ensure is not indexed as
Python (.vfpy); unqualified ensure resolved unrelated uv.ensure, which was not
used as approval. Direct template callers are required_api/ensure and the final
standalone/project action; exact template equality and focused runtime checks
cover the generated consumers. No native, owner install or delivery attempted.

## 2026-11-17 — Draft plugin packaging and extension selection

`wrap.make_plugin` and CLI plugin options package five explicit kinds without
importing App or executing the draft. Six metadata fields and entry-module paths
are checked before output writes; existing plugin.json must agree and keeps its
bytes. Code, relative helper modules, stem and licence are copied unchanged into
canonical lowercase bundles. Stage on the output filesystem before publishing.
The outer manifest maps Extensions/<kind-folder> to that same target, because
the existing destination provider correctly refuses a bare Extensions root.
This preserves the inner parent inside Library and per-file symlink resolution.

Lazy PythonQt helpers now select multiple archives/manifests or one directory;
`install_selected` calls the public install API, prints each result/failure and
continues remaining selections. Cancellation is empty. Console paths are literal,
one per line. Existing message remains print-only. Local Echopy QtGui.pyi native
signatures at 60884/61003/61073 establish str/str/tuple respectively; supplemental
Qt C++ documents QString/QStringList. Exact bundled PythonQt converter source was
not found in the bounded Proteus source inspection. Mocks prove handling of flat
strings/sequences, cancellation and partial failures, not host dialog behavior.

Baseline: 312 passed (7.03s). New red checks: 21 plugin failures and eight picker
failures. Focused final: 32 passed (0.39s). Complete coverage run: 344 passed
(6.89s), ordinary macOS CPython 3.14.10; complete wrap 92%, CLI 93%, GUI 94%.
Targeted Ruff passes with only pre-existing Progress.__enter__ PYI034 excluded;
no new lint exclusions in source/config. git diff --check passes. Removed
unrelated formatter changes from existing wrap/CLI/Progress code.

Both GitNexus environment variables use issue256-features-graph task-owned home
and storage. Pre-edit parser LOW/exact; cmd_wrap and pick_file UNKNOWN because
registered callbacks/references have no indexed caller edges. Current source and
ast-grep confirmed cmd_wrap is registered by parser and dispatched by main;
pick_file had no consumers. Initial index reports truncated execution flows, so
absence is not coverage. Final refreshed change analysis is CRITICAL (17 symbols, 16 flows); independent
review/controller checks remain required. Receipts live in the sibling issue256-features-graph
folder; task-9-report.md records commands and limits. No native calls, user-folder
installation, commit, push, tag, dependency addition or App/Plugmix edit occurred.

### Task 9 review fix 1 — partial archive outcomes

Controller reproduced a multi-extension archive where the first extension commits
and the second collides with owner data. Added a real ZIP regression: it failed
because the original exception had no successful-record information. Archive
installation now annotates and re-raises that same exception with installed_records
for already committed extensions. GUI selection reports those successes alongside
the failed path and returns them; the existing owner file stays byte-exact.
This is not archive-wide rollback, and direct callers still receive the original
failure. No new exception class or installer mechanism was added.

Exact pre-edit extension.install graph impact: HIGH, four callers; its shared API,
CLI, bootstrap and GUI boundaries were considered. Focused extension + selection
checks: 45 passed (0.37s). Full affected-module coverage: 345 passed (6.70s),
wrap 92%, CLI 93%, GUI 94%, extension 93%. Targeted Ruff and diff checks pass.
Receipts: fix1-red.txt, fix1-install-exact.txt, fix1-full-coverage.txt and
fix1-detect.txt in issue256-features-graph. Independent re-review is next.
