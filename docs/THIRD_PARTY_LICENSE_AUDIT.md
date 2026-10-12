# Third-party license audit

## Project code

The repository's original code and documentation are designated proprietary, with all rights reserved, by the root [LICENSE](../LICENSE). This is not an open-source grant and does not replace licenses shipped by dependencies. The notice also does not set end-user terms for the separate mobile app or hosted service.

## AI/model licensing fix

The deployed production image pipeline no longer downloads or loads the InsightFace `buffalo_l` pretrained weights. It uses MediaPipe landmarks and OpenCV image processing. MediaPipe is Apache-2.0 licensed and OpenCV 4.5.0+ is Apache-2.0 licensed; preserve applicable notices. The OpenCV structural-preservation score is not biometric identity recognition.

Production deployment confirming the replacement runtime: [GitHub Actions run 38257623154](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38257623154).

## Automated inventory

The [Third-party License Inventory workflow](../.github/workflows/third-party-license-inventory.yml) generates an artifact containing detected Python dependency licenses and notice texts, and Flutter/Dart dependency license information. It runs for pull requests, relevant dependency changes on `main`, and manual dispatches. Artifacts are retained for 30 days.

The inventory is intentionally not presented as automatic legal approval. Review unknown/ambiguous entries and the licenses of native Android/iOS libraries, operating-system packages, the Python container base image, and any separately supplied images/fonts/models. Re-run the workflow whenever dependencies or model assets change.

## Current decision and remaining gate

- The restricted InsightFace pretrained model was removed; the production replacement was deployed.
- The root repository notice now states that original project materials are proprietary.
- A completed and reviewed third-party inventory is still required before claiming the entire software bill of materials has been legally cleared for commercial distribution.
- No generative makeup model or generative provider is currently configured; do not advertise generative makeup as an available feature.

This document is an engineering record, not legal advice. Obtain qualified legal review before commercial distribution or when deciding whether to redistribute third-party components.
