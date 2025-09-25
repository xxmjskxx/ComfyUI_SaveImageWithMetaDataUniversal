# Future Ideas & Archived Prototypes

Central reference for deferred / speculative features and archived experimental UI elements. These are NOT implemented.

## Archived Prototype UI Components

### Metadata Rule Scanner JSON Editor (Archived)
Location: `ignore/web/disabled/metadata_rule_scanner/`

A prototype auto‑populated editable JSON textarea intended to live inside the `Metadata Rule Scanner` node UI. It was archived to:
- Reduce ongoing maintenance burden
- Avoid layout instability from large JSON blocks
- Encourage explicit external editing & version control of rules

Re‑enable Guidance (if ever adopted):
1. Revisit front‑end form rendering
2. Add size / collapse controls
3. Provide validation feedback pipeline to Python side

## Deferred / Future Feature Concepts

### Workflow Compression (Planned)
Goal: gzip + base64 encode full workflow JSON before embedding in EXIF (esp. for JPEG) while keeping existing staged fallback logic unchanged.
Status: Design placeholder only; not implemented.
Key Constraints:
- Must preserve current fallback staging semantics
- Add a marker key so downstream tooling recognizes compressed payloads
- No multi‑segment APPn splitting; single segment only

### Wan2.2 Support (planned)
Location: `docs/WAN22_SUPPORT.md`
- Add support for wan2.2 and other MoE multi-model workflows. 

### Possible Enhancements (Exploratory)
- Explicit metadata fallback stage key (separate from parameter string suffix)
- Optional sidecar `.json` with full metadata when JPEG hits `com-marker` stage
- Selective hash detail inclusion (per hash type toggles)
- UI affordance for minimal parameter allowlist preview
- Optional: CLIP model hashes for Wan encoders.
- Optional: Env flag to omit the structured block entirely.
- Placeholder: Workflow gzip+base64 pre-EXIF. Keep detection marker and reuse fallback strategy (not implemented).

### Multi‑Segment EXIF / Alternate Embedding
Currently ruled out to avoid complexity & fragile parser expectations. Consider only if compression proves insufficient.

## from https://github.com/alexopus/ComfyUI-Image-Saver

### Easy-Remix
Strip LoRAs and simplify 'embedding:path' from the prompt to make the Remix option on civitai.com more seamless.

### Additional Hashes
- User input for hashes separated by commas, optionally with names. 'Name:HASH' (e.g., 'MyLoRA:FF735FF83F98')
- With download_civitai_data set to true, weights can be added as well. (e.g., 'HASH:Weight', 'Name:HASH:Weight')

## Contribution Guidance For Future Ideas
If implementing any item here:
1. Open an issue referencing this document section.
2. Keep diffs minimal; preserve ordering & fallback semantics.
3. Update this file + README links + `.github/copilot-instructions.md` if behavior surfaces to users or AI assistants.

---
Last updated: v1.1.0
