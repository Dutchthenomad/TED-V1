# PR Layout Guidelines for TED-V1

## 1. Commit Structure

- **Backend Changes**
  - Isolate all backend logic, API updates, and database modifications into dedicated commits.
  - Use clear commit messages. Example: `backend: add user authentication flow`
- **Frontend Changes**
  - Bundle all UI/UX, JavaScript, and HTML/CSS updates into separate commits.
  - Use clear commit messages. Example: `frontend: update dashboard layout`
- **Scaffolds (Optional)**
  - If you introduce new project structure, configs, or boilerplate, use a separate commit.
  - Example: `scaffold: initialize Redux store setup`

## 2. Pull Request Description

- Summarize the problem/feature addressed.
- List changes grouped by backend, frontend, and scaffolds.
- Reference related issues (if any).

## 3. Best Practices

- Avoid mixing backend and frontend changes in the same commit.
- Keep commits atomic and logically grouped.
- Rebase and squash as needed before merging.
