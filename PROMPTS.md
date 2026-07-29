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
