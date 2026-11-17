---
this_file: TODO.md
---
# Remaining Issue 256 work

- [ ] Verify the implemented remote CLI against live FontLab: nonce, owned package, standalone and embedded imports; qualify Windows runtime separately.
- [ ] Implement CrossOver/Wine execution and remote hook submission; ordinary same-OS remote CLI is implemented with offline regression evidence.
- [ ] Complete picker support for manifests and multiple archives, and verify native PythonQt behavior.
- [ ] Reconcile consumer installers and environment helpers, then verify macOS/native and Windows/CrossOver workflows.
- [ ] Independently review and integrate verified changes through repository gates; retain unverified native/release outcomes.

- [ ] Independently review generated-file rollback and qualify it on native/Windows installations; offline failure recovery passes.
- [ ] Complete draft plugin wrapping with the supported plugin bundle structure and installable artifacts.
