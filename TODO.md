---
this_file: TODO.md
---
# Remaining Issue 256 work

- [ ] Verify the implemented remote CLI against live FontLab: nonce, owned package, standalone and embedded imports; qualify Windows runtime separately.
- [ ] Implement CrossOver/Wine execution and remote hook submission; ordinary same-OS remote CLI is implemented with offline regression evidence.
- [ ] Qualify native PythonQt multi-file and folder selection in the serialized FontLab lane; static declarations and offline return-value tests pass.
- [ ] Reconcile consumer installers and environment helpers, then verify macOS/native and Windows/CrossOver workflows.
- [ ] Independently review and integrate verified changes through repository gates; retain unverified native/release outcomes.

- [ ] Independently review generated-file rollback and qualify it on native/Windows installations; offline failure recovery passes.
- [ ] Verify generated lowercase plugin bundles through the paired compatible App loader; packaging and copied/linked ZIP installation pass offline.

- [ ] Independently review Task 11 managed plugin refusal/bootstrap readiness, reconcile the Plugmix consumer, and qualify release/native/Windows installation separately.
