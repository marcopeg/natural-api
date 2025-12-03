# Task 006 Plan: Rename "verb" to "method" in Dynamic Prompt Frontmatter

## Goal
Rename the dynamic prompt frontmatter attribute "verb" to "method" throughout the codebase.

## Steps

1. ✅ **Create task plan document**

2. ✅ **Update PromptMetadata dataclass in loader.py**
   - Change `verb: str` field to `method: str`
   - Update comment from "HTTP method" to clarify it's the HTTP method

3. ✅ **Update load_prompts() function in loader.py**
   - Change `metadata.get('verb', 'GET')` to `metadata.get('method', 'GET')`
   - Update log message from `verb=` to `method=`

4. ✅ **Update router.py to use 'method' instead of 'verb'**
   - Change `prompt.verb` references to `prompt.method`
   - Update comments mentioning "verb"

5. ✅ **Update body_validator.py parameter name**
   - Change `verb: str | None = None` parameter to `method: str | None = None`
   - Update all references to `verb` variable to `method`
   - Update error messages and comments

6. ✅ **Update all test files**
   - test_main.py: Change `verb="GET"` to `method="GET"`
   - test_prompt_loader.py: Change `.verb` to `.method`
   - test_executor.py: Change `verb="GET"` to `method="GET"`
   - test_router.py: Change test names and assertions
   - test_body_validator.py: Change parameter names

7. ✅ **Update all prompt files in data/prompts/**
   - Change `verb:` to `method:` in YAML frontmatter
   - Files to update: greet.md, hi.md, and any others with verb attribute

8. ✅ **Update test fixture prompt files**
   - Change `verb:` to `method:` in tests/fixtures/prompts/*.md

9. ✅ **Update documentation in copilot-instructions.md**
   - Replace all references to `verb:` with `method:`
   - Update examples and explanations

10. ✅ **Run tests to verify all changes**
    - Run full test suite: `pytest tests/ -v`
    - Ensure all tests pass

## Acceptance Criteria
✅ All occurrences of "verb" attribute renamed to "method"
✅ All tests pass (104 passed)
✅ Documentation updated
✅ No breaking changes to API behavior (only internal naming change)
