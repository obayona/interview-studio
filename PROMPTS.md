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

---

Implement Phase 9 in the exact plan order: query and maintain the system map,
build the home dashboard from stored process, attempt, and report aggregates,
include score statistics/trends, recent activity, strengths, weaknesses, and
first-run guidance, omit upcoming sessions and interview readiness, verify the
phase, and mark it complete in the plan, task ledger, and map.

---

Remove the browser test harness completely as though it never existed, restore
required process-stage ownership for every persisted attempt, rename the
interview CLI to `interview-engine-usage.py`, verify it works, and add equivalent
standalone usage scripts for the report engine and profile parser.

---

Continue Phase 10, but implement only the VAD and continuous voice-turn slice so
it can be tested and corrected incrementally. Split the remaining system-design
whiteboard work into later subphases.

---

Implement Phase 10A.1 natural long-form voice turns: transcribe bounded rolling
segments without yielding the candidate's floor, start a five-second handoff
countdown after three seconds of silence, show Finish answer only during that
countdown, suspend capture while the interviewer responds, provide explicit turn
feedback, and keep candidate interruption unsupported.

---

Continue with Phase 10B: add the interactive system-design whiteboard, persist
versioned editable scenes and periodic/explicit PNG snapshots, autosave with
optimistic conflict protection, preserve non-system-design interviews, and leave
diagram-aware AI orchestration for Phase 10C.

---

Start Phase 10C and improve the prompts so the concrete system-design exercise starts
early. A couple of setup questions are acceptable, but the interviewer should then ask
the candidate to design a specific system so the whiteboard is used early.

---

Implement Phase 11 secure web deployment in ordered subphases: keep backend and
frontend as sibling applications, compile Astro into a static Nginx image, add
FastAPI session authentication with authoritative environment credentials, CSRF
and authenticated WebSockets, add Docker Compose for FastAPI/Nginx/Certbot and
explicit schema jobs, validate a documented `.env.example`, bootstrap and renew
Let's Encrypt TLS, add persistent volumes and safe backup/restore/upgrade tooling,
verify the full deployment, and synchronize all SDD governance documents.
