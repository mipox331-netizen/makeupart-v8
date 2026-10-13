# AI capabilities, provider setup and third-party model licensing

## Available processing engines

### Classic enhancement (works without an external AI key)

- MediaPipe locates exactly one face and supplies landmarks.
- OpenCV estimates skin tone and undertone.
- A bounded bilateral filter smooths skin, while a structural-similarity metric checks that this deterministic edit stays within the configured threshold.
- Face-mesh-aware local effects apply lipstick tint, cheek blush, upper-eyelid eyeshadow and a style-dependent eyeliner/wing in the existing natural, soft-glam, bridal-rose and evening-glam presets.
- These are deterministic, local OpenCV effects, not a diffusion model or FaceApp-equivalent generative makeup transfer; they run without a paid API key and do not upload the photo to an external image provider.
- The mobile app supplies five local photo finishes, a draggable Before/After comparison and salon watermarking.

The structure-preservation value is not biometric identity recognition and does not prove a generated image is the same person.

### Generative makeup and hairstyle (optional; requires a paid provider account)

The repository now includes an optional server-side image-edit provider using the OpenAI Images API `POST /v1/images/edits` and a configured GPT Image model. It attempts natural/soft/full glam, bridal glam, smokey eye, cat eye, eyeshadow, eyeliner, lipstick, blush, foundation, editorial looks and hairstyle variations (sleek hair, curls, braids, and elegant updo).

The model is instructed to preserve face shape, complexion, expression, clothing and background while editing only the requested cosmetics or hairstyle. This is a prompt-level constraint, not an identity guarantee; generative image models can still change facial details or other parts of the image. Each generated result must be reviewed before it is treated as a real-world reference.

The engine remains disabled when `OPENAI_API_KEY` is empty. To enable it in production, add a protected GitHub Actions environment/repository secret named `OPENAI_API_KEY` and run the **MakeupArt V8 Modal Production Deploy** workflow. The workflow provisions it into the Modal production secret without printing it. Never place this key in Flutter, source control, issue comments or chat. Model and quality defaults are `gpt-image-2.5-sunburst` and `medium`; operators can change `OPENAI_IMAGE_MODEL` and `OPENAI_IMAGE_QUALITY` server-side.

Generative editing has third-party usage costs and extra latency. Every successful run consumes the existing salon AI quota. Do not advertise unlimited free generation; review provider usage and set spend controls.

## Open-source generative-model assessment for a $0 budget

The model candidates were reviewed for both usage terms and the current production runtime. None is enabled or bundled by this change:

- [Stable-Makeup](https://github.com/Xiaojiu-z/Stable-Makeup) declares Apache-2.0 for its repository code and publishes inference code, but its README points to separately downloaded Google Drive checkpoints without clearly stating separate checkpoint terms. It is built on Stable Diffusion v1.5 plus SPIGA/facelib dependencies. Treat the weights and dependency licenses as unverified until their specific terms are confirmed.
- [SHMT](https://github.com/Snowfallingplum/SHMT) publishes code and checkpoints under CC BY-NC-SA 4.0, which is unsuitable for a commercial product without additional permission. Its documented inference command requires CUDA.
- [MagicMakeup](https://github.com/vivoCameraResearch/Magic-Makeup) documents FLUX.1-Kontext-dev as its base model and says it is intended solely for non-commercial academic research; its checkpoint/base-model access and terms are additional gates.
- [MAD](https://github.com/basiclab/MAD) provides makeup-transfer code and documents a CUDA-tested environment, but the repository's top-level files do not provide a clear license grant that would support commercial redistribution.

The production Modal image currently provisions a CPU-oriented 2-CPU/4-GB service and does not include PyTorch/diffusers model weights. Adding a large diffusion checkpoint would not make inference free: the model still needs compute, memory, storage and a license that permits the intended use. No provider API or external endpoint has been added, and OpenAI remains optional and unchanged.

**Decision:** preserve the $0 no-provider path and extend the existing MediaPipe/OpenCV Classic effects instead. A true reference-image makeup-transfer model is deferred until the checkpoint's commercial terms and a sustainable inference target are verified. The new eye effects are covered by synthetic unit tests only; real-photo quality, skin-tone fairness and edge cases still need a consenting portrait test set before describing them as FaceApp-level.

## Customer privacy and consent

The app requires the existing client/operator processing consent and a distinct confirmation before a photo is sent to an external generative provider. The server rejects generative requests without both confirmations. Classic image enhancement does not send the image to OpenAI. Provider credentials remain server-side, and provider failures are sanitized so credentials and raw portraits are not written to logs.

OpenAI states that API inputs and outputs are not used to improve models by default unless the API organization opts into data sharing; this does not mean zero retention. Salons must disclose external processing to clients and configure provider-account data controls according to their retention requirements. See the [OpenAI API data-use policy](https://help.openai.com/en/articles/10306912-sharing-feedback-evaluation-and-fine-tuning-data-and-api-inputs-and-outputs-with-openai).

## Third-party and commercial licensing

Official API references:
- [OpenAI Images API — edit an image](https://developers.openai.com/api/reference/resources/images/methods/edit)
- [OpenAI image generation guide and model/cost guidance](https://developers.openai.com/api/docs/guides/image-generation)
- [MediaPipe license](https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE) — Apache 2.0.
- [OpenCV license](https://opencv.org/license/) — Apache 2.0 for OpenCV 4.5.0 and newer.

The repository removes InsightFace's pretrained `buffalo_l` weights because published default terms restrict those weights to non-commercial research. Full commercial release still requires a transitive dependency, native SDK and bundled-assets license audit.

## Remaining release gates

The provider integration and mocked tests do not prove live image quality. Before enabling it for customers, configure the API key, run controlled end-to-end tests using consenting test portraits across skin tones and lighting, review face/hair/background preservation, and set provider spend controls. Google Play publication, signed iOS/App Store distribution, real production-row restore testing and a complete commercial license review remain separate gates.
