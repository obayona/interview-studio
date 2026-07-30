Create a detailed implementation plan so that an AI agent (codex with GTP 5) is able to develop the project and all the functionalities described in the file @AGENT.md For now, do not create code, just create the complete implementation plan.

---

The interview engine should not be installable, for now it is just a backend module, that can be imported without changing sys.path

---

add a simple script on [cli](backend/cli/) that generates a graph.png image of the graph. Then, add the graph image reference on the readme

---

Correct Phase 2 resume behavior by adding an interview-history endpoint. If the
client retrieves history it should resume without sending `session.start`;
otherwise it sends `session.start`. A resumed client can send `user.text`
directly.

---

Consolidate the Phase 3 settings wiring so `main.py` exposes one application
settings service. Keep the repository private behind that facade and update all
routes and consumers accordingly.

Keep secret handling simple: remove legacy plaintext-secret migration and only
encrypt values when settings are written.

Centralize setting definitions so API-to-database mappings and repository known
keys are derived from one registry instead of repeated string mappings.

Simplify the registry further: use one flat `key_name` directly for persistence
and API mapping, while higher-level classes may retain conceptual grouping.

Remove the current development database settings; backward compatibility is not
required while the project is still in development.

Expose definition metadata through `SettingKey` properties and provide a helper
for key-only iteration, keeping one source dictionary.

---

Implement Phase 8 evaluation and feedback: evaluate completed attempts only,
redirect completed interviews to a request-bound feedback page, persist fully
validated versioned reports with transcript evidence, prevent duplicate
evaluations, support retry without partial storage, add process-detail evaluation
actions, and deterministically consolidate the highest-scoring attempt per
enabled stage into process feedback.
