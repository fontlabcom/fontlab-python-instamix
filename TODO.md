---
this_file: TODO.md
---

# Remaining Issue 256 work

- [ ] Integrate and release the independently reviewed exact-canonical shared site-packages reuse; keep owner recovery and consumer execution held, and qualify native/Windows behavior separately.

- [ ] Qualify regenerated consumer templates against the released 1.0.10 entry-context guard without lifting the existing execution or owner-recovery holds.

- [ ] Qualify API/book download-link delivery through its normal gates; released 1.0.10 installer HTTP bytes are independently verified.

- [ ] Qualify updated consumer stubs before rollout; independent 1.0.9 release review and all six released-wheel whole-tree legacy-preservation fixtures pass.

- [ ] Verify the implemented remote CLI against live FontLab: nonce, owned package, standalone and embedded imports; qualify Windows runtime separately.
- [ ] Qualify the Wine/CrossOver providers and CLI routing released on GitHub in Remopy 2.0.7; verify runtime execution and remote hook submission. Resolve the separate Remopy PyPI publisher failure before claiming PyPI delivery.
- [ ] Qualify native PythonQt multi-file and folder selection in the serialized FontLab lane; static declarations and offline return-value tests pass.
- [ ] Reconcile consumer installers and environment helpers, then verify macOS/native and Windows/CrossOver workflows.
- [ ] Independently review and integrate verified changes through repository gates; retain unverified native/release outcomes.

- [ ] Qualify generated-file rollback on native/Windows installations; independent 1.0.9 review and released-wheel offline failure recovery pass.
- [ ] Verify generated lowercase plugin bundles through the paired compatible App loader; packaging and copied/linked ZIP installation pass offline.

- [ ] Reconcile the Plugmix consumer with released managed-plugin refusal/bootstrap readiness, retain its separate PyPI publisher gate, and qualify native/Windows installation.
- [ ] Detect a Windows venv whose `pyvenv.cfg` home sits on a uv minor-version junction and recreate it (Issue 259).
- [ ] `stub_install.vfpy` `ensure()`: require a minimum instamix version (≥ 1.0.13) and upgrade from PyPI when older; today any importable instamix is accepted, so Windows users on 1.0.12 or earlier keep the uv (os error 448) and reinstall (`__pycache__`) failures until they run instamix's own installer (Issue 259).
- [ ] Let instamix's own `install.vfpy` (`SELF_INSTALL`) install from the checkout it runs from instead of PyPI latest; today a checkout test silently installs the released version (Issue 259, F7).
