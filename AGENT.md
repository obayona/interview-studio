# Project: Interview Studio

## Agent Role:
AI Engineer, Full-Stack Engineer.

---

## Main goal:

Develop a web app for developers to practice technical interviews with AI.
Main feautures:

- Read job listing.
- Research about company.
i User can submit CV (pdf), portfolio (web site), LinkedIn profile
- Generate interview plans.
- Simulate Behavioral interviews.
- Technical and Expirience interviews.
- System design interviews.
- Evaluate interview answers.
- Provide feedback and useful advices.
- Configurable: users enter their own API keys from an AI provider.
- TTS and STT support, they can be disable so it can support 4 combinations:
    - bot voice + user speak (full tts and stt)
    - bot text + user speak
    - bot voice + user write
    - bot text + user write (text based chat)
- Storage of all interviews.

---

## General Consideration:

These rules apply always for all the phases and features:

- Priorize good practices and security.
- Priorize simplicity, intuitive UI and easy to understand.
- Show confirmation messages (no alert()).
- Include empty placeholders if there is no data.
- Use Font Awesome. 
- Don't break previous features.
- Kepp visual consistency.
- Priorize Accessibility.
- Priorize components reuse.

---

## General Architecture:

### Backend:

Will include:

- Interview Engine
- Database management
- AI integrations
- No authentication, the app is intented to be used for a single user
- Profile management

### Frontend:

SPA with these pages/sections:

- Profile for enter developer info.
- Page to create interviews:
    - Enter job listing text
    - Enter company url (optional)
- Page to list interview processes.
- Interview processess page that allows to:
    - start a specific interview (behavioural, techincal, system desgin etc)
    - review feedback of past interviews
    - review past interviews (transcriptions)
- Config page:
    - Enter AI providers keys
    - Enable TTS or STT
    - General settings
- home page:
    - page the user see for the first time.
    - contains suggested steps (complete developer profile, enter API keys)

### Desktop Shell/Wrapper

This app will have a desktop app shell that the user can install. The installation will download dependencies, create the Database, run migrations and create a native executable integrated on the user OS (app icon, uninstaller, etc).

The executable will init the backend and render a browser tab that looks like a native app.

The idea is that users can easily start using the app. So it can be installed locally using the installer or it can be deployed as a regular web app on a server.

---

## App Features:

### PHASE 1:
- Interview Engine
- Inside the backend folder, create the interview_engine python package
- Propose a LangGraph architecture
- The graph will be responsible to generate the questions
- The interview should be based on these params:
    - developer/candidate profile
    - job listing
    - company info
    - interview type (behavioral, techincal, system design, , screanning, etc)
    - interviewer type/profile: HR recruiter, tech lead, ceo, cto, etc
    - difficulty level: junior, mid, senior, staff 
    - user instructions, the user can include optional notes like "I would like the interview includes questions about LangGraph"
- It should have a state to know if the interview continues or it ends.
- To stop the model can consider time ellapsed (stored on the state), or topics covered, or number of questions already done
- It should have follow-up questions, not only ask predefined questions
- Use stream_mode="messages" on langgraph to stream token by token
- It will be text based only for now, the STT and TTS would be added later but take into account this, so you can add abstractions
- Consider that when TSS and STT is enable both, the audio and text/transcriptions would be streammed/received
- It should support natural interruptions (optional, let me know how hard it is to implement this)
- Add the sqlite checkpointer.
- The python package should have a builder to instantiate the engine, use a fluid api with defaults (example engine.set_openai_api("").set_model("gpt-4o-mini").build())
- The checkpointer should be a builder param (set_checkpointer(checkpointer)) but the default is the MemorySaver
- It should be able to generate the first greeting and introduction message
- The interview loop would be on another place, this package only use langgraph to generate questions/comments and decide when to stop
- You can create templates to guide the interview generation, so you have to research how to conduct interviews, best practices for interviewers and current trends. The system prompt should be really well crafted
- Use the .venv virtual env for python
- setup linters and follow conventions stated in this file
- add logging, the handler will be handled externally (configure output files, stdout, etc), uses debug() and error() mostly. It should have its own channel like "interview-engine".
- Implement `backend/cli/interview-engine-usage.py` to exercise the interview engine from the terminal. Add equivalent standalone usage scripts for the report engine and profile parser.

### PHASE 2:
- Web wrapper of interview engine.
- Setup FastAPI project structure
- Create migrations folder, uses yoyo library to handle migrations.
- The first migration file should have code to init the checkpointer:

```
    def apply_step(conn):
        """Create LangGraph checkpointer tables using the official setup method."""
        
        # Yoyo passes its own connection, but LangGraph's ShallowPostgresSaver
        # requires its own psycopg3 connection. Open a direct connection.
        db_url = _get_database_url()
        with SQLiteCheckpointer.from_conn_string(db_url) as checkpointer:
            checkpointer.setup()


    def rollback_step(conn):
        """Drop LangGraph checkpointer tables."""
        cursor = conn.cursor()
        
        # Drop tables in reverse dependency order
        cursor.execute("DROP TABLE IF EXISTS checkpoint_writes;")
        cursor.execute("DROP TABLE IF EXISTS checkpoint_blobs;")
        cursor.execute("DROP TABLE IF EXISTS checkpoints;")
        cursor.execute("DROP TABLE IF EXISTS checkpoint_migrations;")

        
steps = [
    step(apply_step, rollback_step),
]
```
- Create tables for settings, we are not going to use env variables or .env files, API KEYS are fetched from the DB. You can create a class to access settings.
- The config class should be very easy to use like the Laravel config('ai.api_key'), it is not necessary to implement the string path, but the idea is that it is an store easy to use
- Init DB pool, config, logging, etc
- Implement a websocket endpoint for the interview process
- Implement a small / root endpoint to serve a index.html
- For development I will provide you the keys on a .env file but it is only for you to be able to run and test the code, the backend will uses the DB
- The database name can be hardcoded on the config class, no paswword needed
- If API keys are missing, the backend still should be able to boot however the specific endpoints would fails. I think you can create a convenient method to check if all required settings are not empty. This could be used on the UI to disable different sections.
- In principle, the services that depends on settings should read the config before instantiate because the user could change the settings

### PHASE 3:

- Settings endpoints
- Add a CRUD for the settings, where the user can enter required API keys.
- Add migrations if necessary
- Another setting is toggle STT and TTS


# PHASE 4:
- Initial Frontend.
- Based on prototypes to create the Astro project. Follow the conventions stated in this file
- Start with minimal shared components, css variables, support for dark mode
- Create empty pages, but make sure the routes works and the transitions are smooth, the side menu and header should remain fixed
- Implement the settings page @prototypes/ai_configuration_interviewos/screen.png
- Integrate it with the backend, remember we will start with OpenAI and TTS/STT togles
- The rest of the pages will be implemented later

### PHASE 5:
- Create the full profile feature @prototypes/candidate_profile_interviewos/screen.png
- We will need migrations to store developer profile
- The image will have a reasonable max size and will be stored as bloob on the DB.
- You need additional sections for the work experience and projects
- Changes are stored when user stop typping or leave focus, but a save button will be added too, not the cancel button
- You need to implement another package that uses langgraph to parse the CV and store the data on the DB. If you consider you don't need LLM for this, you can avoid using langgraph and parse it with a library or using conventional ML libraries
- If you use langgraph, you don't need checkpointer


# PHASE 6:
- Implement processes CRUD
- This is the page that list all the processes: @prototypes/interview_processes_interviewos/screen.png
- This is the page with the form to create a process: @prototypes/create_process_interviewos/screen.png
- This is the page to see an individual process: @prototypes/process_detail_interviewos/screen.png
- On the backend add migrations and endpoints
- For sections like the feedback you can add placeholders, since at this point we don't have the feedback
- On the page to create a process I would like the interview stages to be configurable, so you can skip steps
- The user can always skip steps and see the individual interviews even if they are not started, in that case show the status of the interview
- The user can always repeat an interview, you should store repetitions/attempts
- The interviews can be configured, they have defaults but the user can change the level, interviewer type (HR, CTO, etc), optional instructions (empty by default) and all options supported by the interview-engine

# PHASE 7:
- Support for TTS and STT
- Update the interview-engine
- The backend should stream to users text chunks plus audio chunks
- Should perform live transcriptions and voice generation
- don't send every text chunk to the TTS API, you can buffer some text.
- also implement the frontend @prototypes/interview_simulator_interviewos/screen.png
- I am not sure how the natural interruptions would work, not sure if the browser can includes a VAD (silence detector), on the worst case, the user can use a button to start talking and deselect it when it stop talking. Propose ideas and refactor langgraph graph/state
- Remember that all 4 combinations are supported, it would depend on user settings (STT, TTS enabled/disabled, required API keys empty), it would be nice also to have those settings per interview, so before start the interview the user can toggle stt/tts, or even better be able to do this on live interview
- You may need to refactor and define a webhooks protocol with message types ("audio_chunk", "text_chunk", etc)
- Recommend AI providers for this, OpenAI prefered, let me know if you need an additional api key
- Update migrations, you would need references to the checkpoints, so you can associate the interview messages with the process
- You don't need to update the index.html, use the new frontend

### PHASE 8:
- Final report with:
    - Overall score
    - Communication
    - Technical knowledge
    - Problem-solving
    - Confidence
    - Weak topics
    - Strong topics
    - Suggested study plan
    - etc (use your criterion)
- You will need another python package for this, you should use langgraph, it will be similar to the interview-engine
- Propose when this should be run, I think it should be as soon as the interview ends, the user would see a loading animation
- However, if the user close the browser tab, it would be cancelled, so the UI needs a button to evaluate the interview
- create migrations as needed so the report can be associated with the interview.
- I think you don't need checkpointer for this.
- Implement the frontend based on this prototype @prototypes/feedback_report_interviewos/screen.png

### PHASE 9:
- Home page.
- Follow this prototype prototypes/dashboard_interviewos/screen.png
- It will be simpler, we don't need upcomming sessions and interview readiness
- Add simple stats from interview reports, average score, min, max, etc

### PHASE 10:
- system design interview
- This is an extra feature, should not break previous features
- It would work as the regular interview but the frontend includes a white board similar to @prototypes/system_design_simulator_interviewos/screen.png
- The module should generate images from the canvas and send it to the model
- I am not sure how it would work, propose ideas

### PHASE 11:
- Wrap the webapp on a desktop app.
- You can use pywebview to show the frontend on a web-view
- A python build tool to create an installer
- The installer should be simple, the user chose a install path and clicks install
- The installer should install python and packages, the frontend will be pre-build (js, css, html assets)
- The installer will create the DB on the install path
- When the user open the program, it should start the backend and render the frontend
- When the user close the program window, it should stop the server
- I want binaries for windows 64-bit and debian (maybe a .deb)
- The program should integrate with the OS, appear at menus, have icons
- Create a simple unistaller that removes everything from the install path

### PHASE 12:
- Web deployment scripts and containers
- Add docker compose with containers for fastapi app, nginx, certbot (at first should work with http but after the certificate is created, it will use let's encrpt certificate).
- it should be easy to install everything on a server
- the users can access the app from a browser using the domain
- In this case, there should be a way to add basic authentication so only the user can access the app, propose how to do it, maybe at nginx level or app level
---

## Tech Stack:

- HTML5
- CSS3 with BEM methodology (native, no SCSS, less)
- React.js
- Astro with View Transitions API
- Backend language: Python
- Backend framework: FastAPI
- AI orchestrator: LangGraph
- AI Provider: start with OpenAI
- Database: SQLite
- Native libraries for SQLite, no ORM, implement repositories classes
- Yoyo library for migrations
- Candidate tech for App Shell: pywebview

---

## General Preferences:

- Use Clean Architecture.
- Follow SOLID principles.
- Reuse a single DB pool object, pass it to all the classes that depends on it.
- Dependency Injection. Simple, no complex libraries
- Keep web controllers apart from core functinality, implement the Clean Architecture layers.
- Don't exagerate with interfaces, you can have concrete classes, uses criterion
- Update .gitignore when necessary

---

## Design Preferences for the frontend:

- Based on the design prototypes from "prototypes" folder, it is a google stitch design, used as reference, it has errors like incorrect strings and features that are not supported
- They are not perfect, may have consistency issues, uses your criterion
- Also, try to follow Clean Architecture but not too strict, focus more on SOLID Principles

---

## Style Preferences:

- Colors (based on "prototypes" folder) high contrast for accesibility.
- CSS Variables and good practices.
- Dark Mode support
- Use REM units, with base font-size of 10px
- Native HTML5 and CSS3.
- If needed use flexbox and grid layout.
- Responsive UI.

---


## Code preferences:
- Don't mix css code of components, keep them separated. Let Astro bundle the css files.
- Semantic HTML.
- Use always let or const, never var.
- Don't use alert, confirm or prompt, feedback should be done with modal or toast components. You can use the <dialog> html5 element to implement modals.
- Add prevent default on event listeners when necessary.
- Priorize readable and maintainable code.
- If the agent have doubts check project specifications, otherwise ask the user.
- Configure linters, formatters for all languages (js, css, python, etc)
- For python uses type hints as much as possible. Uses the ABC package for interfaces and abstract classes. But informal interfaces are acceptable too.
- Follow best practices for Python
- Implement unit testing for pure functions, don't waste time on complex mocks (AI streamming tokens). It is acceptable to mock repositories. I don't want to have to configure a DB for unit testing. It is also acceptable to mock API of the frontend.
- Implement some integration testings of main features for the backend. For example, simulate a simple interview with 4 question-answer rounds. In this case, you can create a temporal SQLite DB and use real API tokens.
- The idea is that test should be useful and test actual functionality without mocks.
- Regarging e2e test, this could be done with playwright, and we would only have 2 or 3 tests, no more than that. Don't priorize e2e tests, this could be done at the end or even this would never be implemented
- We will work on accesibility checks later


---

## File Estructure:
- prototypes/ images of frontend design
- backend/
- frontend/
- AGENT.md
...

---

## Development Phases:

- Study project charateristics
- Create DB schema
- Follow development phases (App Features section on this file). Stop after a phase to be able to test it, fix and improve. The development will be progressive.
- If something can be optimized, add it to the implementation plan.

---

## Extra considerations:

- Save the implementation plan on PLAN.md file on the project root.
- Store tasks and its state on a file TASK.md on the project root. Anything a task is completed, update the file
- Store each new prompt I enter on a file PROMPTS.md on the project root. Just append the prompt at bottom.

---

## Implementation Mode:
- Only code, minimum comments, self-explanatory code.
- Small explanations of what the code does on the agent chat.
- In case of ambiguity, assume the most simple solution that doesn't break code.
