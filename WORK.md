---
this_file: WORK.md
---

# Current work

## Latest verification

- Release housekeeping passed 547 arm64 Python 3.11 tests, 36 docs tests, workflow lint and two mocked publish checks. Wheel and sdist metadata and licence bytes matched the installed wheel.
- fly-january 0.2.1 (dfdcd5a) passed the strict Python 3.13 build and all 36 docs tests. All 27 versioned asset references match the generated files.
- Instamix 1.0.19 (b37a352) passed 547 arm64 Python 3.11 tests. The release workflow succeeded and the wheel and sdist hashes matched across GitHub and PyPI.
- Issue 271 shipped in 1.0.18 (0a90d01) and all 13 maintained consumers carry the reviewed stub in qualified releases.

Native acceptance remains open. Qualify the current installers and remote paths
only in the approved serialized lane. Consumer execution and owner-folder
recovery remain held. PLAN.md lists the remaining checks.
