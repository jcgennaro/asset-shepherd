# Browser regression fixtures

From the repository root, run `uv run python -m http.server 8012 --bind 127.0.0.1` and open
`http://127.0.0.1:8012/tests/browser/workflow_activity.html`.

This fixture loads the real application script and stylesheet. Its commands and activity responses
are simulated in the browser; it never calls a provider or changes a real workspace.

1. Leave Hosted command checked and click Start Shepherd. Check visible progress must report PASS
   for QUEUED with zero activity requests and a visible mascot.
2. Select RUNNING, then RECONNECTING. Allow one status poll after each selection; Check visible
   progress must report PASS with the appropriate text and the mascot still visible.
3. Select FAILED. The working indicator must stop, the error must appear, and Start Shepherd must
   become usable again. Check visible progress must report PASS.
4. Select SUCCEEDED and click Start Shepherd again. Completion must reload the same notebook URL
   and show `PASS: reloaded saved results at the same notebook URL`.
5. On the reloaded page, uncheck Hosted command and click Start Shepherd. The empty initial local
   activity response must not erase progress. The next response shows Measuring the GLB; Check
   visible progress must report PASS with more than one activity request and no command requests.

Close the fixture tab and stop its temporary HTTP server after testing.
