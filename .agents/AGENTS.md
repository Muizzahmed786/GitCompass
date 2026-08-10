# Project Rules for GitCompass

## Documentation Maintenance Rules

1. **Maintain `docs/DECISIONS.md`**:
   - Whenever any library is chosen, architectural trade-off accepted, or code structure modified, you MUST log the decision in `docs/DECISIONS.md`.
   - Explain why library A was chosen over library B, and what trade-offs were accepted.

2. **Maintain `docs/FLOW.md`**:
   - Whenever introducing or modifying execution paths, endpoints, services, or UI components, you MUST update `docs/FLOW.md`.
   - Clearly document how execution travels between files, functions, and modules (what calls what, in what order).
   - Update the **Current Execution Path Under Modification** section in `docs/FLOW.md` to reflect the specific files and functions being modified during your task.

3. **Maintain `docs/FILE_CONTRACTS.md`**:
   - Whenever creating a new file or modifying an existing file's interface, you MUST update `docs/FILE_CONTRACTS.md`.
   - Document the file's exact Inputs (function parameters, environment variables, HTTP headers/payloads, props) and Expected Outputs (return values, HTTP JSON responses, rendered JSX components, database mutations, or side-effects).

