---
name: regression-testing-and-changelog
description: Use when fixing bugs or making changes to ensure proper documentation and testing.
---
1. For every bug fix, create a corresponding regression test to verify the fix.
2. Organize tests in a dedicated test file, ensuring each test is isolated and focused on a single issue.
3. Document each fix in the CHANGELOG.md under the appropriate section.
4. Use a consistent format for changelog entries (e.g., '- fix(<function name>): <short description>').
5. Ensure that the changelog is updated with every change made to the codebase.
6. Run all tests after making changes to confirm that existing functionality is not broken.
7. If a test fails, investigate the cause and fix it before proceeding with further changes.

**Self-check:**
- Are there regression tests for each bug fix?
- Is the CHANGELOG.md updated with the latest changes?
