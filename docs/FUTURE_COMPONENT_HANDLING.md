# Future Component Labeling and Removal

**Status:** First bounded slice implemented; semantic labeling and broader layouts remain deferred
**Decision:** [D062](DECISIONS.md#d062--add-agent-selected-exact-component-removal)
**Purpose:** Preserve a concrete design for safely handling assets that contain unwanted disconnected
geometry without turning “disconnected” into an automatic deletion rule.

## Problem

A GLB can contain one node, one mesh, and one primitive while still drawing several separate forms.
The riding-crop validation case contained three visible crops in that shape. Asset Shepherd's
position-projected topology probe correctly measured three edge-connected forms, and the workflow
agent correctly determined that the confirmed one-crop target was not satisfied.

That measurement is not enough to authorize deletion. A connected topological component is not a
semantic piece: layered shells, buttons, eyes, greebles, teeth, paired objects, and deliberately
separate hard-surface details may all be valid disconnected geometry.

## Implemented bounded capability

Asset Shepherd now has a bounded **component selection** capability with two distinct phases:

1. A read-only labeling tool inventories and visualizes components.
2. A separately authorized mutation tool removes only the exact labeled components approved by the
   user.

The workflow agent decides whether the inventory appears inconsistent with the confirmed target and
whether removal should be proposed. Deterministic tools identify geometry and enforce the exact
mutation; they never decide that a component is unwanted.

## Read-only component inventory

For each supported triangle primitive, the sensor projects byte-identical positions to avoid
mistaking UV or normal seams for separate forms, then enumerates vertex-connected triangle sets.
Every set receives
a stable source-bound identifier such as:

```text
component-r0-m000-p000-c002-4e91ad7b
```

The current identifier binds mesh and primitive indices, deterministic ordinal, and canonical
triangle membership; the containing inspection binds it to the source SHA-256. Each record includes:

- triangle and referenced-vertex counts;
- local bounds, centroid, and percentage of its primitive, projected into world-space viewer boxes;
- skin, morph-target, compression, and extension involvement;
- bounded scale-relative near-contact AABB group probes; and
- front, right, back, and left source evidence required before an agent selection.

The 3D viewer lets the user hover or focus a label while showing a wireframe box
around that exact component. The workflow agent receives the same labeled views plus the structured
inventory. It may call a component a probable duplicate or unwanted form, but it must preserve the
distinction between that semantic judgment and the topological measurement.

## User interaction and authorization

When the agent proposes removal, the approval surface should state one exact consequence, for
example:

```text
Keep C1. Remove C2 and C3 (two probable duplicate crops).
```

The user can accept, reject, or comment on each proposed selection. A comment starts another agent
turn with the same immutable source and component inventory. Execution requires an approval record
containing the source hash, component IDs to keep and remove, plan hash, and agent assessment ID.

There is no automatic “remove small islands,” “keep the largest,” or “delete all extras” option. The
tool must refuse to remove every visible component or any component whose identity changed since
approval.

## Current mutation boundary

The safest first implementation should support only unskinned, non-morphing, uncompressed triangle
primitives with fully understood attributes and extensions. Within an affected primitive it may:

1. filter only triangles belonging to the approved component IDs;
2. append one replacement index accessor while leaving vertex compaction to a separate turn;
3. preserve primitive material assignment and all unrelated nodes, meshes, buffers, images,
   textures, samplers, extras, and extensions; and
4. write a new versioned candidate rather than modifying R0.

The tool must stop when a component involves unsupported compression, sparse or unknown accessor
semantics, skins, morph targets, animation dependencies, or an extension whose references cannot be
proven safe. Empty-node/resource cleanup is a separate operation and must not occur implicitly.

## Verification

Independent verification must prove:

- the source hash and bytes remain unchanged;
- only approved component IDs are absent;
- every retained triangle corner and vertex attribute is preserved exactly;
- material slots, UVs, normals, tangents, textures, images, and extension payloads remain valid;
- the candidate independently parses and reloads;
- expected component count and world bounds are recomputed rather than copied from the plan;
- standardized retained-component and whole-candidate views are nonblank; and
- the workflow agent compares source, labeled selection, and candidate views before recommending the
  result.

A failed visual or invariant check rejects the candidate but does not make it unavailable for human
inspection and download.

## Remaining acceptance and extension cases

Before this capability joins the repair allowlist, it needs at least:

- a real three-duplicate fixture in browser acceptance, beyond the synthetic three-body test;
- an end-to-end hosted rejected-approval run proving no geometry changes;
- a rerun proving the same approved operation is idempotent;
- a layered-shell prop proving disconnected render geometry is not proposed for deletion;
- a legitimate pair or multipart assembly proving semantic piece counts are respected;
- a seam-split mesh proving UV and hard-normal boundaries do not become false components;
- material, texture, attribute, and extension preservation checks; and
- browser acceptance for component highlighting, selection, exact approval, and comparison evidence.

The current tool fails closed outside its narrow static layout. Semantic labels, isolation, multiple
node instances, skins, morphs, compressed accessors, and automatic component repair remain deferred.
