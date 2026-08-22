# Asset Shepherd Marketing Strategy

**Hackathon:** Agents for Humans  
**Track:** Professional Agents  
**Primary audience:** Indie game developers and technical artists  
**Project:** Asset Shepherd  
**Status:** Controlling marketing and submission guidance

## 1. Core positioning

Asset Shepherd helps indie game developers get AI-generated and marketplace 3D assets safely into Unreal Engine by inspecting, repairing, and verifying them end to end, pausing only when a change could alter artistic intent.

The product is not a conversational assistant that recommends Blender settings. It performs the workflow:

```text
upload asset
→ inspect facts
→ classify defects
→ apply safe repairs
→ request approval for consequential changes
→ repair
→ independently verify
→ return a project-ready package with evidence
```

The concise product promise is:

> A broken 3D asset enters, one meaningful approval is requested, and a correctly scaled, upright, grounded, valid asset exits with before-and-after evidence.

## 2. The concrete problem

Externally sourced 3D assets frequently require repetitive technical cleanup before they can be used in a game project. Common failures include:

- implausible physical scale;
- incorrect orientation or grounding;
- bad pivots and transforms;
- missing, invalid, or duplicate names;
- messy hierarchy;
- excessive materials or textures;
- broken or awkward Blender-to-Unreal import behavior;
- uncertainty about which changes are mechanically safe and which may alter artistic intent.

The existing workflow forces a developer or technical artist to inspect the asset, diagnose issues, cautiously modify it, import it again, and verify that the cleanup did not damage geometry, materials, textures, or intended presentation.

Asset Shepherd converts that work into **exception supervision**:

- deterministic tools measure the asset;
- the Strands agent interprets the findings against project policy;
- safe transformations happen automatically;
- ambiguous or artistic changes wait for human approval;
- verification is independent of the agent's verbal confidence.

## 3. Audience

The primary audience is:

- indie game developers who buy or generate 3D assets but do not have a full technical-art team;
- technical artists responsible for repetitive asset intake and cleanup;
- small studios using generated, marketplace, contractor, or procedurally created assets;
- Unreal developers whose real production path includes Blender and Unreal Interchange.

The project should be described through this audience's workflow and cost, not through generic claims about autonomous agents.

## 4. Why the project stands out

Asset Shepherd is distinctive because it combines:

1. **A narrow, real professional problem.** It addresses the painful Blender-to-Unreal intake pass rather than a broad creative chatbot.
2. **Real work rather than advice.** It emits a repaired GLB, structured findings, decisions, provenance, verification, and a result package.
3. **Constrained autonomy.** The system acts automatically only when the repair is mechanically safe and policy-authorized.
4. **Meaningful human interruption.** It surfaces only when scale, orientation, grounding, pivot, materials, hierarchy, or another consequential choice requires intent.
5. **Independent evidence.** It reopens and reinspects the saved output, checks source preservation and invariants, records hashes, and verifies that the repair plan is exhausted.
6. **A visually legible demo.** Judges can immediately understand a broken asset beside its corrected result in Unreal.
7. **A realistic benchmark.** Validation uses untouched textured Tripo assets, controlled mutations of realistic assets, and Blender-to-Unreal comparison rather than relying only on synthetic fixtures.

## 5. Strands Agents message

Use of Strands Agents must be impossible to miss in every submission surface.

### Project description

State explicitly that Strands Agents orchestrates the complete workflow:

```text
inspection
→ policy interpretation
→ repair planning
→ human approval interrupt
→ repair execution
→ verification
→ final packaging
```

### Built With

Include at minimum:

- Strands Agents SDK;
- Amazon Bedrock or the final selected model provider;
- Amazon Bedrock AgentCore if deployed;
- AWS services used by the final system;
- Python deterministic 3D inspection and repair tools;
- Blender and Unreal Engine as independent validation consumers, not hosted repair dependencies.

### Demo

Show the Strands workflow visually or narratively. The video should clearly demonstrate:

- the agent reading structured inspection evidence;
- a human approval interrupt for one consequential normalization decision;
- resumption after approval;
- independent verification after repair.

Do not bury Strands in a dependency list or describe the product as if deterministic scripts alone constitute the agent.

## 6. Brand and mascot

**Patchling** is the preferred hero asset and potential project mascot if the selected Tripo candidate is visually strong.

Patchling is an original repair-courier automaton with a shepherd-inspired repair tool, braided cable motif, utility satchel, wayfinding post, varied PBR surfaces, and one warm diagnostic light.

Patchling serves four purposes:

- a memorable visual identity for Asset Shepherd;
- a realistic textured validation asset;
- a hero asset for screenshots and the demo;
- a recurring device for explaining the product journey.

Do not reproduce AWS, Devpost, Strands, game-franchise, or other third-party logos or characters inside the 3D asset. Official names may be used normally in project text and metadata.

## 7. Claim discipline

All public claims must be traceable to project evidence.

Preferred wording:

- "Validated on four untouched textured Tripo exports and nine controlled realistic variants." Only use this exact example after those numbers are actually achieved.
- "The repaired output passed independent GLB reload and verification."
- "Asset Shepherd preserved source hashes, geometry counts, and authorized repair provenance in the demonstrated case."
- "In the demonstrated workflow, the user approved one normalization decision while safe naming repairs were applied automatically."
- "The result imported successfully through the isolated Blender and Unreal validation harness." Only use after that specific asset has passed.

Avoid unsupported wording such as:

- "works on any 3D asset";
- "automatically fixes all Blender-to-Unreal problems";
- "production-ready for every studio";
- broad accuracy percentages derived from a tiny corpus;
- time-savings claims not supported by measured trials;
- claims that report-only warnings were repaired.

Case-study evidence is acceptable and more credible than decorative precision.

## 8. Devpost project-page strategy

The Devpost entry should follow this order.

### Opening statement

> Asset Shepherd is a Strands-powered professional agent that helps indie game developers get AI-generated and marketplace 3D assets safely through the Blender-to-Unreal pipeline. It performs inspection, safe repair, human-approved normalization, and independent verification, then returns a project-ready asset package with complete before-and-after evidence.

### Problem

Describe one recognizable workflow:

> A developer downloads or generates a promising model, then discovers that it is enormous, sideways, floating, poorly named, materially messy, or unreliable to import. The developer must repeatedly inspect, modify, export, import, and verify it before using it in the game.

### Solution

Explain that Asset Shepherd handles the mechanical workflow end to end and only interrupts for genuine intent decisions.

### Why it matters

Small teams lack dedicated technical-art capacity. Repetitive asset intake consumes development time and unsafe automation can silently damage art. Asset Shepherd aims to reduce routine work without pretending that artistic intent can be inferred with certainty.

### Technical differentiation

Mention:

- Strands orchestration and native human interruption;
- deterministic 3D measurement and mutation tools;
- explicit repair safety classes;
- immutable source preservation and provenance;
- independent reinspection;
- real-world Tripo, Blender, and Unreal validation.

### Evidence

Use screenshots, side-by-side results, verification excerpts, measured corpus results, and a link to the reproducible validation methodology.

## 9. Five-minute video strategy

Treat the video as a pitch, not a tutorial. Target approximately 4 minutes 15 seconds so editing and platform behavior cannot accidentally cross the five-minute limit.

### 0:00–0:30 — The pain

Show a visually credible raw asset or Patchling importing incorrectly or carrying obvious measurable defects.

Voiceover should establish:

- who encounters the problem;
- what goes wrong;
- why manual iteration is expensive and risky.

### 0:30–0:50 — The product promise

Introduce Asset Shepherd in one sentence and name Strands Agents immediately.

### 0:50–2:35 — The workflow

Show:

1. project profile selection;
2. asset upload;
3. deterministic inspection findings;
4. automatic safe repairs;
5. one consequential approval card;
6. Strands pause and resume;
7. repair and independent verification;
8. downloadable result package.

Do not show long agent transcripts or model monologue.

### 2:35–3:20 — Visual result

Show raw, Asset Shepherd, and human-cleaned or expected-reference arms inside the isolated Unreal comparison environment. Use fixed cameras and lighting.

Highlight:

- dimensions;
- orientation;
- grounding;
- materials and textures;
- remaining warnings;
- source and output integrity.

### 3:20–3:50 — Why the implementation is credible

Show one clear architecture diagram and explain the boundary:

- Strands interprets and coordinates;
- deterministic tools measure and repair;
- the human authorizes consequential changes;
- an independent verifier decides whether the output passes.

### 3:50–4:15 — Impact and close

End with the demonstrated evidence and product thesis:

> Asset Shepherd turns 3D asset intake from repeated technical cleanup into supervision of the few decisions that actually require human intent.

## 10. Screenshot and visual strategy

The strongest images are:

1. Raw versus repaired asset in Unreal under identical camera and lighting.
2. One approval card showing observed evidence, proposed action, consequences, and alternatives.
3. Findings resolved versus remaining warnings.
4. Verification summary with source preservation and independent reload.
5. The Strands workflow graph.
6. Patchling as the recognizable hero asset.

Avoid screenshots dominated by terminals, JSON walls, AWS consoles, dependency installation, or generic chat bubbles.

## 11. Builder Center post strategy

Publishing at least one qualifying Builder Center post is required by the marketing plan because the hackathon explicitly offers bonus points for documenting the build journey.

Preferred first title:

> Agents for Humans: Building a Safe 3D Asset Shepherd for the Blender-to-Unreal Pipeline

Core sections:

- the real workflow problem;
- why a chatbot is insufficient;
- how deterministic inspection differs from agent judgment;
- the act, ask, or refuse repair policy;
- Strands interruption and resume;
- independent verification;
- lessons from real Tripo assets and Unreal imports.

Preferred second title:

> Agents for Humans: When a 3D Repair Agent Should Act, Ask, or Refuse

Potential third title:

> Agents for Humans: Testing a 3D Asset Agent with Tripo, Blender, and Unreal Engine

Use the final required event naming and hashtags. Link to the public repository only after it is ready for public inspection.

## 12. Secrets and public-release hygiene

Before making the repository public or submitting:

- confirm `.env` files are ignored;
- confirm AWS credentials and local credential directories are absent;
- confirm no model-provider API key appears in history or generated artifacts;
- remove presigned URLs, session tokens, account identifiers, and private paths from screenshots and logs;
- run an automated secrets scan over the repository and Git history;
- use environment variables, IAM roles, or a secrets manager;
- verify all demo credentials have minimum required permissions;
- inspect the final release from a logged-out browser.

The video and screenshots must not reveal AWS account emails, Builder ID emails, local personal files, API keys, or unrelated browser tabs.

## 13. Commercial continuation

The hackathon version should imply a credible continuation without bloating the MVP.

Potential product path:

- open-source deterministic inspection and verification core;
- hosted per-asset processing;
- project and studio policy profiles;
- Unreal Editor integration;
- marketplace-vendor validation reports;
- batch intake for small studios;
- future support for additional formats and controlled repair classes.

Do not promise FBX, skeletal repair, animation retargeting, topology reconstruction, UV generation, collision, or LOD generation in the hackathon MVP.

## 14. Marketing acceptance gate

Before submission, confirm:

- [ ] The opening statement names the user, problem, outcome, and Strands Agents.
- [ ] The project is described as real end-to-end work rather than chat.
- [ ] The Blender-to-Unreal workflow is visible in the description and video.
- [ ] One genuine human approval interruption is shown.
- [ ] Every quantitative claim is traceable to evaluation evidence.
- [ ] Patchling or the chosen hero asset is visually recognizable and original.
- [ ] The demo shows before and after under identical conditions.
- [ ] Strands appears in the project description, Built With section, architecture, and video.
- [ ] A qualifying Builder Center post is published before the deadline.
- [ ] The public repository and its history pass a secrets scan.
- [ ] No unsupported universal, accuracy, or time-savings claims remain.
- [ ] The video remains under five minutes and works as a pitch without the repository.

## 15. Single-sentence summary

> Asset Shepherd is a Strands-powered professional agent that safely shepherds AI-generated and marketplace 3D assets through inspection, repair, human approval, and independent verification so small game teams can get them into Unreal without repeating the same fragile cleanup work by hand.
