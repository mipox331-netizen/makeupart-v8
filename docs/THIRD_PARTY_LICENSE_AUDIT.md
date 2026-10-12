# Third-party license audit

## Project code

The repository's original code and documentation are designated proprietary, with all rights reserved, by the root [LICENSE](../LICENSE). This is not an open-source grant and does not replace licenses shipped by dependencies. The notice also does not set end-user terms for the separate mobile app or hosted service.

## AI/model licensing fix

The deployed production image pipeline no longer downloads or loads the InsightFace `buffalo_l` pretrained weights. It uses MediaPipe landmarks and OpenCV image processing. MediaPipe is Apache-2.0 licensed and OpenCV 4.5.0+ is Apache-2.0 licensed; preserve applicable notices. The OpenCV structural-preservation score is not biometric identity recognition.

Production deployment confirming the replacement runtime: [GitHub Actions run 38257623154](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38257623154).

## Findings from the generated dependency inventory

The current inventory artifact `makeupart-third-party-license-inventory-38261976183` includes 68 Python package entries and 95 Flutter/Dart entries. The report is a record of package-provided license text, not a legal sign-off.

- The Python inventory identifies `certifi` as MPL 2.0. Keep its license notice with any applicable redistribution.
- Psycopg identifies `psycopg2` as LGPL with an OpenSSL linking exception. The backend dependency was changed from the binary wheel to `psycopg2==2.9.13`, built from source in the backend image, to avoid bundling a separate `libpq`/`libssl` set in the wheel. This does not remove the LGPL notice or its obligations; retain the upstream license text and review the production distribution model. The upstream project recommends source builds for production use ([license](https://www.psycopg.org/docs/license.html), [installation guidance](https://www.psycopg.org/docs/install.html)).
- Flutter SDK subpackages may refer to license text held at the SDK level rather than expose a separate `LICENSE` file. The revised report splits the Flutter engine's bundled SDK licenses so those component notices can be reviewed separately.

## Automated inventory

The [Third-party License Inventory workflow](../.github/workflows/third-party-license-inventory.yml) generates an artifact containing detected Python dependency licenses and notice texts, and Flutter/Dart dependency license information. It runs for pull requests, relevant dependency changes on `main`, and manual dispatches. Artifacts are retained for 30 days.

The inventory is intentionally not presented as automatic legal approval. Review unknown/ambiguous entries and the licenses of native Android/iOS libraries, operating-system packages, the Python container base image, and any separately supplied images/fonts/models. Re-run the workflow whenever dependencies or model assets change.

## Current decision and remaining gate

- The restricted InsightFace pretrained model was removed; the production replacement was deployed.
- The root repository notice now states that original project materials are proprietary.
- A completed and reviewed third-party inventory is still required before claiming the entire software bill of materials has been legally cleared for commercial distribution.
- No generative makeup model or generative provider is currently configured; do not advertise generative makeup as an available feature.

This document is an engineering record, not legal advice. Obtain qualified legal review before commercial distribution or when deciding whether to redistribute third-party components.
