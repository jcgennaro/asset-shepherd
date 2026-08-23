# Asset Shepherd Real-World Validation and Thematic Benchmark Plan

**Document type:** Approved project-contract addendum  
**Applies to repository:** `jcgennaro/asset-shepherd`  
**Primary owner:** Codex, working directly on `main`  
**Human dependencies:** Tripo generation, visual adjudication, and any manual Blender or Unreal actions that cannot be automated safely  
**Document version:** 1.0  

---

## 1. Authority and relationship to the project contract

This document extends `docs/PROJECT_CONTRACT.md`. It does not replace the existing MVP, repair-safety model, deterministic verification rules, GLB-only product scope, or direct-to-`main` workflow.

Its purpose is to replace synthetic-only product validation with a layered evaluation program using realistic textured assets, controlled mutations of those assets, and an actual Blender-to-Unreal production pass.

D036 changes the product's decision architecture without changing this corpus or downstream evidence
program. Real-world runs must now freeze the agent's sensor choices, assessments, disposition, and
typed action requests in addition to deterministic observations and results. Legacy deterministic
plans remain historical benchmark evidence, not the target product behavior.

Use this priority order when instructions conflict:

1. A direct current instruction from the user.
2. This addendum for corpus creation, real-world validation, and demo-asset strategy.
3. `docs/PROJECT_CONTRACT.md`.
4. `docs/PROJECT_STATUS.md` and approved decision records.
5. Existing implementation details.

Codex must not weaken an existing safety invariant merely to improve benchmark results. The correct response to an unsupported real-world asset is a precise `BLOCKED` or `REPORT_ONLY` result, not a bold act of file vandalism presented as autonomy.

---

## 2. Why this addendum exists

The deterministic synthetic robot remains valuable. It establishes exact ground truth and has already demonstrated the following:

- The original source remains unchanged.
- The repaired candidate is a valid GLB 2.0 file.
- Independent reload and reinspection work.
- Geometry and resource-count invariants are checked.
- Naming repairs work.
- Approved scale, orientation, and grounding normalization works.
- Executed actions are represented in provenance.
- A second planning pass proposes no additional version-1 repair.

However, the current fixture is intentionally simple and contains no textures. It proves plumbing, authorization, provenance, and core transform mathematics. It does not adequately stress:

- Real PBR materials and embedded textures.
- Generative-model topology and hierarchy.
- Unknown defects that were not encoded by the fixture author.
- Transparent, emissive, alpha-masked, or normal-mapped surfaces.
- Blender import and re-export behavior.
- Unreal Interchange import behavior.
- Visual preservation after repair.
- Real technical-artist time savings.

Synthetic fixtures therefore remain the regression foundation, but they are not sufficient evidence for the product claim or final demo.

---

## 3. Real-world validation thesis

Asset Shepherd should be evaluated on four layers:

| Layer | Purpose | Ground truth |
|---|---|---|
| Synthetic microfixtures | Fast deterministic regression and exact invariants | Fully known before execution |
| Raw Tripo exports | Discover unanticipated real-world failures | Established after blind prediction and human adjudication |
| Controlled mutations of realistic assets | Real complexity with precise known defects | Known from mutation manifest |
| Blender-to-Unreal acceptance | Determine whether the output is actually useful in the user's production path | Unreal import evidence plus human-cleaned reference |

No single layer replaces the others.

A raw asset can reveal problems we did not imagine, but it lacks perfect ground truth. A controlled mutation has ground truth, but it may not represent naturally occurring failure distributions. Unreal acceptance reveals downstream usefulness, but not every structural cause. The layered program prevents us from flattering ourselves with whichever test happens to be easiest.

---

## 4. Hackathon iconography and original mascot decision

### 4.1 Research conclusion

The public Agents for Humans materials do not present a named official mascot or a distinctive creature that should be reproduced. The visible identity is primarily the event name, AWS sponsor branding, Devpost hosting, the Strands Agents SDK, and the theme of autonomous helpers that quietly handle repetitive work and surface only for consequential decisions.

The benchmark corpus and demo should therefore use original Asset Shepherd iconography rather than copying AWS, Devpost, or Strands logos.

### 4.2 Trademark and presentation rule

Do not place any of the following inside generated 3D assets:

- AWS wordmark or smile mark.
- Devpost wordmark or icon.
- Strands Agents logo.
- Event title rendered as model text.
- Third-party game logos, characters, or recognizable franchise designs.

Official names may appear in ordinary submission text where appropriate. The assets themselves must remain original and independently brandable.

### 4.3 Original visual motifs

Use these nonexclusive motifs:

- A quiet helper or courier rather than a heroic combat robot.
- A shepherd's crook interpreted as a repair wrench or diagnostic staff.
- Braided cables as a visual nod to “strands.”
- A literal wayfinding post as a subtle nod to “Devpost,” without copying its logo.
- Clouds, parcels, tools, lanterns, and workshop objects as general background-agent imagery.
- Warm amber, cloud blue, cream, charcoal, and muted teal as an original palette, not an exact reproduction of sponsor branding.

---

## 5. Canonical benchmark mascot: Patchling

### 5.1 Concept

**Patchling** is Asset Shepherd's Benchy-like canonical test asset: a small whimsical game-development courier automaton that carries a wayfinding post and a repair satchel.

Patchling should become:

- The recognizable benchmark model.
- The principal real-world validation asset.
- A possible Asset Shepherd UI mascot.
- The hero asset in the Devpost demo.

### 5.2 Visual design

Patchling is a friendly, compact shepherd-and-courier robot with:

- A clearly readable face and front direction.
- Two stable feet or four compact feet with unambiguous ground contact.
- A braided cable tail or scarf.
- One asymmetrical tool satchel.
- A crook-shaped repair wrench.
- A small geometric wayfinding post mounted to its pack.
- One warm emissive diagnostic eye or chest light.
- One glass or translucent visor component.
- Painted metal, rubber, cloth, and glass materials.
- No text, lettering, logos, weapons, or detached floating props.

The design should be cute enough to remember but mechanically specific enough to expose import failures. It should look like a game asset, not a calibration appliance designed by a committee that dislikes joy.

### 5.3 Technical target

The selected Patchling candidate should ideally have:

- A represented height between 0.9 and 1.5 meters after human adjudication.
- A clear Y-up orientation in compliant GLB form.
- A clear forward direction.
- An asymmetric silhouette.
- 20,000 to 100,000 triangles before any manual optimization.
- Four to eight materially distinct surfaces.
- At least one base-color texture.
- Preferably normal and metallic-roughness information.
- Preferably emissive content.
- Preferably one transparent or alpha-masked material.
- Embedded GLB resources.
- No skin, animation, or morph targets for the MVP corpus.

These are selection preferences, not assumptions. The untouched Tripo export remains raw evidence even when it misses some targets.

---

## 6. The Asset Flock: thematic corpus

Patchling is the canonical asset. The broader corpus is called **The Asset Flock**. Each asset should inhabit the same whimsical fantasy-technology workshop world while stressing a different import concern.

### 6.1 Minimum corpus

Generate at least four raw Tripo assets:

| Asset | Role | Primary stress dimensions |
|---|---|---|
| Patchling Courier | Canonical mascot | Mixed materials, clear orientation, asymmetry, hierarchy, emissive/transparent details |
| Shader Lantern | Small prop | Glass, alpha/transparency, emissive surfaces, thin cage geometry, grounding |
| Debug Beetle | Creature-mechanical hybrid | Organic topology, mirrored limbs, normal-map fidelity, disconnected parts, orientation |
| Cloudforge Workbench | Environment prop | Realistic scale, many components, material count, hierarchy, repeated objects |

### 6.2 Stretch corpus

Add these only after the minimum corpus is functioning:

| Asset | Role | Primary stress dimensions |
|---|---|---|
| Strandwing Glider | Vehicle/drone prop | Strong forward direction, thin surfaces, asymmetry, pivot and bounding-box interpretation |
| Wayfinder Post | Environment marker | Grounding, pivot, hanging banner or alpha mask, modular pieces, clear scale |

### 6.3 Selection rule

Generate two or three Tripo candidates for each prompt. Select one based on:

- Strong silhouette.
- Useful PBR texture variety.
- Clear semantic orientation.
- Lack of obvious copyrighted resemblance.
- Static-mesh eligibility.
- Enough complexity to be realistic.
- Visual appeal in a five-minute demo.

Do not select only the cleanest exports. At least one corpus asset should be retained specifically because it exhibits a plausible natural failure.

---

## 7. Tripo generation protocol

### 7.1 Human responsibilities

The user performs Tripo generation and export because Codex does not control the user's Tripo account.

For each asset:

1. Use the approved prompt from Appendix A.
2. Generate two or three candidates.
3. Select one candidate using Section 6.3.
4. Export an untouched textured GLB.
5. Optionally export FBX for archival comparison, but do not treat FBX as supported Asset Shepherd input.
6. Do not open, re-export, scale, rename, or clean the GLB before raw ingestion.
7. Place the file at the requested repository-external or ignored corpus path.
8. Record generation settings and confirm that the output may be used publicly in the repository and demo.

### 7.2 Codex responsibilities

Codex must create a compact generation card before requesting human action. The card must state:

- Exact Tripo prompt.
- Number of candidates requested.
- Export format and options.
- Exact destination path.
- What not to inspect or modify before ingestion.
- Minimal provenance fields to record.

Codex should request one asset batch at a time, beginning with Patchling. It must not present the user with six simultaneous production chores merely because a table can contain six rows.

### 7.3 Required provenance

For every raw asset, record:

```json
{
  "asset_id": "patchling_01",
  "display_name": "Patchling Courier",
  "generator": "Tripo",
  "generation_date_utc": "",
  "prompt": "",
  "negative_prompt_or_constraints": "",
  "model_or_mode": "",
  "generation_settings": {},
  "selected_candidate_reason": "",
  "export_format": "glb",
  "export_settings": {},
  "raw_sha256": "",
  "public_use_confirmed": false,
  "notes": ""
}
```

Do not commit an asset to a public repository until `public_use_confirmed` is true.

### 7.4 Raw-file rule

The raw export is immutable. All derived work uses copies. Hash it immediately and verify that later workflows have not changed it.

---

## 8. Corpus layout

Use this structure unless the existing repository architecture provides an equally clear equivalent:

```text
validation/
  corpus/
    patchling_01/
      provenance.json
      prompt.md
      raw/
        asset.glb
        asset.fbx                 # optional archive, unsupported by product
      blind_asset_shepherd/
        inspection.json
        repair_plan.json
        decisions.json
        verification.json
        report.md
        repaired.glb
        result.zip
      observed_real_world/
        blender_import.md
        unreal_import.md
        adjudication.json
      human_reference/
        cleaned.blend
        cleaned.glb
        intervention_log.md
      controlled_variants/
        normalization_chaos/
          asset.glb
          mutation_manifest.json
        hierarchy_trap/
          asset.glb
          mutation_manifest.json
        material_texture_bloat/
          asset.glb
          mutation_manifest.json
      unreal_results/
        raw/
        shepherd/
        human_reference/
        comparison.json
        screenshots/
  profiles/
  mutations/
  blender/
  unreal/
  reports/
```

Large binary assets may remain outside Git or use Git LFS if repository size becomes unreasonable. The final public repository must still contain enough original or distributable assets for judges to reproduce at least one complete demo workflow.

---

## 9. Blind raw-asset workflow

The blind phase is mandatory. It prevents the inspection rules from being written after a human has already diagnosed the asset.

For each untouched Tripo GLB:

1. Hash and register the raw file.
2. Run the Asset Shepherd workflow agent with a confirmed target and recorded project constraints.
3. Freeze its sensor calls, observations, assessments, disposition, proposed actions, decisions,
   report, and verification artifacts.
4. Record every agent finding and invariant failure before manual Blender or Unreal diagnosis.
5. Only after the prediction is frozen, import the raw asset into Blender and Unreal.
6. Record the actual interventions or problems observed by the user.
7. Adjudicate each Asset Shepherd finding as true positive, false positive, useful warning, unsupported-but-correctly-blocked, or incorrect.
8. Add missed real-world defects to the adjudication record.

Do not retroactively alter the frozen blind result. Improvements are evaluated in a later run and recorded as a new product version.

---

## 10. Controlled realistic mutations

Synthetic primitives are not the only way to obtain known defects. Apply repeatable mutations to copies of realistic textured assets.

Mutation scripts must be independent of the production repair path wherever practical. Each variant must include a machine-readable manifest containing exact transformations, affected elements, expected findings, expected action classes, and expected post-repair invariants.

### 10.1 Required mutations

| Mutation | Example operation | Expected Asset Shepherd behavior |
|---|---|---|
| Scale mismatch | Multiply represented size by 100 | Agent recognizes the target conflict from sensor evidence, previews a supported scale action, and obtains approval |
| Sideways orientation | Rotate root 90 degrees around X or Z | Agent uses transform and rendered evidence, previews a supported rotation, and obtains approval |
| Floating geometry | Translate model above ground | Agent determines whether grounding is intended, previews a supported translation, and obtains approval |
| Pivot displacement | Offset root origin laterally or vertically | Detect or report according to current capability; never silently invent intent |
| Name corruption | Missing, duplicate, invalid node and mesh names | Agent chooses a typed rename when project rules warrant it; deterministic tools preserve references |
| Empty hierarchy | Add empty leaf and nested transform nodes | Remove only when mechanically safe; otherwise report or require approval |
| Material bloat | Duplicate visually equivalent material slots or add unused material | Report budget; remove only provably unused resources if contract permits |
| Texture bloat | Inflate one texture to 8192 or create duplicated image references | Report budget; do not resize or artistically edit in MVP |
| Negative scale | Mirror through a negative root scale | Detect; block or report unless preservation is proven; do not risk winding/normal corruption |
| Unsupported content | Add skin, animation, morph target, or required unsupported extension | Inspect and block structural repair explicitly |

### 10.2 Combined variants

Create at least these three combined variants from realistic assets:

#### `normalization_chaos`

- 100× scale.
- Sideways rotation.
- Non-grounded translation.
- Invalid and duplicate names.

This is the realistic successor to the synthetic broken robot and should remain repairable with one coherent human approval.

#### `hierarchy_trap`

- Nested non-identity transforms.
- Empty nodes.
- One negative-scale or ambiguous transform branch.

The expected result may include blocked or unresolved findings. Safety is more important than repair count.

#### `material_texture_bloat`

- Material count beyond profile budget.
- At least one provably unused resource.
- At least one oversized or duplicated texture resource.

The expected result is mostly report-only, with removal only where reachability and reference preservation are certain.

### 10.3 Mutation acceptance

A mutation is valid only when:

- The pre-mutation source remains unchanged.
- The manifest exactly describes the variant.
- The mutated GLB parses.
- The mutation does not unintentionally destroy textures or geometry.
- Independent inspection confirms the intended defect is present.

---

## 11. Blender production-path validation

Blender is a local validation and reference tool, not a hosted Asset Shepherd runtime dependency.

### 11.1 Three Blender paths

For selected assets, preserve:

1. **Raw import:** Untouched Tripo GLB imported into Blender.
2. **Asset Shepherd import:** Repaired GLB imported into Blender.
3. **Human reference:** Raw GLB manually cleaned in Blender by the user, with every intervention recorded.

### 11.2 Blender evidence

Record:

- Blender version.
- Import settings.
- Export settings.
- Scene dimensions and axes.
- Object and material counts.
- Texture availability.
- Warnings and errors.
- Visual anomalies.
- Manual interventions and elapsed time.
- Saved `.blend` and re-exported `.glb` where distributable.

### 11.3 Human-reference rule

The human-cleaned asset is a practical reference, not infallible ground truth. It represents what the user would actually do to make the asset usable.

The intervention log must distinguish:

- Required import repair.
- Project preference.
- Visual polish outside Asset Shepherd's scope.
- Optional optimization.

Only required import repairs should count against Asset Shepherd's defect recall.

### 11.4 Automation

Codex should automate Blender import, metric extraction, and export with background Python scripts where stable. The user should not be forced to repeat mechanical clicks. Manual visual assessment remains acceptable and necessary for appearance.

---

## 12. Unreal acceptance validation

Unreal is the downstream product oracle for the hackathon demo.

### 12.1 Comparison set

For at least one asset, and ideally three, import:

```text
A. Raw Tripo GLB
B. Asset Shepherd repaired GLB
C. Human-cleaned Blender reference GLB
```

Import all three using the same Unreal version and equivalent Interchange settings.

### 12.2 Isolated validation project

Create a small dedicated Unreal project or validation map. Do not test inside the user's production game project.

The project should contain:

- Separate content folders for raw, Shepherd, and human-reference assets.
- Three standardized pedestals or spawn locations.
- Fixed lighting and camera positions.
- A scale reference, such as a 1.8-meter mannequin proxy or measurement frame.
- Automated or repeatable screenshots.

### 12.3 Recorded Unreal evidence

Capture:

- Import success or failure.
- Import warnings and errors.
- Static-mesh bounds in centimeters.
- Actor orientation.
- Ground contact and pivot behavior.
- Vertex and triangle counts where exposed.
- Material slot count.
- Imported texture count and dimensions.
- Missing or unassigned materials.
- Visible normal, shading, transparency, emissive, or UV problems.
- Standardized screenshots.
- Time required for any remaining manual fixes.

### 12.4 Unreal automation

Codex should use Unreal Python or commandlets to automate import, placement, metric collection, and screenshot setup where practical. If a fully headless path proves disproportionately expensive, preserve a repeatable semi-automated workflow and a structured manual checklist.

Do not expand the Asset Shepherd product into an Unreal plugin during the hackathon merely because validation uses Unreal.

---

## 13. Adjudication model

Each real-world asset receives `adjudication.json` with at least:

```json
{
  "asset_id": "patchling_01",
  "product_version": "",
  "findings": [
    {
      "finding_code": "",
      "classification": "TRUE_POSITIVE",
      "human_notes": "",
      "downstream_evidence": []
    }
  ],
  "missed_required_repairs": [],
  "false_severe_findings": [],
  "unsafe_automatic_repairs": [],
  "correctly_blocked_cases": [],
  "raw_unreal_result": "",
  "shepherd_unreal_result": "",
  "human_reference_unreal_result": "",
  "manual_minutes_raw_to_usable": null,
  "manual_minutes_after_shepherd": null,
  "visual_fidelity_assessment": "",
  "demo_candidate": false
}
```

Allowed finding classifications:

- `TRUE_POSITIVE`
- `FALSE_POSITIVE`
- `USEFUL_WARNING`
- `CORRECTLY_BLOCKED`
- `INCORRECT_ACTION_CLASS`
- `NOT_ADJUDICATED`

---

## 14. Metrics and hard gates

### 14.1 Required metrics

Report:

- Controlled-defect recall.
- False `ERROR` or `BLOCKER` findings on clean or human-reference assets.
- Automatic name-repair success.
- Approved normalization success.
- GLB parse and validation rate.
- Blender import rate.
- Unreal import rate.
- Material and texture preservation rate.
- Idempotence rate.
- Median deterministic runtime.
- Human decisions per job.
- Manual minutes from raw export to usable Unreal asset.
- Manual minutes after Asset Shepherd.
- Missed required repairs by category.
- Correctly blocked unsupported cases.

### 14.2 Nonnegotiable safety gate

**Unsafe, unapproved, or agent-unrequested repairs must equal zero.**

An unsafe repair includes any unapproved or agent-unrequested operation that:

- Damages visible geometry.
- Changes intended scale or orientation.
- Breaks materials or textures.
- Alters artistic appearance.
- Removes referenced content.
- Produces an asset that imports worse than the source.

A missed finding is a product defect to improve. A silent damaging repair is a release blocker.

### 14.3 Honest claims

Do not claim broad industry-wide accuracy from a small corpus. Public claims should be phrased as controlled and case-study evidence, for example:

- “Validated on four untouched textured Tripo exports and nine controlled realistic variants.”
- “Preserved geometry, materials, and textures in all successful repair runs.”
- “Reduced manual normalization steps on the demonstrated Unreal workflow from X to Y.”

Do not invent percentages whose denominator is three attractive robots.

---

## 15. Minimum completion gate

Real-world validation is minimally complete when all of the following are true:

1. Four untouched textured Tripo GLBs have been registered and hashed.
2. Patchling is among them and is suitable for public demo use.
3. Blind Asset Shepherd results were frozen before manual diagnosis.
4. At least six controlled realistic variants exist across at least three base assets.
5. `normalization_chaos`, `hierarchy_trap`, and `material_texture_bloat` are represented.
6. At least one asset has completed the three-way raw versus Shepherd versus human-reference Blender-to-Unreal comparison.
7. Asset Shepherd produced zero unsafe, unapproved, or agent-unrequested repairs.
8. Material and texture preservation has explicit evidence.
9. A reproducible report summarizes findings, misses, blocks, runtime, and manual effort.
10. One asset and one failure story have been selected for the final demo.

### 15.1 Preferred completion gate

If schedule permits:

- Six raw Tripo assets.
- Twelve controlled variants.
- Three Unreal comparisons.
- Two separate human evaluators or repeated trials for manual-time estimates.

The preferred gate must not displace a stable Strands workflow, web experience, AWS deployment, or final video.

---

## 16. Relationship to existing milestones

### 16.1 M6 deterministic checkpoint

Complete the existing rejection-path, clean-control, package-audit, and independent-consumer checks first. Do not discard synthetic fixtures.

### 16.2 Real-world validation insertion

After M6:

1. Create validation scaffolding and Patchling generation card immediately.
2. Run the first raw Patchling blind evaluation before large agent/UI changes obscure deterministic behavior.
3. Continue M7 Strands work once one textured real-world asset completes the deterministic pipeline without corruption.
4. Use Patchling as the preferred M8 web-preview asset if it remains visually strong.
5. Complete the minimum real-world gate as part of the expanded M10 evaluation milestone.
6. Do not finalize public claims or record the final demo before the three-way Unreal comparison exists.

This plan does not require Codex to idle while the user generates assets. It should build corpus tooling, mutation scripts, Blender automation, report generation, and Unreal harness scaffolding in parallel.

---

## 17. Execution milestones for Codex

### RW0 — Adopt addendum and scaffold corpus

**Work:**

- Commit this document as `docs/REAL_WORLD_VALIDATION_PLAN.md`.
- Link it from README and project status.
- Update M10 to reference this addendum.
- Create ignored or LFS-aware corpus directories.
- Add typed provenance, mutation-manifest, and adjudication schemas.
- Add a concise Tripo generation-card template.

**Gate:**

- Common quality gate passes.
- No product behavior changes.
- Patchling is the next requested human asset.

### RW1 — Patchling blind baseline

**Human action:** Generate and export Patchling according to Appendix A.

**Codex work:**

- Hash and register raw GLB.
- Run Asset Shepherd without manual diagnosis.
- Freeze blind outputs.
- Produce a compact checkpoint report.

**Gate:**

- Raw file unchanged.
- Textures and materials enumerated.
- Any repair is safely authorized or blocked.
- No visual or structural corruption.

### RW2 — Minimum Asset Flock blind corpus

**Work:**

- Repeat blind ingestion for Shader Lantern, Debug Beetle, and Cloudforge Workbench.
- Generate preliminary adjudication forms.
- Identify recurring natural failures.
- Fix only clear product defects without overfitting to asset IDs or prompts.

**Gate:**

- Four raw assets registered.
- Results are versioned and frozen.
- No scenario-specific dispatch exists in product code.

### RW3 — Controlled realistic variants

**Work:**

- Implement repeatable mutation scripts.
- Create at least six variants across three base assets.
- Generate manifests and expected results.
- Run evaluation and record recall, action class, repair result, preservation, and idempotence.

**Gate:**

- All intended mutations independently confirmed.
- No source mutation.
- Zero unsafe, unapproved, or agent-unrequested repairs.

### RW4 — Blender and Unreal acceptance

**Work:**

- Automate Blender evidence where practical.
- Create human-reference cleanup log.
- Build isolated Unreal validation project or map.
- Import raw, Shepherd, and human-reference variants.
- Capture metrics and standardized screenshots.

**Gate:**

- One complete three-way comparison.
- Shepherd output imports at least as reliably as raw.
- No material or texture regression attributable to Asset Shepherd.
- Remaining manual work is documented.

**Mandatory periodic checkpoint:** Stop and provide the user with the comparison report and screenshots for visual adjudication before using the asset in public claims.

### RW5 — Evaluation report and demo selection

**Work:**

- Generate consolidated report.
- Select final hero asset and strongest failure story.
- Update README evidence and Devpost claims.
- Integrate Patchling into UI/demo branding if useful.

**Gate:**

- Every public metric traces to an artifact.
- Demo asset has confirmed public-use rights.
- Video path is repeatable and prevalidated.

---

## 18. Codex autonomy and escalation

Codex should continue autonomously between gates.

### 18.1 Codex may decide without asking

- Corpus directory implementation.
- JSON schema details consistent with this document.
- Hashing and artifact naming.
- Local Blender scripting.
- Unreal validation-project organization.
- Screenshot naming and report formatting.
- Mutation implementation details that preserve manifest semantics.
- Whether large private artifacts use `.gitignore`, Git LFS, or documented external storage, provided the public reproducibility requirement remains satisfied.

### 18.2 Codex must request human action only when necessary

Examples:

- Generate a specified Tripo asset.
- Confirm public-use rights.
- Choose between visually distinct candidates.
- Perform a Blender or Unreal visual judgment that cannot be automated reliably.
- Approve a scope change.

Human requests must be concise, singular, and immediately actionable.

### 18.3 Escalation conditions

Stop and report when:

- A real asset suffers an unsafe, unapproved, or agent-unrequested repair.
- A repaired asset loses textures, materials, geometry, or visible fidelity.
- Product code appears to require scenario-specific logic.
- The only apparent fix requires FBX support or Blender in the hosted product runtime.
- Tripo output rights are uncertain for public release.
- Unreal automation would consume more schedule than the stable web/AWS/demo path permits.
- The final demo candidate cannot survive a repeatable end-to-end run.

---

## 19. Scope protections

This validation plan does not authorize:

- FBX input support.
- Skeletal or animation repair.
- Topology reconstruction.
- UV generation.
- Texture generation, resizing, or artistic editing.
- Material merging.
- Hosted Blender dependency.
- Unreal Editor plugin development.
- Training or fine-tuning on the corpus.
- Hardcoded handling for Patchling or any named corpus asset.

The corpus exists to test generality, not to inspire a special case called `if asset_id == "patchling_01"`.

---

# Appendix A — Tripo generation prompts

Use these as starting prompts. Record any edits verbatim in provenance.

## A1. Patchling Courier

```text
Create a single isolated stylized 3D game asset of a friendly small repair-courier automaton named Patchling. It is an original whimsical shepherd-inspired helper robot with a clearly readable face and front direction, compact stable feet, a braided cable tail or scarf, one asymmetrical utility satchel, a crook-shaped repair wrench, and a small geometric wayfinding post attached to its backpack. Use painted metal, rubber, cloth, glass, and one warm emissive diagnostic light. Include a clear translucent visor if feasible. Strong clean silhouette, charming fantasy-technology design, detailed PBR textures, game-ready proportions, full body visible, centered, no background, no ground plane, no text, no letters, no logos, no weapons, no human, no extra detached props, no franchise resemblance.
```

Selection preference: clear front/back, visible feet, strong textures, asymmetry, visor/emissive detail, moderate complexity.

## A2. Shader Lantern

```text
Create a single isolated stylized 3D game prop called the Shader Lantern: a whimsical fantasy-technology workshop lantern used by tiny repair agents. It has a sturdy grounded base, thin protective cage elements, a glass or translucent chamber, a warm emissive core, painted metal, worn rubber grips, and subtle cloth or cord details. Strong clean silhouette, detailed PBR textures, game-ready, centered, full object visible, no background, no ground plane, no text, no letters, no logos, no characters, no extra detached objects, no franchise resemblance.
```

Selection preference: visible transparency, emissive surface, thin geometry, obvious ground plane.

## A3. Debug Beetle

```text
Create a single isolated stylized 3D game asset of a friendly mechanical-organic beetle called the Debug Beetle. It is a small workshop creature with a curved segmented shell, mirrored articulated legs, one asymmetrical repair pouch, tiny diagnostic lenses, painted metal mixed with natural chitin-like surfaces, rubber joints, and subtle emissive markings. Clear head and forward direction, stable feet, detailed PBR textures and normal detail, charming rather than threatening, centered, full body visible, no background, no ground plane, no text, no letters, no logos, no weapons, no extra detached props, no franchise resemblance.
```

Selection preference: organic curvature, mirrored parts, normal-map detail, clear orientation, multiple materials.

## A4. Cloudforge Workbench

```text
Create a single isolated stylized 3D game environment prop called the Cloudforge Workbench. It is a compact whimsical fantasy-technology repair bench with a sturdy frame, drawers, clamps, braided cables, a small diagnostic screen with abstract shapes only, several attached tools, a hanging cloth, painted metal, wood or composite surfaces, rubber, and small emissive accents. The workbench must read as one coherent asset with realistic human-scale proportions and clear ground contact. Detailed PBR textures, game-ready, centered, full object visible, no background, no ground plane, no readable text, no letters, no logos, no characters, no detached floating objects, no franchise resemblance.
```

Selection preference: many components, repeated objects, material variety, clear scale and grounding.

## A5. Strandwing Glider — stretch

```text
Create a single isolated stylized 3D game prop of an unmanned courier glider called the Strandwing. It has a very clear forward direction, asymmetrical satchel compartment, thin wing surfaces, braided cable control lines, a translucent windscreen or sensor canopy, painted metal, cloth, rubber, and warm emissive navigation lights. Compact whimsical fantasy-technology style, no pilot, stable display stance or landing skids, detailed PBR textures, centered, full object visible, no background, no ground plane, no text, no letters, no logos, no weapons, no extra detached props, no franchise resemblance.
```

## A6. Wayfinder Post — stretch

```text
Create a single isolated stylized 3D game environment prop called the Wayfinder Post. It is a whimsical workshop signpost used by repair agents, with several plain geometric direction arrows, a grounded stone-and-metal base, braided cords, a small hanging cloth pennant with no symbols or text, painted metal, wood or composite material, and one warm emissive locator light. Clear upright orientation and pivot at the base, detailed PBR textures, game-ready, centered, full object visible, no background, no ground plane, no readable text, no letters, no logos, no characters, no detached floating objects, no franchise resemblance.
```

---

# Appendix B — First Codex execution instruction

After this file is added to the repository, use this instruction:

```text
Read docs/PROJECT_CONTRACT.md, docs/PROJECT_STATUS.md, and docs/REAL_WORLD_VALIDATION_PLAN.md completely. Treat the real-world validation plan as the controlling addendum for corpus, Tripo, Blender, Unreal, evaluation, and demo-asset work.

Work directly on main. Begin RW0. Do not change product scope or repair safety. Continue autonomously through all work that does not require a human-generated Tripo asset. When Patchling generation becomes the actual blocking dependency, provide one concise generation card containing the exact prompt, candidate count, export settings, destination path, and what the user must not modify before ingestion. Continue building validation scaffolding in parallel rather than idling.

Stop only at a defined escalation condition or the mandatory RW4 visual-adjudication checkpoint. Keep docs/PROJECT_STATUS.md current and evaluate each commit against both controlling documents.
```
