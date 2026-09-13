sweep18_a18, run 2026-09-13 17:11-17:48, moved here 2026-09-13 18:40.

NOT discarded, and NOT known to be bad. Set aside because its plateau came in at
24.3 s per agent-turn against the 21.4-22.1 band of ctx8192_a12/a24/a36, and the
run that followed it (sweep18_a36) was measured at 2.16x the reference cost with
near-identical action counts -- 39 posts against 33 at round 1. Something on the
machine was taking time that the simulation was not, and a18 sits inside the same
window.

Its BEHAVIOURAL data is unaffected and remains valid: engagement 7.28%, and every
odds ratio (tier, repeat exposure, slot position) is computed within the run and
does not care how long a request took. Only its TIMINGS are in doubt.

Re-run cleanly on an idle machine before using it in any cost curve.
