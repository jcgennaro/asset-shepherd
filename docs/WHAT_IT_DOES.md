# What Asset Shepherd does

Asset Shepherd checks whether a GLB will import, look as intended, and remain practical to ship.

| Asset-worker question | What is checked | Why it matters |
| --- | --- | --- |
| Will it import? | Container structure, references, accessors, finite geometry, required extensions, names, and independent consumer loading | Broken references or unsupported data can stop an engine or DCC import before the asset reaches the scene |
| Will it look right? | Intended scale, grounding, upright pose, front/yaw, normals, UV coverage, materials, textures, alpha, and emissive metadata | An asset can import successfully while facing the wrong way, appearing at the wrong size, or rendering differently than intended |
| Is it practical to ship? | Triangle and resource budgets, topology defects, disconnected index topology, unused data, and estimated vertex-cache locality | Defects can cause shading artifacts; excess or poorly organized work can raise memory, draw, and GPU costs |

The agent interprets target-dependent questions from the user's description and recorded evidence.
Deterministic tools supply measurements and invariants, preview exact supported actions, enforce
approval, perform mutations, and verify the result. Unsupported repairs remain explicit findings
rather than hidden changes.

glTF uses +Y as up and +Z as forward. For a yaw check, the agent compares all four
coordinate-labeled views and uses semantic cues such as a face, gaze, controls, or headlights. It
does not infer front from the longest axis. If front is unclear or symmetric, it leaves yaw
unchanged and reports the ambiguity.
