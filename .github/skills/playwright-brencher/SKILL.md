---
name: playwright-brencher
description: "Write or refactor Playwright tests for brencher UI. Use when creating page helpers, extracting browser code from tests, or enforcing set_/verify_ method naming."
---

# Playwright Brencher Conventions

Use this skill when writing or refactoring Playwright tests in this repository.

## Required API Shape

Create and use a context manager in this style:

```python
with brencher_page(APP_URL) as page:
    page.verify_dry_run_on()
    page.set_dry_run_off()
    page.verify_dry_run_off()
```

## Naming Rules

1. Action methods that change UI/application state must use `set_...` names.
2. Verification methods (assertions, waits, checks) must use `verify_...` names.
3. Keep low-level selector helpers private (prefix `_`).
4. Prefer one page-object class per screen/area (`BrencherPage` for the current app page).

## Structure Rules

1. Put shared Playwright helpers in `tests/playwright_helper.py`.
2. Keep tests focused on scenario flow; move DOM selectors and waiting logic into page helper methods.
3. Use context manager functions to own Playwright/browser lifecycle.
4. Inline trivial one-use logic where it improves readability and does not duplicate behavior.

## Method Guidance

Recommended style for page object methods:

- `set_*`: click/toggle/type actions.
- `verify_*`: assert visible state, button title/text, or wait until target state is reached.

Example method names:

- `set_dry_run_off`
- `verify_dry_run_on`
- `verify_dry_run_off`

## Review Checklist

1. Test uses `with brencher_page(...) as page` style.
2. No direct `sync_playwright()` block remains in the test body when helper abstraction is intended.
3. Action and verification methods follow `set_` / `verify_` naming.
4. Selector details are encapsulated in private helper methods.
