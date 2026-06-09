```markdown
# Hackathon Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns and conventions used in the "Hackathon" Python repository. You'll learn how to structure files, write imports/exports, and follow commit and testing conventions. This guide also provides step-by-step workflows and helpful command suggestions to streamline your development process.

## Coding Conventions

### File Naming
- Use **snake_case** for all file names.
  - Example: `data_processor.py`, `user_authentication.py`

### Import Style
- Prefer **relative imports** within the project.
  - Example:
    ```python
    from .utils import helper_function
    ```

### Export Style
- Use **named exports** (define specific functions/classes to be imported elsewhere).
  - Example:
    ```python
    def process_data(data):
        pass

    class DataProcessor:
        pass
    ```

### Commit Patterns
- Commit messages are **freeform**, with no strict prefix.
- Average commit message length: ~49 characters.
  - Example:  
    ```
    Add user authentication and session management
    ```

## Workflows

### Adding a New Feature
**Trigger:** When you need to implement a new functionality.
**Command:** `/add-feature`

1. Create a new Python file using snake_case (e.g., `new_feature.py`).
2. Implement the feature using relative imports for shared code.
3. Export functions/classes with clear names.
4. Write or update corresponding test files (`new_feature.test.py`).
5. Commit changes with a clear, descriptive message.

### Refactoring Existing Code
**Trigger:** When improving code structure or readability.
**Command:** `/refactor-code`

1. Identify the target files/modules.
2. Refactor code, maintaining snake_case naming and relative imports.
3. Update exports as needed.
4. Run or update tests to ensure functionality.
5. Commit with a message describing the refactor.

### Writing and Running Tests
**Trigger:** When adding or updating tests for your code.
**Command:** `/run-tests`

1. Create or update test files using the pattern `*.test.py`.
2. Write test cases for each function/class.
3. Use your preferred testing framework (none detected, so choose as appropriate).
4. Run tests and ensure all pass.
5. Commit test changes with a descriptive message.

## Testing Patterns

- Test files follow the `*.test.py` naming convention.
  - Example: `data_processor.test.py`
- Testing framework is not specified; use your preferred Python testing tool (e.g., `unittest`, `pytest`).
- Place test files alongside the modules they test or in a dedicated tests directory.

## Commands
| Command        | Purpose                                      |
|----------------|----------------------------------------------|
| /add-feature   | Start the workflow for adding a new feature  |
| /refactor-code | Begin refactoring existing code              |
| /run-tests     | Run or update tests for your code            |
```