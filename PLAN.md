---
this_file: fontlab-python-instamix/PLAN.md
---

# fontlab-python-instamix plan (issue 256)

Native checks require the approved serialized guard and owned fixtures. The
consumer execution and owner-folder recovery holds remain in force.

- **Qualify the released Issue 271 installer and updated consumer stubs on macOS and Windows in the admitted native lane.**
  Use an owned FontLab data folder and the approved serialized guard. Confirm the installed provider version, repeat self-install with both 1.0.17 and 1.0.18 wheels available, and check that a modified destination and its receipt survive refusal. Exercise the current consumer stubs in the compatible cohort after the consumer-execution hold is lifted.

- **Qualify exact-canonical shared site-packages reuse in FontLab on macOS and Windows.**
  In an owned environment whose site-packages resolves to the canonical path, verify venv reuse and imports from standalone and embedded Python. Check that the operation preserves the existing links, files and path configuration.

- **Qualify the script-first remote CLI against live FontLab on macOS and Windows.**
  Require a bridge that can return the catalogue and Remopy 2.0.13 or later. Check setup preferences before the probe, host facts, nonce access, and an owned package install. Verify post-install cache refresh and imports through both Python entry points.

- **Qualify Wine/CrossOver provider execution and remote hook submission.**
  Verify routing in an owned bottle using the published Remopy provider. Retain unresolved submission receipts and verify their state before considering any replay.

- **Qualify native PythonQt multi-file and folder selection.**
  In the serialized lane, check the native return values for multiple files, one folder and cancellation.

- **Verify App and Instamix environment routing in the maintained consumer cohort on macOS and Windows/CrossOver.**
  Check that App's native path and version attributes and Instamix's target/site API lead consumers to the intended data folder and interpreter.

- **Qualify generated-file rollback on native macOS and Windows installations.**
  In owned scratch data, induce a failed replacement and compare prior files, modes and receipt against the restored result.

- **Verify that the paired App loader discovers generated lowercase plugin bundles and that Plugmix installs on macOS and Windows.**
  Use a host that naturally loads a compatible App and Plugmix cohort. Verify managed-plugin refusal and bootstrap readiness in an owned folder before checking discovery.

- **Verify Issue 259 junction repair in FontLab 9 for Windows.**
  Use an owned existing venv whose home points to a uv minor-version junction. Verify in-place repair and imports of packages already installed in that venv.

- **Verify Issue 259's 1.0.13 minimum and released-stub upgrade in FontLab 9 for Windows.**
  Start with an owned 1.0.12 installation. Verify that the released stub upgrades it and that the expected provider imports before installing the project.
