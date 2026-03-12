# Persona
Be concise. No sycophancy. No pandering. Challenge ideas with rationale and verifiable citations.

# Constraints
- Iterations must be small and focused
- Every commit to `main` must contain working code; no commit is fine, broken code is not
- Strictly follow Domain-Driven Design
- Use domain nouns and verbs in all communication; infer them from context rather than requiring explicit declaration
- DDD vocabulary is maintained in `docs/ddd-vocab.md` — consult it and update it continuously

# Iteration flow
When I say "let's start a new iteration":
1. Create `work-log/YYYY-MM-DD/` if it doesn't exist
2. All work logs for that day go in this folder
3. Prepare `iteration-NNN.md` and close the turn


## Rules for the Iteration documents
1. No content may be added before Context is provided
2. JTBD (Jobs To Be Done) must exist before proceeding next
3. Every other section may proceed in any desired manner
4. We may loop back to 1 or 2 any number of times, and then cascade
5. When all iteration tasks are complete:
    1. Assess domain terms that emerged during implementation
    2. Propose additions to `docs/ddd-vocab.md` and await confirmation before writing
6. When I say "let's close this iteration":
    1. Mark incomplete tasks as carried forward (not dropped)
    2. Write a one-paragraph summary in `## Notes` — decisions made, not actions taken

# Testing

## Scratch vs permanent tests
- **Scratch tests** verify that an iteration was implemented correctly. They are disposable: once the implementation is committed, the code is the evidence. Never commit scratch tests.
- **Permanent tests** protect against regression. They cover user-facing behaviour and cross-cutting constraints (mobile layout, auth guards, API contracts). Commit them to their natural homes: `frontend/tests/` for Playwright specs, `backend/tests/` for pytest. These run on every test pass.
- No test artifact (scripts, logs, generated data) may be written to a version-controlled paths.

## Running tests
- Always run permanent pytest as `make test`, with logs at `logs/make-test.log`
- Always run permanent playwright tests as `make test-browser`, with logs at `logs/make-test-browser.log`
- For scratch playwright test, logs must at `frontend/tests/scratch/iteration-NNN/logs/test-name.log`
- The main `playwright.config.ts` excludes `**/scratch/**` via `testIgnore`.
- Use `playwright-scratch.config.ts` to run scratch tests.
- For scratch pytests, logs must at `backend/tests/scratch/iteration-NNN/logs/test-name.log`
- Always run tests before declaring them iteration complete

## Playwright commands
- **Permanent tests**: `make test-browser`
- **Scratch tests**: `cd frontend && npx playwright test --config=playwright-scratch.config.ts 2>&1 | tee frontend/tests/scratch/iteration-NNN/logs/test-name.log`

# Delegation model
- Use Sonnet sub-agents extensively to prevent context rot
- Use intent-based prompts over dictation prompts for sub agents: describe the problem, constraints, existing patterns, and acceptance criteria. Let Sonnet make implementation decisions. Do NOT dictate exact code.
- Do not give programming tasks to Haiku

## Output handling
- Never dump large tool output (diffs, full files) directly into Opus context
- Write tool outputs to `tools/` files and use Haiku/Sonnet sub-agents to extract only the relevant details
- For code review tasks, write the diff to a file and send a sub-agent to analyze it

## Sonnet prompt rules: tool usage
Every Sonnet prompt that involves file modification MUST include this block near the top:
```
TOOL USAGE RULES (mandatory):
- Use the Read tool to read files. Never use cat, head, tail, or Bash for reading.
- Use the Edit tool for all file modifications. Never use sed, awk, or Bash for editing.
- Use the Write tool only to create new files. Never use echo/cat heredoc for writing.
- Use Grep for content search. Never use grep or rg via Bash.
- Use Glob for file search. Never use find or ls via Bash.
- Reserve Bash exclusively for running commands (tests, builds, git).
```
- Without this block, Sonnet defaults to Bash for file ops (sed -i, cat heredoc, grep -r)
- Place the block before the task description; Sonnet prioritizes early instructions
- Tell Sonnet: "Do not pipe make output through tee. Makefile targets already log to logs/ via tee internally. Run make commands bare."
- Sonnet defaults to wrapping shell commands with `2>&1 | tee`, which breaks `Bash(make *)` permission matching

## Sonnet prompt rules: frontend
- State the problem being solved, not just the layout: "Edit must be reachable by thumb in the lower third of the screen" not just "put Edit in the toolbar"
- Say "do not add ARIA attributes beyond what the design mock uses"
- Say "do not duplicate functions that differ by one flag; use a parameter instead"
- Say "only include CSS tokens that are used on this page"
- Explicitly list which routes exist. Sonnet will link to nonexistent routes otherwise.

## Sonnet prompt rules: general
- Name the representation of every domain value: if a field has a fixed set of values, tell the agent to use an enum or constant, not a bare string
- State terminal conditions explicitly: "all mutation methods must reject calls after terminal state"
- If the prompt defines a type or alias, say where it must be used; Sonnet won't wire unused definitions on its own
- Tell test agents to import constants from the source module, not duplicate them
- Specify generic type parameters: `list[dict[str, str]]` not `list[dict]`
- Mark constants as immutable: "use a tuple, not a list" for sequences that must not change
- Name the invalid inputs: "reject empty and whitespace-only strings"
- Say "chain exceptions with `from`"
- List every category of test expected: Sonnet won't infer edge-case tests from happy-path examples
- Extract test data into local variables: any string literal used in both setup and assertion must be defined once at the top of the test; assert full structures (compare dicts) rather than individual field lookups
- Tell Sonnet what each assertion guards against: "assert the dict has exactly these keys and no others" not just "assert it's a dict"
- When sending feedback to Sonnet, state the problem not the solution

# Visual verification
- Use JPEG format to minimize token consumption (quality 20 by default, 40 for more higher resolution)
- Never take full-page screenshots; viewport only
- Wait for CSS/Svelte transitions to complete before capturing. Svelte `transition:fade` starts at opacity 0; capturing immediately after `waitForSelector` will screenshot an invisible element. Add `waitForTimeout` matching the transition duration.

# Debugging discipline
- Before applying a CSS or HTML fix, verify it applies to the project's target platform. Always check browser compatibility against project constraints before proposing platform-specific properties.
- When a fix does not work, research the root cause (web search, MDN) before trying alternatives. Do not guess at CSS/HTML properties.
- Try the simplest CSS fix first. A missing CSS property is more likely than a browser bug.
- When debugging visual issues with screenshots, check for transition/animation timing first. A "missing" element is more likely mid-transition (opacity 0) than a z-index bug.
- Always revert debug color changes before moving on. Do not leave diagnostic artifacts in production code.

# Frontend scratch test patterns
- Scratch tests are capture scripts (`.ts`) or spec files (`.spec.ts`) that screenshot UI journeys
- Use `chromium.launch()`
- Mock auth: `page.route("**/api/v1/me", ...)`, mock iteration detail, mock list
- Screenshots: JPEG quality 20, saved to `tests/scratch/iteration-NNN/screenshots/`

# Writing style
- No dramatic before/after framing, no anthropomorphising the agent, no rhetorical flourish
- Plain, factual, direct. State what the system does, not how remarkable it is
- No em dashes
- No grandiose language. This is a personal project. No "strategic questions", "architectural decisions", "validation spikes", "definitively answers"
- Don't narrate the document ("this spike tests whether..."). Just state what happened
- Use plain verbs: "handles" not "absorbs", "works" not "succeeds", "broke" not "encountered a failure"
- Drop unnecessary formality: "Decisions" not "Architectural Decisions (user-confirmed)", "Build later" not "Future implementation task"
- The doc should not talk about itself. State findings, skip self-congratulation

# Comment style
- State what the code does and why it's correct, not what would go wrong otherwise
- No "don't do X or Y happens" -- just "X owns Y"
- Factual, no hypotheticals. If ownership is clear, the danger is implied

# Interaction patterns
- "?" on a code selection means "explain this to me" -- respond in learning mode (concepts, mechanics, why it exists), not in fix/refactor mode

# Python conventions
- Use `asyncio.TaskGroup` over `asyncio.gather` for concurrent async work. Do not use `gather` in new code.

# Tech stack
- Python 3.13, FastAPI + uvicorn, SQLite (aiosqlite, WAL mode)
- Auth: WebAuthn/passkeys + cookie sessions (itsdangerous)
- Package manager: uv (hatchling build), dev deps in `[dependency-groups]`
- Frontend: SvelteKit 2 + Svelte 5, adapter-static, sveltekit; built with npm in `frontend/`
- Node managed via nvm