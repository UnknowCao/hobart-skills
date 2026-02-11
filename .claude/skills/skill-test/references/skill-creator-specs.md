# Skill Creator Specifications

This document contains the official skill-creator specifications that skill-test validates against. All checks are based on these requirements.

## Table of Contents

- [Skill Directory Structure](#skill-directory-structure)
- [Validation Criteria](#validation-criteria)
  - [1. Structure Validation](#1-structure-validation)
  - [2. YAML Frontmatter](#2-yaml-frontmatter)
  - [3. Naming Conventions](#3-naming-conventions)
  - [4. Content Quality Guidelines](#4-content-quality-guidelines)
  - [5. Scripts Guidelines](#5-scripts-guidelines)
  - [6. References Guidelines](#6-references-guidelines)
  - [7. Assets Guidelines](#7-assets-guidelines)
  - [8. What NOT to Include](#8-what-not-to-include)
- [Progressive Disclosure Patterns](#progressive-disclosure-patterns)
- [Package Validation](#package-validation)

## Skill Directory Structure

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (required)
│   │   ├── name: (required)
│   │   └── description: (required)
│   └── Markdown instructions (required)
└── Bundled Resources (optional)
    ├── scripts/          - Executable code
    ├── references/       - Documentation
    └── assets/           - Output files (templates, etc.)
```

## Validation Criteria

### 1. Structure Validation

**Required:**
- `SKILL.md` must exist in skill root directory
- No unnecessary files (README.md, INSTALLATION_GUIDE.md, CHANGELOG.md, etc.)

**Optional:**
- `scripts/` - For executable code (Python/Bash/etc.)
- `references/` - For documentation loaded as needed
- `assets/` - For files used in output (templates, images, etc.)

### 2. YAML Frontmatter

**Required Fields:**
- `name`: The skill name
- `description`: Clear explanation of what the skill does and when to use it

**Format:**
```yaml
---
name: skill-name
description: Comprehensive description of what this skill does and when to use it. Include triggers, use cases, and scenarios.
---
```

**Description Quality:**
- Must explain both WHAT the skill does and WHEN to use it
- Should include trigger conditions and use cases
- Examples of good descriptions:
  - "Use when Codex needs to work with X files for: (1) Creating new documents, (2) Modifying content, (3) Performing analysis"
  - "Comprehensive X for Y scenarios. Use for: feature implementation, refactoring, optimization"

### 3. Naming Conventions

**Skill Name:**
- Use lowercase letters, digits, and hyphens only
- Normalize to hyphen-case (e.g., "Plan Mode" → `plan-mode`)
- Under 64 characters
- Prefer short, verb-led phrases
- Namespace by tool when clarifying (e.g., `gh-address-comments`)

**File Naming:**
- Follow same conventions as skill name
- Directory named exactly after skill name

### 4. Content Quality Guidelines

**SKILL.md Body:**
- Keep under 500 lines to minimize context bloat
- Use imperative/infinitive form (e.g., "Create X" not "How to create X")
- Avoid template documentation (delete sections about "Structuring This Skill")

**Core Principles:**

1. **Concise is Key**
   - Context window is a shared resource
   - Only add context Codex doesn't already have
   - Prefer concise examples over verbose explanations

2. **Progressive Disclosure**
   - Metadata (name + description): Always in context
   - SKILL.md body: When skill triggers (<5k words)
   - Bundled resources: As needed

3. **Appropriate Freedom Degree**
   - High freedom (text-based): Multiple valid approaches
   - Medium freedom (pseudocode/scripts): Preferred pattern exists
   - Low freedom (specific scripts): Fragile/error-prone operations

### 5. Scripts Guidelines

**When to Include:**
- Same code being rewritten repeatedly
- Deterministic reliability needed
- Repeatedly executed operations

**Examples:**
- `rotate_pdf.py` for PDF rotation
- `fill_fillable_fields.py` for PDF form handling

**Best Practices:**
- Scripts may be executed without loading into context
- Can be read by Codex for patching
- Should be tested for actual execution

### 6. References Guidelines

**When to Include:**
- Documentation Codex should reference while working
- Large content that doesn't fit in SKILL.md
- Domain-specific knowledge (schemas, APIs, policies)

**Examples:**
- `finance.md` for financial schemas
- `api_docs.md` for API specifications
- `policies.md` for company policies

**Best Practices:**
- Keep SKILL.md lean, move detailed info to references
- Avoid duplication between SKILL.md and references
- For large reference files (>100 lines), include table of contents

### 7. Assets Guidelines

**When to Include:**
- Files used in final output, not loaded into context
- Templates, boilerplate code, images, icons, fonts

**Examples:**
- `assets/logo.png` for brand assets
- `assets/slides.pptx` for PowerPoint templates
- `assets/frontend-template/` for HTML/React boilerplate

### 8. What NOT to Include

Do NOT create extraneous documentation files:
- README.md
- INSTALLATION_GUIDE.md
- QUICK_REFERENCE.md
- CHANGELOG.md
- etc.

The skill should only contain information needed for an AI agent to do the job.

## Progressive Disclosure Patterns

**Pattern 1: High-level guide with references**
```markdown
# PDF Processing

## Quick start
Extract text with pdfplumber: [code example]

## Advanced features
- **Form filling**: See skill-creator documentation for complete guide (example only)
- **API reference**: See skill-creator documentation (example only)
```

**Pattern 2: Domain-specific organization**
```
bigquery-skill/
├── SKILL.md (overview and navigation)
└── reference/
    ├── finance.md
    ├── sales.md
    └── product.md
```

**Pattern 3: Conditional details**
```markdown
## Editing documents
For simple edits, modify XML directly.

**For tracked changes**: See skill-creator documentation (example only)
```

## Package Validation

The `package_skill.py` script validates:
1. YAML frontmatter format and required fields
2. Skill naming conventions and directory structure
3. Description completeness and quality
4. File organization and resource references

skill-test should maintain consistency with these validation standards.
