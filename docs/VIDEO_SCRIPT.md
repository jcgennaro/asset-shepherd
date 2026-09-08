# Asset Shepherd — pitch video and production script

Draft 1 · September 7, 2026 · Professional Agents / Agents for Humans

**Target cut: 4:45, including the end card. Hard ceiling: 5:00.**

[Narration-only recording copy](VIDEO_VOICEOVER.md). Main narration is 631 whitespace-delimited
words, averaging about 133 words per minute across the cut. Some short beats need up to roughly
160 words per minute; rehearse and shorten those before recording rather than rushing.

The story: getting a plausible 3D model is not the same as getting the asset your game needs.
Asset Shepherd turns that gap into an inspectable, approval-driven conversation. Demonstrate
this with the gaming-peripherals scene: keep the headphones, not the whole generated set.

This is a production plan, not a claim that footage, final narration, or the finished video exists.
Do not schedule another paid model run just to follow this document without coordinating with
the owner. Prefer capturing the saved successful run and its exported result first.

## 1. Editorial decisions and outstanding facts

- Lead with the actual visual problem and reveal the product within the first minute. Give the
  working example almost two minutes; architecture supports the proof, not the reverse.
- Address solo/small-team 3D game developers and technical artists who prepare acquired/generated
  assets. This is our initial audience, not a claim that every game developer needs the product.
- The owner confirms a background in engineering and product development, not digital art,
  and firsthand frustration moving even simple static assets from concept into a game despite
  helpful generation, Blender, and engine tools. Existing open-source tools can perform the
  supported repair actions; Shepherd brings those actions together with agent guidance.
  “All in one place” refers to these repairs, not embedding generation, Blender or a game engine.
  Use “we” for the product thesis, without implying a larger team or inventing experience, roles,
  shipped games, revenue or customers.
- The multi-part headphones result has positive **user visual assessment**. Its exact component
  count, selected IDs, final verification, output hash, elapsed time, and tokens await the saved
  workspace/evidence. The supplied comparison screenshot says “rejected candidate” / “candidate
  not ready.” It may be an intermediate state. Do not hide that label or describe that frame as
  verified. Capture the actual final state before locking the demo.
- The second gamer-headphones test is a separate user-reported success. Do not substitute its
  final screen or downloaded file for the multi-part example.
- Default: **Luna xhigh through the OpenAI API**, hosted orchestration on AWS. Kimi K2.5 remains
  selectable through Bedrock. Do not say Luna is running “in Bedrock,” all inference stays in AWS,
  or a router automatically falls back between providers.
- Model-selection story: quality, latency, and cost **per satisfactory completed task** matter.
  Luna is our current choice based on observed results, not a proven universal price/performance
  winner. There is not yet an unbiased, complete Luna success-rate denominator.
- The component-label copy shortening is committed but not yet hosted. Freeze the capture build
  before recording; do not intercut incompatible UI versions as one uninterrupted run.

## 2. Beat-by-beat master script

Times are edit allocations, including brief visual holds. Read only the quoted narration.
Bracketed production instructions are not spoken. Record each beat as its own audio take,
with two seconds of room tone at either end. Footage and graphic IDs resolve in the inventory.

### 01 · 00:00–00:12 · The hook

> I asked for gaming peripherals. I got this. But for my game, I only want the headphones.
> Getting a convincing model is one thing. Getting the right usable asset is another.

**Picture:** V01, slow orbit of the untouched scene. At “only want,” freeze briefly and add a
thin mint outline around the headphones, leaving keyboard/PC visible. Do not fake removal.
**Overlay O01:** “I only need the headphones.” No title animation before this problem.
**Cut:** Hold the contrast for one second; no rapid flashing component labels yet.

### 02 · 00:12–00:29 · Who needs this, and how large is the audience?

> SlashData estimated 11.1 million game developers worldwide in early 2024. Our starting audience
> is narrower: solo developers and small teams preparing 3D props without a dedicated technical
> artist. They need usable assets, not another complicated cleanup workflow.

**Picture:** G01 market card over a softened, still-visible source model; then S01/S02 asset
thumbnails. Use our actual assets, not stock footage of imaginary customers.
**Overlay O02:** “11.1M game developers worldwide” followed by “Initial focus: small-team 3D workflows.”
**Source footer, visible throughout the statistic:** “SlashData · Q1 2024 estimate · includes
professionals, hobbyists and students.” The estimate is ecosystem context, not TAM or paying users.
**Optional tighter fallback:** Remove the number and say “Our starting audience is solo developers
and small game teams working with acquired or generated 3D props.” Do not replace it with a guessed
2026 population or an unsupported revenue forecast.

### 03 · 00:29–00:49 · Why we built it

> Our background is engineering and product development, not digital art. Even with AI model
> generation, Blender, and game engines, getting a simple static prop from concept into a game
> was frustrating. Open-source repair tools existed. We needed help connecting the problem
> to the right tool.

**Picture:** S01 oversized collar with banana for scale; S02 tablet or riding crop; optional
V02 founder on camera, if desired. Otherwise use a clean project-history montage.
**Overlay O03:** “Built from real asset-cleanup failures.”
**Confirmed founder framing:** Describe practitioner motivation, not an art-expert credential.
Blender is a creation/inspection tool, not itself an AI model generator. Do not show an invented
studio team or imply that Shepherd incorporates these entire applications.

### 04 · 00:49–01:05 · The promise

> That is Asset Shepherd, built for Agents for Humans: supported asset repairs in one place,
> guided by a vision-capable language model. Upload a static GLB, explain what you need, and
> review the proposal. The agent reasons; bounded tools do the work.

**Picture:** G02 product/mascot lockup dissolves into V03 Gallery. End on New asset.
**Overlay O04, revealed one at a time:** “Inspect” / “Propose” / “Approve” / “Verify.”
**Small qualifier:** “Static GLB assets.” Do not promise arbitrary 3D formats or full retopology.

### 05 · 01:05–01:22 · Upload the real example

> Here is the original Tripo export. The headphones are mixed into a scene of peripherals,
> with many separate geometric parts. I upload the original file and describe the outcome:
> keep the headphones, remove the rest.

**Picture:** V03 → V04. Show the actual original filename, upload acceptance, and Describe.
Type or reveal the actual recorded instruction; the proposed demo wording is
“Out of this set, I only want the headphones.” If the saved run used different wording, use it.
**Overlay O05:** “Original preserved.”
**Optional measured overlay:** “[N] disconnected components” only after N is copied from this
source's saved inspection. Until then use “Many parts. One intended object.”
**Edit note:** Skip most upload waiting, marking the cut “Processing shortened.”

### 06 · 01:22–01:39 · Agree on the target

> I confirm the destination, intended dimensions, and how closely the asset will be viewed.
> These are use-case choices, not a request for me to calculate a polygon budget. The agent
> works against that agreed target.

**Picture:** V05 shows the actual engine choice, proposed dimensions, viewing-use selection,
and target confirmation. A restrained crop enlarges the relevant control as each is mentioned.
**Overlay O06:** “Destination · Intended size · Viewing use.”
**Do not:** Enter invented values to match the narration, or imply selecting Unreal exports a
`.uasset`. Deliverable remains GLB.

### 07 · 01:39–02:01 · Make the intelligence visible

> Now the agent reads measurements and standardized screenshots. The difficult question isn't
> “which piece is biggest?” It's “which pieces together make the headphones?” It can inspect
> further before proposing what to keep. That is visual judgment, grounded in measured evidence.

**Picture:** V06. Show the real activity indicator briefly, then the labeled components and
source model. Open the long component disclosure, scroll slowly, and focus two or three parts
that the actual proposal keeps. Include a headband/earcup/detail example only if the IDs match.
**Overlay O07:** “Geometry counts ≠ object identity.” Then “Measurements + screenshots.”
**Edit note:** Retain 2–3 seconds of live activity; shorten the wait with a labeled jump cut.
Never overlay fabricated tool calls, hidden reasoning, or an invented selection animation.

### 08 · 02:01–02:21 · Keep the human in control

> The proposal identifies the parts to retain and remove. I can disagree or request a revision.
> Only my explicit approval authorizes the removal. The agent cannot quietly turn a guess—or
> an ordinary chat message—into permission to delete geometry.

**Picture:** V07, readable proposal and Keep/Remove controls; then the real Apply recommendations
click. Hold the exact selection before the click. If the run required a revision, show that
revision with its true order and label it; do not fabricate a one-pass result.
**Overlay O08:** “Proposed changes → Your approval.”
**Key proof:** Show at least one kept and one removed component with labels matching the scene.

### 09 · 02:21–02:46 · Show the result and its checks

> After the change, the tools reopen and measure the candidate, and the agent reviews fresh
> visual evidence. Here are the headphones separated from the original scene. I inspect the
> earcups, headband, and small details—and read any remaining warnings rather than treating
> “the tool ran” as proof of success.

**Picture:** V08, shared-scale before/after orbit → S03 exact verification/action summary →
V09 isolated candidate orbit. Keep any genuine remaining warnings visible.
**Overlay O09:** “Reopen · Measure · Reinspect.”
**Success gate:** This narration intentionally does not claim automated verification passed.
If the final record does pass, add “The recorded checks passed” only with the visible supporting
state. If only a rejected candidate exists, say “This candidate looks right to me, but automated
verification still flags it” and show the warning. If it cannot be downloaded/reopened, switch
the main end-to-end demo to a confirmed successful tablet/crop run and use headphones as a brief
honest component-selection case study. Re-time the cut; do not relabel failure as success.

### 10 · 02:46–03:00 · Deliver something real

> I download the result and reopen the actual exported file. This is a changed 3D asset, not
> advice about changing one. The original and the recorded evidence remain available for review.

**Picture:** V10 actual result download, then V11 reopen that file in a fresh viewer/session.
Use this run's output, not a prepared lookalike. Save the hash and filename off-camera.
**Overlay O10:** “A downloadable GLB—not just a recommendation.”
**Edit note:** If acceptance is still needed, briefly show Use this version before download.
Rejected-candidate downloads must remain labeled as such; acceptance is not a verification bypass.
An Unreal import is optional separate evidence, not something this script claims happened.

### 11 · 03:00–03:20 · Tease the rest without another full demo

> Component selection is one capability. Asset Shepherd can also propose scale, pose and pivot
> corrections, clean up display names, and offer controlled mesh simplification for the intended
> viewing use. It preserves the original and reports limitations instead of promising to repair
> every possible mesh.

**Picture:** V12 or three still cards: tablet scale; crop pose/pivot; collar simplification.
**Overlay O11, max three groups:** “Scale, pose & pivot” / “Names & structure” /
“Controlled simplification.”
**Qualifiers:** Do not imply general hole-filling, remeshing, UV repair, rigging, animation, or
texture compression. “Structure” means supported exact cleanup/component operations.
**Optional measured collar card:** 783,571 → 56,885 triangles and 30.2 → 7.7 MB only for the
archived D092 Luna run with those exact values, labeled “Separate collar test.” Do not mix the
slightly different later hosted collar result or predict file size from triangle reduction.

### 12 · 03:20–03:32 · Architecture reveal 1: the product core

> We started with the core: a Strands agent, deterministic GLB tools, and a lightweight browser
> renderer. The model chooses the work; the tools constrain and verify it.

**Picture:** G03/F1. Reveal a product-owned application box: Strands ↔ typed tools, with
Chromium evidence rendering alongside. Title “1 · Prove the asset workflow.”
**Overlay O12:** “Model judgment. Bounded execution.”
**Scope:** A conceptual build-up, not a dated claim about exact service creation order.

### 13 · 03:32–03:44 · Architecture reveal 2: put it on AWS

> We hosted the website with ECS Express and moved the workflow into Amazon Bedrock AgentCore
> Runtime. A queue and a small Lambda dispatcher separate long-running agent work from web requests.

**Picture:** G03/F2. Browser → ECS Express; ECS → SQS → Lambda → AgentCore. Place the existing
Strands/tools/renderer box inside AgentCore; keep positions stable after this move.
**Overlay O13:** “Web requests stay separate from long-running work.”

### 14 · 03:44–03:56 · Architecture reveal 3: remember the work

> S3 retains asset files and evidence. DynamoDB records workspace state and queued-command
> progress. The browser polls for updates, so the workflow does not depend on keeping one
> web request open.

**Picture:** G03/F3. Add S3 and DynamoDB under both web/runtime; animate “artifacts” and “state”
arrows once. Show a subtle browser ↔ web polling arrow, not streaming tokens.
**Overlay O14:** “Files + durable workflow state.”

### 15 · 03:56–04:08 · Architecture reveal 4: protect and operate it

> Cognito handles sign-in. IAM limits service permissions, and Secrets Manager holds the external
> model key. CloudWatch, alerts, and a shared spending ledger give us visibility and cost safeguards.

**Picture:** G03/F4. Add identity/security and operations bands. Show a small release strip:
source → CodeBuild → ECR → web/runtime images. Leave that strip unspoken to avoid acronym overload.
**Overlay O15:** “Authenticated · Observable · Budget-aware.”
**No overclaim:** These are safeguards, not a guarantee against account compromise or a cap on
all AWS charges. Current judge Gallery is shared, not private per-user tenancy.

### 16 · 04:08–04:20 · Architecture reveal 5: model boundary

> The same orchestration supports Bedrock models, or an approved external provider. Today's
> default is Luna xhigh through OpenAI. The application runs on AWS; the selected model call
> crosses that boundary over HTTPS.

**Picture:** G03/F5. Add Amazon Bedrock/Kimi **inside AWS** and OpenAI/Luna **outside AWS**.
Highlight Luna's selected path; show Kimi's alternative path in muted color.
**Overlay O16:** “Current default: Luna xhigh · OpenAI API.” Small secondary label:
“Alternative: Kimi K2.5 · Amazon Bedrock.”
**Precision:** Both web intake and AgentCore workflow can call the selected provider. Include
both caller arrows in the master; do not imply only AgentCore performs all inference.

### 17 · 04:20–04:40 · Why this model?

> We choose models for completed-task value: visual decisions, reliable tool use, latency, and
> total cost—including retries. Luna has delivered strong results in our hands-on asset tests,
> so it is our current default. We retain a Bedrock alternative and measure outcomes rather
> than picking a model by its name alone.

**Picture:** G04 concise model-decision card, then dissolve back to the headphones result.
**Overlay O17:** “Quality of result” / “Time to completion” / “Cost including retries.”
**Do not show:** “100% success,” “best model,” “cheapest,” or a fabricated comparison chart.
If complete comparable ledgers become available, replace this with a measured narrow claim,
labeling model/provider, sample count, date, retries, and exclusions. Never attribute the Kimi
8/8 selected-case gate to Luna or present it as a first-attempt production success rate.

### 18 · 04:40–04:45 · Close on the benefit

> Asset Shepherd. Less asset cleanup. More time making your game.

**Picture:** G05 end card with mascot, product name, repository path, “Built for Agents for Humans.”
**Overlay O18:** “Try the hosted demo · Testing instructions in Devpost.” Never show credentials.
Hold all the way to 04:45. No extra logo sting, black tail, credits crawl, or subscription animation.

## 3. Capture inventory — footage to record

Record at 1920×1080 or higher, 16:9, 30 fps. Edit/export at 1080p unless a higher-resolution
delivery is proven readable. Capture 3 seconds of stillness before/after every action. Record
one continuous master of the main run even though the final cut shortens waiting. Preserve
that master and a cut log as provenance. Durations below are raw capture targets, not promises
about model latency. Suggested filenames are production destinations, not existing files.

| ID / suggested file | Record exactly | Raw target | Used in beats | Acceptance check |
|---|---|---:|---|---|
| V01 `01-source-orbit.mp4` | Untouched gaming-peripherals scene, gentle orbit; headphones, keyboard, PC readable | 20–30s | 1, 2, 5 | Hash matches benchmark source; no other candidate substituted |
| V02 `02-founder.mp4` (optional) | Founder delivering beat 3, uncluttered background | 2 takes | 3 | Background/credentials confirmed; can omit camera entirely |
| V03 `03-gallery-upload.mp4` | Gallery → New asset → Luna selected → original GLB upload | Full action + wait | 4, 5 | No other users' private asset names; no key/email visible |
| V04 `04-describe.mp4` | Actual headphones-only request submitted and acknowledged | 20s + wait | 5 | Exact text matches saved run; no fake typing over unrelated state |
| V05 `05-target.mp4` | Destination, proposed dimensions, viewing use, confirmation | 30–45s + wait | 6 | Readable target; same workspace and source |
| V06 `06-inspection.mp4` | Activity → component inventory; expand, scroll, focus representative components | Full wait + 45s | 7 | Real labels and retained-parts reasoning; no hidden model thoughts |
| V07 `07-approval.mp4` | Whole proposal, selected Keep/Remove rows, revisions if any, approval click | 30–60s + wait | 8 | Approval clearly precedes mutation; every real refinement retained in cut log |
| V08 `08-result-comparison.mp4` | Final shared-scale before/after orbit plus result summary | 30–45s | 9 | Actual final state; warnings not cropped to imply pass |
| V09 `09-headphones-detail.mp4` | Isolated output: front, rear, both earcups, headband and small details | 30–45s | 9, 17 | Checks unwanted objects removed and expected headphone parts retained |
| V10 `10-download.mp4` | Acceptance if applicable → download → completed filename | 15–25s | 10 | Download completes; rejected versus verified status honest |
| V11 `11-reopen-export.mp4` | Load the downloaded GLB in a fresh viewer; orbit | 20–30s | 10 | Same output hash/file; geometry and materials visible |
| V12 `12-other-capabilities.mp4` (or stills) | Saved tablet/crop/collar results, with factual before/after metrics | 10–15s each | 11 | Each labeled separate example; no mixed-run metrics |
| V13 `13-architecture-reveal.mp4` | Five diagram frames/camera crops timed to beats 12–16 | 60s | 12–16 | Current AWS/external boundary correct; labels readable |

**One workspace, one chain of evidence:** mark the master capture with source hash, workspace ID,
model/provider/reasoning, deployed commit, approval/revision order, final state, output hash, and
observed run duration. Store private identifiers outside the public video when unnecessary.
Do not capture a second expensive run solely to obtain a prettier activity sequence without
owner approval. Saved-history footage must be labeled “Recorded session” if edited to resemble
active execution; never simulate an approval on a previously finished workspace.

## 4. Still-image inventory

| ID / suggested file | Needed still | Usage / requirements |
|---|---|---|
| S01 `collar-scale.png` | Real oversized collar with scale reference | Founder/problem montage; retain units and reference label |
| S02 `tablet-or-crop-result.png` | A separate confirmed successful saved result | Credibility montage; not a stand-in for headphones success |
| S03 `headphones-verification.png` | Final headphones outcome and relevant checks | Full-resolution reference plus readable video crop; unresolved status cannot be edited away |
| S04 `headphones-proposal.png` | Actual keep/remove proposal | Producer's reference for labels; optional beat-8 hold |
| S05 `headphones-export.png` | Downloaded GLB opened independently | End-to-end proof frame / possible video thumbnail |
| S06 `collar-simplification.png` | Exact archived simplification counts and byte sizes | Optional capabilities card; label separate test and preserve measurement units |
| S07 `market-source-reference.png` | Source page title/date/estimate | Internal citation evidence only; create our own statistic card, don't reproduce a publisher's chart |
| S08 `architecture-final.png` | Full final current architecture | Repository/Devpost architecture and production reference; detailed version need not fill the video screen |
| S09 `video-thumbnail.png` | Side-by-side original scene / extracted headphones with mascot | Make after final result confirmed; headline “I only need the headphones” |

The supplied chat screenshots are references, not final video plates: some are narrow crops,
intermediate states, or too small for a clean 1080p recording. Recapture cleanly rather than
upscaling UI text or painting out warning labels.

## 5. Graphics and overlay inventory

| Asset | Build specification | Required variants |
|---|---|---|
| G01 audience card | Original typography; 11.1M large, historical-date/source qualifier visibly smaller; second line narrows audience | Statistic card and no-number fallback |
| G02 brand lockup | Existing mascot and brand colors; restrained fade, no new animated logo dependency | Transparent lockup + full-frame title |
| G03 architecture | Editable vector/slides with named layers, as specified below | F1–F5 frames; detailed master; 1080p video-friendly crops |
| G04 model-choice card | Three criteria, not a benchmark podium; Luna default and Kimi alternative labeled by provider | Main criteria card; optional real measured comparison only after evidence review |
| G05 close | Mascot, benefit line, GitHub path, Devpost access instructions | 5-second end card; no credentials or private email |
| O01–O18 | Exact copy under each beat; separate editable text layers | Caption-safe placement variants |
| O19 processing disclosure | “Processing shortened” for jump cuts; actual “4× speed” only for footage genuinely at 4× | Small consistent top-corner tag |
| O20 run-metric chip (optional) | Actual end-to-end duration, model tokens, estimated model cost; specify exclusions | Omit if incomplete; no estimated number invented for recording |
| C01 captions | English SRT and corrected transcript derived from final audio | Validate model names, GLB, Strands, AgentCore, Cognito |

At 1080p: key overlays approximately 42–56 px, secondary text 30–36 px, source footers at least
24 px. Keep critical UI and overlays within a 90 px safe margin. No more than three short
bullets at once. Reserve the lower region for captions; move overlays instead of obscuring
approval buttons or warnings. Check readability at a 720p playback size. Use one subtle
transition language; no busy mascot animation during detailed component inspection.

## 6. Architecture animation: precise layer plan

The existing [architecture SVG](assets/asset-shepherd-aws-architecture.svg) is a layout reference,
**not a current video-ready source**: it still marks deployed authentication/external OpenAI
work as future and depicts Bedrock as the sole runtime model path. Rebuild its semantic layers
before recording. Do not simply animate that outdated image. This document specifies the new
asset; it does not claim those new frames have already been produced.

Use a fixed 16:9 canvas. White or very light service field, AWS boundary, category-colored
service boxes, dark text; a mint outline highlights the just-added layer. Use official AWS
architecture icons only with the applicable usage guidance, or neutral labeled boxes. Product
code (Strands workflow/tools/renderer) has a separate border so it is not mistaken for an AWS
managed service. Do not put external OpenAI inside the AWS boundary.

| Frame | Reveal / emphasis | Connections and precision |
|---|---|---|
| F1 core | Strands workflow, typed GLB tools, headless Chromium renderer | Bidirectional observation/action loop. Label as application components, not separate microservices. “1 · Prove the workflow.” |
| F2 hosted compute | AWS boundary; browser outside; ECS Express and AgentCore inside | Put workflow/tools/renderer within AgentCore. Browser ↔ ECS via HTTPS. ECS → SQS → Lambda → AgentCore via IAM-authorized runtime API. Label ECS “Web UI + target intake”; avoid invented WebSocket/direct browser-to-AgentCore path. |
| F3 durable work | S3 and DynamoDB below the compute row | ECS and runtime ↔ storage. S3: GLBs, evidence, sessions. DynamoDB: workspace, command receipts, spend state. Queue contains command envelopes, not 30 MB assets. Browser polls ECS for status. No S3-direct upload arrow unless implementation changes. |
| F4 operations | Cognito; IAM boundary; Secrets Manager; CloudWatch/SNS; small release strip | Cognito sign-in relates to browser/web, not GLB mutation. Secret-access arrows only to web/runtime. Observability edges dotted; source→CodeBuild→ECR→web/runtime edges dashed and marked build-time. Spend safeguards use existing app/Dynamo state, not an invented billing service. |
| F5 providers | Bedrock/Kimi inside AWS; OpenAI/Luna outside | Both web intake and runtime call the selected provider. Highlight external Luna HTTPS line, keep Kimi alternative muted; no automatic-fallback arrow. Secret→backend credential-access edges are distinct from asset/model-data flows. Label external model billing separate. |

Keep a detailed master with every relationship, but use a focused crop/highlight for each 12-second
video beat. At F5, retain at least three seconds on a simplified readable final view. The detailed
master goes in Devpost/repo. Do not make a service-name word cloud: the viewer should understand
where a request runs, where files live, and where inference occurs.

**Do not add for visual prestige:** App Runner, Kubernetes, Step Functions, RDS, CloudFront,
Route 53/custom domain, Lambda geometry processing, hosted Blender, private per-user tenancy,
or Meta production routing. They are not the demonstrated deployment. ALB/TLS and ECS task
compute can stay inside the ECS Express abstraction; if expanded in the master, verify against
the deployed template rather than guessing subnets/private endpoints.

“Piece by piece” is an explanatory reveal of what we built, not a claim that this was the literal
chronological deployment order. Optional future work belongs in the written roadmap, not a
dashed box that steals the final video seconds from the functioning product.

## 7. Claim and evidence register

| Claim | Evidence / disposition | Approved pitch wording |
|---|---|---|
| Audience size | SlashData Q1 2024 estimate; professionals/hobbyists/students, not just 3D or indie | Historical broad population; narrow our initial audience explicitly |
| Founder credibility | Owner confirms engineering/product-development background, not digital art, and firsthand concept-to-game frustration | Practitioner-built guidance across existing supported repair tools; no invented art credentials |
| Headphones selection | User visual success report; exact run artifacts pending | “Selected the headphone parts” only against actual recorded proposal/result; exact count held |
| Working exported asset | Must record completed download and reopen same file | “A changed 3D asset, not advice” after V10/V11 proof |
| Other capabilities | Existing source and real validation records | Supported bounded capabilities, not universal mesh repair |
| Luna performance | User-reported hosted successes: tablet, riding crop, multi-part headphones, separate headphones; no complete unbiased ledger assembled | “Strong results in our hands-on asset tests”; no percentage |
| Kimi acceptance | D094's selected compatible passing runs, 8/8 safety and semantic gate | Small curated acceptance gate, not production success rate; don't transfer to Luna |
| Best price/performance | Not established by complete comparable evidence | “We optimize completed-task value”; measure cost including failed/retried work |
| Speed comparison | D092 collar: Kimi was faster than Luna in that specific run, Luna included recovery | No blanket Luna-is-faster claim |
| Cost per run | Must include intake/workflow/refinement, input/output/reasoning/cache accounting where reported and pricing date | Say “estimated model cost”; separate hosting, credits and provider invoice |
| AWS implementation | Current technical guide, CloudFormation templates, D103–D125 deployment records | AWS-hosted application; external OpenAI inference; Bedrock alternative |

Sources checked September 7, 2026:

- [SlashData game-developer population estimate](https://www.slashdata.co/post/there-are-11-1-million-game-developers-in-the-world).
  Use the attributed number in our own card. It is not a surveyed count of people with this
  exact problem, nor a forecast of our paying market.
- [Current technical guide](TECHNICAL_GUIDE.md), [project evidence](PROJECT_STATUS.md),
  [model acceptance methodology](../validation/provider-acceptance/README.md),
  [headphones source/runbook](../validation/benchmarks/gaming-peripherals-headphones/README.md).

For a later startup deck, estimate the actual addressable subset through customer interviews
and workflow adoption data. Do not calculate an invented market value by multiplying 11.1M by
a hypothetical subscription. The contest video needs a credible specific audience, not a fake TAM.

## 8. Contest and final-export checklist

The [official rules](https://agentsforhumans.devpost.com/rules), checked September 7, require a
video no longer than five minutes, a working demonstration, and a pitch explaining the problem,
audience, and importance. Screen recordings, slides, and voiceover are allowed; appearing on camera
is optional. Upload to **public YouTube or Vimeo**. English or an English translation is required.
The project must function as depicted. The submission also needs a public licensed repository,
architecture diagram, and working judge access with private credentials where needed. This
script addresses video planning; it does not certify the complete entry. Recheck rules before
submission. The [organizer FAQ](https://agentsforhumans.devpost.com/details/faqs) reinforces
the demo-plus-pitch requirement.

Producer checks (our recommendations, not additional contest rules):

- [x] Confirm founder background and the meaning of bundled repair actions.
- [ ] Lock exact successful headphones run or choose the honest fallback.
- [ ] Save source/output hashes, run evidence, and continuous master before deleting anything.
- [ ] Resolve the rejected-candidate screenshot versus final outcome; no disguised failure.
- [ ] Freeze capture build; no mid-recording deployment. Update README's stale Kimi-default sentence
  before public repository footage; technical guide already reflects Luna.
- [ ] Record all footage and five diagram frames; preserve timings in an edit decision list.
- [ ] Rehearse narration at a comfortable pace. The allocated windows are ceilings, not a command
  to rush. If a beat overruns, shorten its words before stealing readable demo time.
- [ ] Keep cuts/speedups honest. If showing duration or cost, use the full run including waits/retries,
  not the edited video's elapsed time.
- [ ] Check public media/asset/music/font rights. Use original or appropriately licensed music,
  softly, or none. Preserve required credits in the video description where appropriate.
- [ ] Hide password manager UI, login emails, API keys, account IDs, private URLs/query strings,
  notifications, browser-control banner, and unrelated projects. Never put judge credentials in video.
- [ ] Export with captions, check spelling/pronunciation, and watch at normal speed on a smaller screen.
- [ ] Check actual container duration, including intro, fades and tail: target 285 seconds,
  never above 300. A standard check is `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 final.mp4`.
- [ ] Upload publicly, then verify logged-out playback, captions, readable UI and final duration.
- [ ] Link video, current architecture, public repo and private judge testing instructions in the
  proper Devpost fields. Verify the judge account works without publishing its credentials.

If the cut runs long, trim in this order: founder montage by 4 seconds; market card by 4;
capability montage by 5; architecture narration by removing the release/ops detail. Keep the
real approval, result inspection, and exported-file reopen. Do not speed-read the final minute
or rely on judges watching beyond five minutes.

## 9. Practical production order

1. Obtain the main run evidence; approve the spoken copy and claims (founder background confirmed).
2. Capture the end-to-end master first. If its result cannot support the story, change the story
   before producing polished graphics or a voiceover that asserts the wrong outcome.
3. Capture reusable result orbits, stills, and the short separate-capabilities montage.
4. Build the corrected architecture master and F1–F5 layers; export video-friendly frames.
5. Record voiceover beat by beat; assemble a rough 4:45 cut with simple text overlays.
6. Verify narration pacing, evidence continuity, rights/privacy, and 720p readability.
7. Polish audio/captions, export, check duration, and perform logged-out public-playback review.

Suggested local production tree (large raw recordings need not enter Git):

```text
demo-output/pitch/
  footage/       V01–V13 + untouched continuous master
  stills/        S01–S09
  graphics/      G01–G05, architecture layers and overlay sources
  audio/         beat-01.wav … beat-18.wav
  edit/          editor project, cut log, music/font attribution
  evidence/      source/output hashes, exact run metrics, recording-build note
  export/        final.mp4, captions.srt, thumbnail.png, public-links.md
```

Retain this script and sanitized evidence in the repo. Keep credentials, personal data, and
unreviewed raw sessions out of both Git and the public video.
