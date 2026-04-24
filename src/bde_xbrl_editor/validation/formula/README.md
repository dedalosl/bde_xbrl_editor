# Formula Validation Module Boundaries

Formula validation is intentionally split by responsibility:

- `xfi_functions.py` implements callable XBRL formula functions and keeps access to the current evaluation context.
- `xpath_registration.py` wires those functions into `elementpath` parser instances and handles duplicate or incompatible registration diagnostics.
- `filters.py`, `evaluator.py`, and `details.py` keep formula filtering, assertion execution, and user-facing formatting separate from function registration.

New XFI/EFN/IAF functions should be implemented in `xfi_functions.py` and added to the function spec lists there. Changes to parser wiring, namespace defaults, or custom function registration should go in `xpath_registration.py`.
