[SKILL.md](https://github.com/user-attachments/files/25239090/SKILL.md)
---
name: skill-test
description: Comprehensive skill validation and testing tool using hybrid approach (Python structural checks + AI semantic analysis). Validates skills against skill-creator best practices including naming conventions, YAML frontmatter integrity, content quality, references structure, and script syntax. Generates detailed reports with scoring and actionable recommendations. Use when reviewing newly created skills, validating skill structure before packaging, or performing quality assurance on existing skills.
---

# Skill Test

Comprehensive skill validation and testing tool using a **hybrid detection approach**:

- **Phase 1: Python Structural Checks** - Fast, deterministic validation of file structure, naming conventions, YAML integrity, and script syntax
- **Phase 2: AI Semantic Analysis** - Deep, intelligent analysis of description quality, content clarity, and practicality (when enabled)

## Quick Start

This skill provides two validation modes:

### Mode 1: Structural Checks Only (Fast)
Best for: Quick validation, CI/CD pipelines, pre-commit hooks

```bash
python .claude/skills/skill-test/scripts/test_skill.py <skill-path>
```

### Mode 2: Structural + AI Analysis (Comprehensive)
Best for: Final review, quality assurance, skill improvement

```bash
python .claude/skills/skill-test/scripts/test_skill.py <skill-path> --ai-metadata ./reports/ai-meta.json
```

> **When to use each mode**:
> - Use **structural checks only** for fast feedback during development
> - Use **with AI analysis** when preparing to package/share a skill, or when you want semantic quality feedback

### Examples

```bash
# Quick structural check
python .claude/skills/skill-test/scripts/test_skill.py .claude/skills/my-skill

# Full validation with AI semantic analysis
python .claude/skills/skill-test/scripts/test_skill.py .claude/skills/my-skill --ai-metadata ./reports/ai-meta.json

# Custom output directory
python .claude/skills/skill-test/scripts/test_skill.py .claude/skills/my-skill --output-dir ./reports
```

## Workflow

When a user requests skill testing or review:

1. Identify the skill path - Get the path to the skill directory
2. Run the test script - Execute `test_skill.py` with the skill path and `--ai-metadata`
3. Check for AI metadata marker - Look for `SKILL_TEST_AI_METADATA::` in output
4. If AI metadata exists:
   - Read the metadata JSON file
   - Read the full SKILL.md content
   - Perform AI semantic analysis
   - Append AI analysis results to the report
5. Provide summary - Display terminal output with key findings and report location

## Validation Modules

### Phase 1: Structural Checks (Python)

#### 1. Naming Convention Validation
- Format check (lowercase, digits, hyphens only)
- Length validation (<64 characters)
- Directory name vs YAML name matching

#### 2. Directory Structure Validation
- SKILL.md exists
- No unnecessary files (README.md, CHANGELOG.md, etc.)
- Resource directories (scripts/, references/, assets/)

#### 3. YAML Frontmatter Validation
- Proper `---` delimiters
- Required fields present (name, description)
- No extra fields (only name/description allowed)
- Description quality (trigger/use case information, length)

#### 4. Content Structure Validation
- Body line count (<500 lines recommended)
- Incomplete task detection
- Template documentation patterns (skill-creator sections)
- Usage/trigger information placement (should be in description, not body)
- Imperative language in headings

#### 5. References Validation
- Large file TOC check (>100 lines should have table of contents)
- Deep nesting detection (references linking to references)

#### 6. Script Testing
Supports multiple scripting languages:
- **Python**: Syntax check via `py_compile`, main block detection, --help support
- **Bash**: Syntax check via `bash -n`, shebang validation
- **JavaScript/TypeScript**: Syntax check via `node -c`
- **PowerShell**: Syntax check via `pwsh`
- **Batch**: Basic validation

### Phase 2: AI Semantic Analysis

AI semantic analysis runs in the **main Claude session** (not in the Python script) when this skill is invoked via the Task tool. The Python script generates metadata that the main session uses for deep semantic analysis.

**Analysis Areas** (performed by main session):
- Description quality assessment
- Instruction clarity check
- Practical value assessment
- Structure rationality analysis

> **Note**: This phase is optional. Structural checks alone provide comprehensive validation. Use `--ai-metadata` flag to generate metadata for main session AI analysis.

## Scoring System

The tool calculates a quality score (0-100) with letter grades:

| Score | Grade | Meaning |
|--------|--------|---------|
| 90-100 | A | Excellent |
| 80-89 | B | Good |
| 70-79 | C | Acceptable |
| 60-69 | D | Needs Improvement |
| 0-59 | F | Fail |

**Deductions**:
- Critical issue: -20 points
- Warning: -10 points
- Suggestion: -5 points

## Output Format

The test tool provides three levels of output:

**1. Terminal Summary (user-facing)**
```
============================================================
Test Completed: my-skill
============================================================

Status: WARN
Score: 85/100 (B)
Issues: 0 Critical, 1 Warnings, 1 Suggestions
Report: [skill-test-report-my-skill-20250211-143022.md](...)

Top Issues:
  ⚠ SKILL.md body is 650 lines (recommend <500)
```

**2. Structured Return Value (for main agent)**
```json
{
  "status": "warn",
  "score": 85,
  "grade": "B",
  "report_path": "e:/claude/code/reports/skill-test-report-my-skill-20250211-143022.md",
  "summary": {
    "critical": 0,
    "warnings": 1,
    "suggestions": 1
  },
  "top_issues": [
    "SKILL.md body is 650 lines (recommend <500)"
  ]
}
```

**3. Markdown Report File (detailed documentation)**
Full report saved to `reports/skill-test-report-<skill-name>-<timestamp>.md` with:
- Executive summary with score and grade
- Detailed results from each module
- **AI Semantic Analysis** (if metadata provided)
- Priority recommendations (Critical and Warning sections)
- Conclusion

See [AI Analysis Report Format](references/ai-analysis-report-format.md) for details on the AI semantic analysis section.

**Exit Codes** (returned by the test script):
- `0` - PASS or WARN (skill is usable, may have suggestions)
- `1` - FAIL (critical issues found that must be addressed)

## Best Practices Covered

Based on [skill-creator](references/skill-creator-specs.md) specifications:

- Naming conventions (lowercase, hyphens, <64 chars)
- YAML frontmatter (only name/description, trigger info in description)
- Progressive Disclosure (body <500 lines, use references/)
- Content structure (imperative language, no template docs)
- References structure (one level deep, TOC for large files)
- Script quality (syntax checks, proper shebangs)

## Usage as Subagent

This skill is designed to run as a Task/subagent. When invoked, it:
1. Executes the test script
2. Captures all output
3. Returns both human-readable summary and machine-parsable JSON
4. Provides the full report file path for detailed review

## References

- [skill-creator-specs.md](references/skill-creator-specs.md) - Complete validation criteria
- [ai-analysis-report-format.md](references/ai-analysis-report-format.md) - AI semantic analysis report format
