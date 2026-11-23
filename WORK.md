---
this_file: WORK.md
---

# Issue 256 implementation review

## 2026-11-23 — Documentation theme

The strict Python 3.13 build now uses fly-january 0.1.1 with FontLab chrome.
All nine generated HTML pages contain one Instamix menu, one FontLab footer
and three versioned Fly asset references. The asset manifest verifies 14
retained files and the removal of 35 unused search helpers. All 36 docs tests
and 547 arm64 Python 3.11 runtime tests passed.

## 2026-11-19 — Remote setup before installation

Remote CLI validation checks the supported command and hook options before
loading Remopy. The dispatcher checks the installed release, resolves the bridge
with Remopy's public discovery function and calls `ensure_ready` before opening
the client. Remopy 2.0.12 exports that helper but probes before the setup script.
The 2.0.13 minimum protects the script-first contract. Numbered local builds
are accepted. Prereleases, development builds and unknown versions are refused.
No mandatory dependency changed.

The selected bridge determines which FontLab app receives the setup script.
On macOS, a bundled bridge identifies its app after resolving symlinks.
On Windows, the adjacent FontLab executable is used when present. An external
wrapper uses the default app, with a user Applications fallback on macOS.

Setup timeout reports include any Remopy notes naming the retained setup files.
The CLI exits before the remote environment probe or any local install work.
Existing host fact validation, shared nonce checks and completed-install reporting
after a cache-refresh failure remain in use.

Baseline 528 tests passed in 7.97s. The first readiness regressions exposed nine
failures. All seven application-selection cases first failed against the
original review candidate and then passed. The complete source passed
547 tests in 9.28s on arm64 Python 3.11.14, with 97.76% combined statement/branch
coverage for the complete changed module
(80% gate). Scoped Ruff and whitespace checks passed. Strict docs and 36 docs
tests passed using the existing 31 locked packages. Candidate wheel and sdist
built successfully. Scratch wheel installation verified the license, RECORD,
local CLI and optional dependency, including installation of Remopy 2.0.13.

Pre-edit graph impact for `execute` is LOW and identifies `cli.main` as its only
direct caller. Structural search confirms that caller. Reindexed change analysis
is LOW with zero mapped flows. The analyzer reports 120 untraced entry points,
so its flow coverage is incomplete.

Source is ready for independent review and delivery. End-to-end native
qualification needs a FontLab bridge that can return the MCP catalogue.

## 2026-11-18 — Issue 271 installer conflicts and local wheels

Modern receipt conflicts are checked before tracked project files or sibling
dependencies change. A link replaced by a directory, edited copied file or
unrecorded package content is preserved and reported with backup-and-retry
instructions. Existing case-only plugin parent aliases remain supported.
First-install conflicts can still follow committed sibling installs; recursive
errors retain those records. CLI and regenerated installer stubs report partial
results and failures, with missing requirements labelled incomplete. APIs still
raise and CLI failures remain nonzero. New stubs require the conflict preflight
capability before reusing an installed provider.

Bootstrap deduplicates resolved local wheel paths (including the self-installer's
double lookup), chooses the newest eligible numeric project version, refuses
conflicting bytes at the selected version and checks filename/metadata agreement.
Existing extraction safety, SHA-256 checks and failed-upgrade restoration remain.
Wheel ordering covers this project's three-part releases and dev/a/b/rc/post/local
suffixes; unsupported forms fail with instructions. No dependency was added.

Validation: baseline 481 tests passed; 11 of the first 12 new regressions failed
before implementation. Final combined source: 528 arm64 Python 3.11 tests passed
in 9.60 seconds, with 90.94% combined statement/branch coverage across complete
bootstrap/extension/cli/gui modules (80% gate retained). Scoped lint, strict docs
build and 36 docs tests passed; final wheel and sdist builds passed. Independent
read-only review approved the combined diff against 60c9c80 and independently
passed 179 focused tests in 0.90 seconds. Temporary fake-provider files trigger
coverage source warnings; the actual complete modules are reported separately.

Fresh upstream main is 60c9c80; its release/build changes are preserved in the
integration successor. Reindexed graph change analysis reports 23 symbols and
34 affected flows, critical risk. Analyzer process extraction remains truncated
after rerun (120 untraced entries, 11 dropped processes); this is incomplete graph
evidence, supplemented by structural caller checks and independent review, not
an all-clear. Task-owned graph registries remain isolated. Evidence is retained
under the controller's Issue 271 data folder.

No native or owner-folder operation ran; the required serialized guard is absent.
Release/distribution and consumer stub propagation remain follow-ups.


## 2026-11-17 — Remopy release qualification

Remopy 2.0.7 includes the Wine/CrossOver providers and CLI routing in its
reviewed GitHub release. Runtime execution, remote hooks and native Windows
bootstrap remain unverified. Remopy PyPI publication failed with
invalid-publisher; publisher administration and any admitted retry remain open.
No owner-recovery or consumer-execution hold is lifted.

## 2026-11-17 — Existing shared-package venvs

A compatible environment whose site-packages resolves exactly to the canonical
package directory can now be reused without creating a redundant managed path
file or directories. Runtime version, implementation, platform, architecture and
prefix checks remain mandatory. Other escaping paths and unrelated managed path
files are still refused. The read-only runtime probe disables bytecode writes.

Four canonical-layout regressions failed first; nine mismatch/preservation cases
already passed. All 425 arm64 Python 3.11 tests pass in 8.70 seconds, with 96.49%
statement coverage for the complete venv module. The controller subsequently
qualified 21 focused tests in 4.37 seconds with 94.52% combined statement/branch
coverage for the whole module (55/57 statements and 14/16 branches). An actual offline uv-created environment,
then linked to its canonical site-packages, preserves its files, links and path
files while probing and importing. Scoped lint and wheel/sdist builds pass. The locked strict docs build and
all 36 docs tests pass (10.603 seconds), preserving the exact installer asset.
This is source qualification on owned scratch data. Owner-folder recovery and
consumer execution remain held; no existing installation is converted or repaired.
Independent source review passed. Controller reindexing now includes probe,
create and the new tests: 16 changed symbols across 11 files, one affected
cmd_pkg_install flow, MEDIUM risk. This supersedes the earlier omitted-symbol
summary; index extraction caps and the initial metadata-census limit remain.
Task 20 integration, exact-SHA CI/release and native/Windows checks remain open.

## 2026-11-17 — Installer entry context

All three standalone installer copies check the existing read-only site context
before bootstrapping, including when a ready provider is reused. External entry
execution without FontLab or FONTLAB_DATA_DIR now refuses before deployment.
The import sentinel remains side-effect free; explicit data-folder and host
preference contexts retain their behavior. CLI and direct API defaults are unchanged.

Twelve fake-provider cases cover all copies, including blocked deployment before
removing the test data override. The three missing-context cases fail before the
fix. All 411 arm64 Python 3.11 tests pass in 7.70 seconds; compile, template
parity and scoped lint checks pass. No real provider, installer deployment or
native host is executed by these
new regressions. Independent release review qualifies the guard in published
1.0.10 at 5b875f0dc41ab404cfda92b127186f1896f540b3, with successful exact-SHA
release/docs/Pages runs and matching GitHub/PyPI artifacts.
Consumer execution and owner-folder recovery remain held pending their existing
incident review; this source guard does not repair or prove prior folder state.

## 2026-11-17 — Public standalone installer download

The existing strict docs build now publishes the exact root install.vfpy as a
static download. The homepage and README link to its canonical public URL and
the homepage links the project licence. Only that exact root asset is allowed
through the source-download test; all other script and private-payload bans
remain intact. Reproducible builds now include the installer in their full-file
hash comparison.

The new missing-asset regression failed first, then 36 docs tests passed in
5.064 seconds. Full arm64 Python 3.11 source checks passed 399 tests in 11.51
seconds with an explicit owned scratch data root. Runtime modules and installer
bytes were unchanged in that increment. Independent 1.0.10 review now qualifies
the delivered download: HTTP 200, 7143 bytes, matching the released canonical
installer SHA256 5e7b64584ddfef9e276add3d465343c641b91c29840db34967735d4d00ab643e.
API/book guide delivery retains its own gates.

## 2026-11-17 — Failed legacy upgrade preservation

A legacy project upgrade now keeps a private snapshot of its affected targets,
shared tools, metadata and receipts until replacement succeeds. Installation,
requirements, ledger, startup or launcher failure restores the prior bytes,
links, modes and ownership state. Rollback failure retains recovery files and
adds their location to the exception. External package-manager effects remain
outside this file-deployment transaction; nonempty dependency folders are kept.
A rolled-back project is removed from partial-success reports, preserving other
completed records. Existing extension/ZIP partial-success behavior is unchanged.

The common bootstrap requires this private rollback capability before reusing
or accepting a provider. Published 1.0.8 lacks it and is replaced; failure to
obtain a safe replacement preserves the prior provider and prevents deployment.
The 1.0.8 release has a known legacy-upgrade defect: an unowned conflict can
leave other old files removed. Do not use that version for legacy migration.

Verified 399 arm64 Python 3.11 tests in 8.84 seconds; complete changed module
bootstrap.py has 91% combined coverage. Six real historical-installer scenarios
pass against an ordinary candidate-wheel prefix with whole-tree failure
oracles, preserving 234 Examples or 224 Scriptmix entries on refusal. Actual
published 1.0.8 rejection, failed-fetch preservation and candidate-wheel
replacement pass. Independent release review qualifies published 1.0.9 at
c676c7cad2f87556edacd98c6da6b000f9dfbfe0, its GitHub/PyPI artifact identity and
all six released-wheel legacy-preservation fixtures. Updated consumer-stub
readiness/delivery, native and Windows qualification remain separate.


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


## 2026-11-17 — Safe managed plugin suffix migration (Task 11)

Added one extension.preflight_plugin_migration helper before managed installation
writes and before project dependency/legacy operations. It examines only planned
canonical bundles and their same-name title-case counterparts in the five plugin
kinds. Actual directory entries and samefile distinguish filesystem aliases.
Distinct legacy trees must be completely unchanged and owned by the prior receipt;
otherwise installation refuses with InstallError, preserving files and receipt.
Existing removal handles unchanged copies and editable links without new cleanup.

All three shipped bootstrap copies require that actual callable helper, checking
both reused imports and newly installed wheel APIs inside the existing rollback
transaction. Plugmix's isolated consumer now uses the shared canonical template.
Its obsolete header/80-line assertion became canonical parity plus readiness.
Fixture wheels/parity mocks now provide the actual required interface.

Baseline: 345 passed (6.95s). The real retained 64MB case-sensitive HFS+ fixture
reproduced 21 failures/3 passes before the fix. Expanded focused tests: 30 passed
(1.50s). Full ordinary CPython 3.14 suite: 378 passed (7.20s), both complete
changed modules 92%. Full actual arm64 Python 3.11.14 on HFS+: 378 passed
(10.67s), bootstrap 92%, extension 93%. Coverage also warns about temporary
fixture modules removed by rollback; the production module counts are intact.
The original App-discovery reproduction now keeps one bundle per scenario:
unchanged upgrades; modified/unowned refuse, retaining old receipt entries.

A genuine downloaded SHA-verified PyPI 1.0.7 wheel failed required readiness. An
injected offline replacement failure preserved its usable prior package and
metadata, then the genuine hatch-vcs built current wheel replaced it successfully
in scratch storage. No version override, source fallback or user-folder install.
Evidence: the controller-owned issue256-migration-graph directory contains
red/focused/full logs, migration.json, genuine-wheels.json and executable probes.

Pre-edit install_folder impact HIGH through API/CLI/GUI/bootstrap callers; project
impact LOW. Template required_api UNKNOWN (.vfpy is absent from the graph),
confirmed by direct source and tests. Combined graph HIGH, 7 files/6 symbols/14
processes; it omits untracked tests/new helper and has analyzer flow-budget limits.
Both graph home/storage were task-owned from first invocation; exclude bytes
unchanged. No global registry/MCP use. No commit, push, tag, FontLab call or
user-folder installation. Independent review and release/native/Windows gates
remain open. The genuine built development version remains below release 1.0.7;
release version selection is the controller's separate delivery gate.

Final refreshed graph includes the new helper: its upstream impact is HIGH;
combined detect-changes is CRITICAL (12 files, 19 symbols, 19 processes), including
progress-document changes. Analyzer flow-budget omissions and .vfpy indexing
limits remain explicit; no graph closure claim. Task-owned excludes still match.
Plugmix consumer focused 3 tests and full prepared source suite 459 tests pass
(5.63s); its unchanged complete-module check_coverage.py coverage.json passes.
The final exact resolver runner remains held on genuine App 1.2.31, as Task 10
records. Targeted lint and Instamix diff check pass. Plugmix's two touched files
pass diff check; prior task's seven Markdown hard-line-break whitespace findings
remain untouched. The HFS+ fixture image is retained and disk17 was gracefully
detached after all tests/probes completed. Writer frozen for independent review.
