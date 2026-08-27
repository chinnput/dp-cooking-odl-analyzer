# User Preferences & Coding Guidelines

This instruction set defines the core interaction rules, coding standards, and safety guidelines for the automated AI agent working on this workspace.

---

## 1. Communication & Approval Guidelines (CRITICAL RULE)

- **Ask and Discuss First**: When encountering errors, bug fixes, or proposing architectural changes, ALWAYS analyze, explain, and discuss the plan with the user FIRST.
- **Wait for Explicit Approval**: NEVER modify files or execute corrective terminal commands automatically. Wait for the user's explicit consent (e.g., *"approve"*, *"do it"*, *"แก้เลย"*) before applying changes or executing scripts.

---

## 2. Code Quality & Style Rules

- **Keep Code Simple & Clean**: Avoid over-engineering, unnecessarily complex algorithms, or advanced abstractions. Write simple, readable, and straightforward Python code.
- **Concise & Substance-Focused Communication**: Provide short, substance-focused explanations without unnecessary filler or prose.

---

## 3. Safety, Execution & Dry-Run Operations

- **Non-Disruptive Terminal Operations**: Never run risky system commands (e.g., `shutdown`, `restart`, or killing unrelated processes).
- **Dry-Run Safe Mode**: Provide dry-run options during testing so that live production systems, state files, or external databases are not accidentally mutated or overloaded.

---

## 4. Efficient Incremental Processing & Visibility

- **Avoid Redundant Processing**: Use state tracking (e.g., `sync_state.json`) to skip previously processed files and focus only on new/incremental real-time updates.
- **Clear Terminal Visibility**: Output clear, item-by-item status logs on the terminal so the user can easily verify data correctness and progress at a glance.
