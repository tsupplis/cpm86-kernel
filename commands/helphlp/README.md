# HELP source standard

The same presentation rules apply to all three kernel projects.

- Store `help.dat` as UTF-8/ASCII text with LF line endings, spaces and host EOF.
  The index recipe creates a CRLF temporary copy for the native HELP compiler.
- Use uppercase topic names. Level-one markers start at column 1; each deeper
  level adds four spaces before `///`. Keep the existing topic hierarchy.
- Indent body text by four spaces. Preserve internal table columns and command
  literals. Use one blank line between paragraphs and before the next topic.
- Use `Syntax:`, `Explanation:`, `Options:` and `Examples:` consistently.
  Informational topics need only the headings that make sense for their content.
- Use braces for optional syntax and literal brackets for bracket options.
  Keep implementation-specific spellings and examples faithful to the parser.
- Share text where command capabilities match. Identify genuine platform/version
  differences explicitly; do not advertise another build's unsupported options.
- Keep common DIR help identical; resident extensions belong in DIR RESIDENT.

`make check` verifies this style. `help.hlp` is always generated from `help.dat`;
do not edit the indexed binary. Style checking does not assert runtime parity.
