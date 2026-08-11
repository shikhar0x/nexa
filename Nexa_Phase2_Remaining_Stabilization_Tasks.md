# Nexa Phase 2 Remaining Stabilization Tasks

> **Status**
>
> -   ✅ Fix #1 -- Central Path Resolver **Completed**
> -   ✅ Fix #2 -- Follow-up Context & Pending Skill Continuation
>     **Completed**
>
> The following tasks remain before considering Phase 2 fully complete.

------------------------------------------------------------------------

# Fix #3 --- Recursive Filename Search

## Objective

Audit and improve `OsWalkSearchBackend.search_filenames()`.

## Requirements

-   Search recursively using `pathlib.Path.rglob()`
-   Support case-insensitive matching
-   Support fuzzy substring matching
-   Support arbitrary search roots
-   Never rely on `os.listdir()`

### Expected Matches

Query:

`DBMS`

Should match:

-   `Resource Book DBMS.pdf`
-   `dbms_notes.docx`
-   `Database Management Systems.pdf`

### Supported Queries

-   Find files related to Telegram
-   Find PDF files
-   Find README
-   Find report

### Debug Logging (`NEXA_DEBUG`)

Log:

-   Search root
-   Normalized query
-   Files scanned
-   Matches found

### Verification

-   Add recursive search regression tests
-   Run full test suite

------------------------------------------------------------------------

# Fix #4 --- Automatic Filename Resolution

## Objective

Allow filename-only operations without requiring full paths.

### Current

    summarize ~/Downloads/report.pdf

### Desired

    summarize report.pdf

### Behaviour

If only a filename is supplied:

1.  Search known directories
2.  If exactly one match exists
3.  Resolve automatically
4.  Execute requested action

If multiple matches exist:

    I found multiple files named report.pdf.

    1. ...
    2. ...
    3. ...

    Which one would you like?

Never guess.

Never invoke the LLM.

Reuse `OsWalkSearchBackend`.

### Tests

-   Single match
-   Duplicate filename
-   Missing filename
-   PDF
-   DOCX

Run all tests.

------------------------------------------------------------------------

# Fix #5 --- Unified Filesystem Utilities

Audit every filesystem skill.

Create one shared utility exposing:

-   `resolve_path()`
-   `expand_special_folder()`
-   `expand_relative_path()`
-   `expand_filename()`
-   `validate_exists()`
-   `normalize_directory()`

Ensure these all use the shared helper:

-   DirectoryListingSkill
-   FileReaderSkill
-   OpenFileSkill
-   FileSearchSkill
-   FileContentSearchSkill
-   OsWalkSearchBackend

Remove duplicated implementations.

Run all tests.

------------------------------------------------------------------------

# Fix #6 --- Better Natural Language Argument Extraction

Support:

-   Downloads
-   Desktop
-   Documents
-   Pictures
-   Videos
-   Music
-   Templates
-   home directory
-   current directory
-   parent directory
-   this folder
-   that folder
-   my downloads
-   downloads folder
-   desktop folder
-   documents folder

Examples:

-   List files in Downloads
-   Open Desktop
-   Search Documents
-   Summarize report.pdf from Downloads

Create regression tests.

Run full suite.

------------------------------------------------------------------------

# Fix #7 --- Filesystem Working Context

Remember the most recently used directory after a successful filesystem
operation.

Example:

    List Downloads

↓

Remember:

    ~/Downloads

Later:

    Summarize report.pdf

↓

Automatically resolve inside `~/Downloads`.

Likewise:

    Search Documents

↓

Remember Documents.

    Open report.docx

↓

Search Documents first.

Requirements:

-   Deterministic implementation
-   No LLM involvement
-   Configurable timeout
-   Unit tests

------------------------------------------------------------------------

# Fix #8 --- Better Failure Recovery

Replace generic failures with intelligent recovery.

Instead of:

    Path not found.

Return:

    Did you mean:

    ~/Downloads

Use fuzzy matching against:

-   Special folders
-   Existing directories
-   Current working directory

Example:

    Open Downlods

↓

    Did you mean Downloads?

Never hallucinate.

Add regression tests.

------------------------------------------------------------------------

# Fix #9 --- Prompt-Based Regression Suite

Create:

`tests/prompts.json`

Example:

``` json
[
  {
    "input":"List files in Downloads",
    "expected_skill":"DIRECTORY_LISTING"
  },
  {
    "input":"Find DBMS files",
    "expected_skill":"FILE_SEARCH"
  },
  {
    "input":"Summarize report.pdf",
    "expected_skill":"FILE_READ"
  },
  {
    "input":"run pwd",
    "expected_skill":"RUN_COMMAND"
  }
]
```

Build a test runner that verifies:

-   Intent
-   Dispatched skill
-   No fallback to GENERAL

Integrate with unittest.

------------------------------------------------------------------------

# Fix #10 --- Phase 2 Reliability Audit

Perform a complete reliability audit.

Focus only on stabilization.

Audit:

-   Dispatcher
-   Intent routing
-   Skill execution
-   Conversation context
-   Path resolver
-   File search
-   Directory listing
-   File reader
-   Shell execution
-   Grounded interpretation

Tasks:

-   Remove dead code
-   Remove duplicated logic
-   Improve logging
-   Verify every supported prompt executes the correct skill

Run:

``` bash
venv/bin/python -m unittest discover tests
```

Deliver:

-   Issues fixed
-   Architectural improvements
-   Remaining known limitations
-   Phase 2 completion assessment

Do **not** add new capabilities.
