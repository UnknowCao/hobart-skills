#!/usr/bin/env python3
"""
Skill Test - Comprehensive skill validation and testing tool.

Hybrid Approach:
  Phase 1: Python structural checks (fast, deterministic)
  Phase 2: AI semantic analysis (deep, intelligent)

Usage:
    python test_skill.py <skill-path> [--output-dir <dir>] [--no-ai]

This script performs comprehensive validation of Claude Skills based on
skill-creator specifications and generates a detailed Markdown test report.
"""

import argparse
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Fix Windows encoding issue
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================

# skill-creator specification requirements
MAX_SKILL_NAME_LENGTH = 64
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9-]+$")
MAX_SKILL_BODY_LINES = 500
MAX_REFERENCE_LINES_FOR_TOC = 100
REQUIRED_YAML_FIELDS = {"name", "description"}
ALLOWED_YAML_FIELDS = REQUIRED_YAML_FIELDS

# Template documentation patterns to detect
TEMPLATE_PATTERNS = [
    r"##?\s*When\s+to\s+Use\s+(?:This\s+)?Skill",
    r"##?\s*Structuring\s+(?:This\s+)?Skill",
    r"##?\s*Bundled\s+Resources?",
    r"##?\s*Anatomy\s+of\s+a\s+Skill",
    r"##?\s*Progressive\s+Disclosure",
    r"##?\s*What\s+(?:to\s+)?Not\s+Include",
    r"##?\s*Skill\s+Naming",
]

# Unnecessary file patterns
UNNECESSARY_FILE_PATTERNS = [
    r"^readme",
    r"^changelog",
    r"^install",
    r"^license",
    r"^contributing",
    r"^authors",
    r"^upgrade",
]

# Script extensions and their checkers
SCRIPT_CHECKERS = {
    ".py": "python",
    ".sh": "bash",
    ".js": "javascript",
    ".ts": "typescript",
    ".ps1": "powershell",
    ".bat": "batch",
    ".cmd": "batch",
}


# =============================================================================
# TERMINAL OUTPUT
# =============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


def print_success(msg: str) -> None:
    """Print success message."""
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {msg}")


def print_error(msg: str) -> None:
    """Print error message."""
    print(f"{Colors.FAIL}✗{Colors.ENDC} {msg}")


def print_warning(msg: str) -> None:
    """Print warning message."""
    print(f"{Colors.WARNING}⚠{Colors.ENDC} {msg}")


def print_info(msg: str) -> None:
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ{Colors.ENDC} {msg}")


def print_phase_header(phase: int, total: int, title: str) -> None:
    """Print phase header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Phase {phase}/{total}: {title}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}\n")


# =============================================================================
# VALIDATION RESULT
# =============================================================================

class ValidationResult:
    """Represents a single validation check result."""

    def __init__(
        self,
        category: str,
        status: str,
        message: str,
        details: str = "",
        line_ref: Optional[int] = None,
        suggestion: str = "",
    ):
        self.category = category  # Module name
        self.status = status  # "critical", "warning", "suggestion", "pass", "info"
        self.message = message
        self.details = details
        self.line_ref = line_ref
        self.suggestion = suggestion

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "line_ref": self.line_ref,
            "suggestion": self.suggestion,
        }


# =============================================================================
# CONTENT EXTRACTORS
# =============================================================================

class SkillContentExtractor:
    """Extracts and parses content from SKILL.md files."""

    def __init__(self, skill_md: Path):
        self.skill_md = skill_md
        self.content = ""
        self.yaml_content = ""
        self.yaml_lines: List[str] = []
        self.body_lines: List[str] = []
        self.all_lines: List[str] = []
        self._load_content()

    def _load_content(self) -> None:
        """Load and parse SKILL.md content."""
        try:
            with open(self.skill_md, "r", encoding="utf-8") as f:
                self.content = f.read()
                self.all_lines = self.content.split("\n")
        except Exception as e:
            return

        # Find YAML boundaries
        yaml_start = -1
        yaml_end = -1

        for i, line in enumerate(self.all_lines):
            stripped = line.strip()
            if stripped == "---":
                if yaml_start == -1:
                    yaml_start = i
                elif yaml_end == -1:
                    yaml_end = i
                    break

        if yaml_start >= 0:
            self.yaml_lines = self.all_lines[yaml_start + 1:yaml_end]
            self.yaml_content = "\n".join(self.yaml_lines).strip()
            self.body_lines = self.all_lines[yaml_end + 1:]

    def get_yaml_field(self, field_name: str) -> Optional[str]:
        """Extract a YAML field value."""
        for line in self.yaml_lines:
            if line.startswith(f"{field_name}:"):
                value = line.split(":", 1)[1].strip()
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                return value
        return None

    def find_line_number(self, pattern: str) -> Optional[int]:
        """Find the line number containing a pattern."""
        for i, line in enumerate(self.all_lines, 1):
            if pattern.lower() in line.lower():
                return i
        return None

    def extract_markdown_links(self) -> List[Tuple[str, str, int]]:
        """Extract all markdown links [(text, url, line_num)]."""
        links = []
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

        for i, line in enumerate(self.body_lines, 1):
            for match in link_pattern.finditer(line):
                text = match.group(1)
                url = match.group(2)
                links.append((text, url, i))
        return links

    def count_body_lines(self) -> int:
        """Count lines in the body (excluding YAML)."""
        return len(self.body_lines)

    def has_pattern(self, pattern: str) -> bool:
        """Check if body contains a pattern."""
        body_text = "\n".join(self.body_lines).lower()
        return pattern.lower() in body_text


# =============================================================================
# PHASE 1: STRUCTURAL VALIDATOR
# =============================================================================

class StructuralValidator:
    """Performs Python-based structural validation checks."""

    def __init__(self, skill_path: Path):
        self.skill_path = skill_path
        self.skill_name = skill_path.name
        self.results: List[ValidationResult] = []

    def add_result(
        self,
        category: str,
        status: str,
        message: str,
        details: str = "",
        line_ref: Optional[int] = None,
        suggestion: str = "",
    ) -> None:
        """Add a validation result."""
        self.results.append(
            ValidationResult(category, status, message, details, line_ref, suggestion)
        )

    def validate_all(self) -> None:
        """Run all structural validation checks."""
        self._validate_naming()
        self._validate_structure()
        self._validate_yaml()
        self._validate_content_structure()
        self._validate_references()
        self._test_scripts()

    # -------------------------------------------------------------------------
    # Naming Convention Validation
    # -------------------------------------------------------------------------

    def _validate_naming(self) -> None:
        """Validate skill naming conventions."""
        print(f"{Colors.BOLD}[1/7] Naming Convention Validation{Colors.ENDC}")

        # Check name format (lowercase, digits, hyphens only)
        if not SKILL_NAME_PATTERN.match(self.skill_name):
            self.add_result(
                "naming",
                "warning",
                f"Skill name '{self.skill_name}' contains invalid characters",
                "Use only lowercase letters, digits, and hyphens",
                suggestion="Rename directory to match format: my-skill-name",
            )
            print_warning(f"Invalid name format: {self.skill_name}")
        else:
            print_success(f"Name format valid: {self.skill_name}")

        # Check name length
        if len(self.skill_name) > MAX_SKILL_NAME_LENGTH:
            self.add_result(
                "naming",
                "warning",
                f"Skill name is {len(self.skill_name)} chars (max {MAX_SKILL_NAME_LENGTH})",
                "",
                suggestion="Shorten the skill name",
            )
            print_warning(f"Name too long: {len(self.skill_name)} chars")
        else:
            print_success(f"Name length OK: {len(self.skill_name)} chars")

        # Check directory name matches YAML name
        skill_md = self.skill_path / "SKILL.md"
        if skill_md.exists():
            extractor = SkillContentExtractor(skill_md)
            yaml_name = extractor.get_yaml_field("name")
            if yaml_name and yaml_name != self.skill_name:
                self.add_result(
                    "naming",
                    "critical",
                    f"Directory name '{self.skill_name}' doesn't match YAML name '{yaml_name}'",
                    "Directory name must exactly match the 'name' field in YAML",
                    suggestion=f"Rename directory to '{yaml_name}'",
                )
                print_error(f"Name mismatch: dir='{self.skill_name}', yaml='{yaml_name}'")
            else:
                print_success("Directory name matches YAML")

    # -------------------------------------------------------------------------
    # Structure Validation
    # -------------------------------------------------------------------------

    def _validate_structure(self) -> None:
        """Validate skill directory structure."""
        print(f"\n{Colors.BOLD}[2/7] Structure Validation{Colors.ENDC}")

        skill_md = self.skill_path / "SKILL.md"
        scripts_dir = self.skill_path / "scripts"
        refs_dir = self.skill_path / "references"
        assets_dir = self.skill_path / "assets"

        # Check SKILL.md exists
        if not skill_md.exists():
            self.add_result(
                "structure",
                "critical",
                "SKILL.md not found",
                "Required file for all skills",
                suggestion="Create SKILL.md with proper YAML frontmatter",
            )
            print_error("SKILL.md not found (required)")
            return
        else:
            print_success("SKILL.md found")

        # Check for unnecessary files
        unnecessary_files: List[str] = []
        for f in self.skill_path.iterdir():
            if f.is_file() and f.name != "SKILL.md":
                # Check against unnecessary file patterns
                fname_lower = f.name.lower()
                if any(
                    re.match(pattern, fname_lower)
                    for pattern in UNNECESSARY_FILE_PATTERNS
                ):
                    unnecessary_files.append(f.name)

        if unnecessary_files:
            self.add_result(
                "structure",
                "warning",
                f"Unnecessary files found: {', '.join(unnecessary_files)}",
                "Skills should only contain SKILL.md and bundled resources",
                suggestion="Delete README.md, CHANGELOG.md, etc.",
            )
            print_warning(f"Unnecessary files: {', '.join(unnecessary_files)}")
        else:
            print_success("No unnecessary files")

        # Report resource directories
        found_dirs = []
        if scripts_dir.exists():
            found_dirs.append("scripts/")
        if refs_dir.exists():
            found_dirs.append("references/")
        if assets_dir.exists():
            found_dirs.append("assets/")

        if found_dirs:
            print_success(f"Resource directories: {', '.join(found_dirs)}")

    # -------------------------------------------------------------------------
    # YAML Frontmatter Validation
    # -------------------------------------------------------------------------

    def _validate_yaml(self) -> None:
        """Validate YAML frontmatter."""
        print(f"\n{Colors.BOLD}[3/7] YAML Frontmatter Validation{Colors.ENDC}")

        skill_md = self.skill_path / "SKILL.md"
        if not skill_md.exists():
            return

        extractor = SkillContentExtractor(skill_md)

        # Check if YAML exists
        if not extractor.yaml_lines:
            self.add_result(
                "yaml",
                "critical",
                "No YAML frontmatter found",
                "Must start with --- delimiters",
                suggestion='Add YAML frontmatter: \n---\nname: my-skill\ndescription: ...\n---',
            )
            print_error("No YAML frontmatter")
            return

        print_success("YAML frontmatter found")

        # Check for extra fields
        extra_fields: Set[str] = set()
        for line in extractor.yaml_lines:
            if ":" in line:
                field = line.split(":", 1)[0].strip()
                if field and field not in ALLOWED_YAML_FIELDS:
                    extra_fields.add(field)

        if extra_fields:
            self.add_result(
                "yaml",
                "warning",
                f"Extra YAML fields found: {', '.join(sorted(extra_fields))}",
                "Only 'name' and 'description' are allowed",
                suggestion="Remove extra YAML fields (keep only name and description)",
            )
            print_warning(f"Extra fields: {', '.join(sorted(extra_fields))}")
        else:
            print_success("No extra YAML fields")

        # Check required fields
        for field in REQUIRED_YAML_FIELDS:
            value = extractor.get_yaml_field(field)
            if not value:
                self.add_result(
                    "yaml",
                    "critical",
                    f"Missing required field: {field}",
                    f"Add '{field}: <value>' to YAML",
                    suggestion=f"Add '{field}' field to YAML frontmatter",
                )
                print_error(f"Missing field: {field}")
            else:
                print_success(f"Field found: {field}")

        # Validate name field matches directory
        yaml_name = extractor.get_yaml_field("name")
        if yaml_name and yaml_name != self.skill_name:
            # Already reported in naming check
            pass

        # Validate description quality
        description = extractor.get_yaml_field("description")
        if description:
            self._validate_description_quality(description)

    def _validate_description_quality(
        self, description: str
    ) -> None:
        """Validate the quality of the description field."""
        desc_lower = description.lower()

        # Check if description mentions "when to use"
        trigger_keywords = ["when", "use", "trigger", "scenario", "context"]
        has_trigger_info = any(keyword in desc_lower for keyword in trigger_keywords)

        if not has_trigger_info:
            self.add_result(
                "yaml",
                "warning",
                "Description lacks trigger/use case information",
                "Description should explain WHEN to use this skill",
                suggestion='Add: "Use when ... for (1) X, (2) Y, (3) Z"',
            )
            print_warning("Description lacks trigger info")
        else:
            print_success("Description includes trigger info")

        # Check description length
        if len(description) < 30:
            self.add_result(
                "yaml",
                "suggestion",
                f"Description is too short ({len(description)} chars)",
                "Description should be detailed enough to explain the skill's purpose",
                suggestion="Expand description with more context",
            )
            print_info(f"Description short: {len(description)} chars")

    # -------------------------------------------------------------------------
    # Content Structure Validation
    # -------------------------------------------------------------------------

    def _validate_content_structure(self) -> None:
        """Validate content structure."""
        print(f"\n{Colors.BOLD}[4/7] Content Structure Validation{Colors.ENDC}")

        skill_md = self.skill_path / "SKILL.md"
        if not skill_md.exists():
            return

        extractor = SkillContentExtractor(skill_md)

        # Check line count
        body_count = extractor.count_body_lines()
        if body_count > MAX_SKILL_BODY_LINES:
            self.add_result(
                "content",
                "warning",
                f"SKILL.md body is {body_count} lines (recommend <{MAX_SKILL_BODY_LINES})",
                "Long content bloats context; use Progressive Disclosure",
                suggestion="Move detailed content to references/ directory",
            )
            print_warning(f"Body too long: {body_count} lines")
        else:
            print_success(f"Body length OK: {body_count} lines")

        # Check for TODO items
        todo_count = extractor.content.count("TODO")
        if todo_count > 0:
            self.add_result(
                "content",
                "warning",
                f"Contains {todo_count} TODO items",
                "Complete all TODOs before using the skill",
                suggestion="Complete or remove TODO items",
            )
            print_warning(f"Found {todo_count} TODOs")
        else:
            print_success("No TODO items")

        # Check for template documentation sections
        for pattern in TEMPLATE_PATTERNS:
            if re.search(pattern, extractor.content, re.IGNORECASE):
                self.add_result(
                    "content",
                    "suggestion",
                    f"Template documentation found: {pattern}",
                    "Remove skill-creator template sections from production skills",
                    suggestion="Delete template documentation sections",
                )
                print_info(f"Template found: {pattern}")

        # Check for "When to Use" section in body (should be in description)
        if extractor.has_pattern("When to Use") or extractor.has_pattern("When to Use This"):
            line_num = extractor.find_line_number("When to Use")
            self.add_result(
                "content",
                "suggestion",
                "'When to Use' section found in body",
                "This information should be in the YAML description, not body",
                suggestion="Move trigger info to YAML description field",
            )
            print_info("'When to Use' in body (should be in description)")

        # Check for imperative language in headings
        for i, line in enumerate(extractor.body_lines, 1):
            if re.match(r"^##+\s+How\s+to\s+", line, re.IGNORECASE):
                self.add_result(
                    "content",
                    "suggestion",
                    "Found 'How to' heading (non-imperative)",
                    "Use imperative form: e.g., 'Create X' instead of 'How to Create X'",
                    suggestion="Change to imperative/infinitive form",
                )
                print_info("Found 'How to' heading")
                break

        # Check for "Resources" section that just describes structure
        if "## Resources" in extractor.content or "### scripts/" in extractor.content:
            self.add_result(
                "content",
                "suggestion",
                "Template 'Resources' section found",
                "Remove sections that just describe the skill structure",
                suggestion="Delete structural documentation sections",
            )
            print_info("Template 'Resources' section found")

    # -------------------------------------------------------------------------
    # References Validation
    # -------------------------------------------------------------------------

    def _validate_references(self) -> None:
        """Validate references directory."""
        print(f"\n{Colors.BOLD}[5/7] References Validation{Colors.ENDC}")

        refs_dir = self.skill_path / "references"

        if not refs_dir.exists():
            print_info("No references/ directory")
            return

        print_success("references/ directory found")

        # Check each reference file
        ref_files = list(refs_dir.glob("*.md"))
        if not ref_files:
            print_info("No .md files in references/")
            return

        print(f"Checking {len(ref_files)} reference file(s)...")

        for ref_file in ref_files:
            # Check line count and TOC
            with open(ref_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                line_count = len(lines)

            if line_count > MAX_REFERENCE_LINES_FOR_TOC:
                # Check for TOC
                has_toc = any("toc" in line.lower() or "contents" in line.lower() for line in lines[:20])
                if not has_toc:
                    self.add_result(
                        "references",
                        "suggestion",
                        f"{ref_file.name}: {line_count} lines (no TOC)",
                        f"Files >{MAX_REFERENCE_LINES_FOR_TOC} lines should have a table of contents",
                        suggestion=f"Add TOC to {ref_file.name}",
                    )
                    print_info(f"{ref_file.name}: No TOC ({line_count} lines)")

        # Check for deep nesting (references linking to references)
        self._check_deep_nesting(refs_dir)

    def _check_deep_nesting(self, refs_dir: Path) -> None:
        """Check for deep nesting in references."""
        # For each reference file, check if it links to other references
        for ref_file in refs_dir.glob("*.md"):
            try:
                with open(ref_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for markdown links to other .md files
                link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")
                for match in link_pattern.finditer(content):
                    target = match.group(2)
                    # Skip if it's a self-reference or external link
                    if not target.startswith("http") and ref_file.name not in target:
                        self.add_result(
                            "references",
                            "warning",
                            f"{ref_file.name} links to another reference: {target}",
                            "References should only be one level deep from SKILL.md",
                            suggestion="Move the linked content directly into SKILL.md or restructure",
                        )
                        print_warning(f"Deep nesting: {ref_file.name} -> {target}")
                        break
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Script Testing
    # -------------------------------------------------------------------------

    def _test_scripts(self) -> None:
        """Test executable scripts."""
        print(f"\n{Colors.BOLD}[6/7] Script Testing{Colors.ENDC}")

        scripts_dir = self.skill_path / "scripts"
        if not scripts_dir.exists():
            print_info("No scripts/ directory")
            return

        print_success("scripts/ directory found")

        # Find all supported scripts
        all_scripts: List[Path] = []
        for ext in SCRIPT_CHECKERS.keys():
            all_scripts.extend(scripts_dir.glob(f"*{ext}"))

        if not all_scripts:
            print_info("No scripts found")
            return

        print(f"Testing {len(all_scripts)} script(s)...")

        for script in all_scripts:
            checker = SCRIPT_CHECKERS.get(script.suffix)
            if checker == "python":
                self._test_python_script(script)
            elif checker == "bash":
                self._test_bash_script(script)
            elif checker in ("javascript", "typescript"):
                self._test_js_script(script)
            elif checker == "powershell":
                self._test_powershell_script(script)
            elif checker == "batch":
                self._test_batch_script(script)

    def _test_python_script(self, script: Path) -> None:
        """Test a Python script."""
        print(f"\n  {Colors.OKCYAN}Testing: {script.name}{Colors.ENDC}")

        # Syntax check
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            self.add_result(
                "scripts",
                "critical",
                f"{script.name}: Syntax error",
                result.stderr.strip(),
                suggestion="Fix Python syntax errors",
            )
            print_error(f"  Syntax error")
            return

        print_success(f"  {script.name}: Syntax OK")

        # Check for main block
        try:
            with open(script, "r", encoding="utf-8") as f:
                content = f.read()

            if '__name__ == "__main__"' in content:
                print_info(f"  {script.name}: Has main block")

                # Try --help
                try:
                    help_result = subprocess.run(
                        [sys.executable, str(script), "--help"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if help_result.returncode == 0 or "usage:" in help_result.stdout.lower():
                        print_success(f"  {script.name}: Supports --help")
                    else:
                        print_info(f"  {script.name}: No --help support")
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
        except Exception as e:
            print_warning(f"  Runtime check skipped: {e}")

    def _test_bash_script(self, script: Path) -> None:
        """Test a Bash script."""
        print(f"\n  {Colors.OKCYAN}Testing: {script.name}{Colors.ENDC}")

        # Syntax check
        result = subprocess.run(
            ["bash", "-n", str(script)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            self.add_result(
                "scripts",
                "critical",
                f"{script.name}: Syntax error",
                result.stderr.strip(),
                suggestion="Fix Bash syntax errors",
            )
            print_error(f"  Syntax error")
            return

        print_success(f"  {script.name}: Syntax OK")

        # Check shebang
        try:
            with open(script, "r", encoding="utf-8") as f:
                first_line = f.readline()

            if first_line.startswith("#!"):
                print_success(f"  {script.name}: {first_line.strip()}")
            else:
                self.add_result(
                    "scripts",
                    "warning",
                    f"{script.name}: No shebang",
                    "Add #!/bin/bash or #!/usr/bin/env bash",
                    suggestion="Add shebang line",
                )
                print_warning(f"  No shebang")
        except Exception:
            pass

    def _test_js_script(self, script: Path) -> None:
        """Test a JavaScript/TypeScript script."""
        print(f"\n  {Colors.OKCYAN}Testing: {script.name}{Colors.ENDC}")

        # Check if node is available
        try:
            subprocess.run(
                ["node", "--version"],
                capture_output=True,
                timeout=2,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            print_info(f"  {script.name}: Node not available, skipping syntax check")
            return

        # Syntax check with node
        result = subprocess.run(
            ["node", "-c", str(script)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            self.add_result(
                "scripts",
                "critical",
                f"{script.name}: Syntax error",
                result.stderr.strip(),
                suggestion="Fix JavaScript/TypeScript syntax errors",
            )
            print_error(f"  Syntax error")
        else:
            print_success(f"  {script.name}: Syntax OK")

    def _test_powershell_script(self, script: Path) -> None:
        """Test a PowerShell script."""
        print(f"\n  {Colors.OKCYAN}Testing: {script.name}{Colors.ENDC}")

        # Check if pwsh is available
        try:
            subprocess.run(
                ["pwsh", "-Version"],
                capture_output=True,
                timeout=2,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            print_info(f"  {script.name}: PowerShell not available, skipping check")
            return

        # Syntax check
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", f"{{ {script} }}"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            self.add_result(
                "scripts",
                "critical",
                f"{script.name}: Syntax error",
                result.stderr.strip(),
                suggestion="Fix PowerShell syntax errors",
            )
            print_error(f"  Syntax error")
        else:
            print_success(f"  {script.name}: Syntax OK")

    def _test_batch_script(self, script: Path) -> None:
        """Test a Batch script."""
        print(f"\n  {Colors.OKCYAN}Testing: {script.name}{Colors.ENDC}")

        # Batch scripts are hard to validate syntactically
        # Just check for basic issues
        try:
            with open(script, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for @echo off (good practice)
            if "@echo off" in content or "@echo ON" in content:
                print_success(f"  {script.name}: Has @echo directive")
            else:
                print_info(f"  {script.name}: No @echo off")

            print_info(f"  {script.name}: Manual review recommended")
        except Exception:
            pass

    def get_results(self) -> List[ValidationResult]:
        """Get all validation results."""
        return self.results


# =============================================================================
# PHASE 2: AI SEMANTIC ANALYZER
# =============================================================================

class AISemanticAnalyzer:
    """Performs AI-based semantic analysis on skill content."""

    def __init__(self, skill_path: Path):
        self.skill_path = skill_path
        self.skill_name = skill_path.name
        self.results: List[ValidationResult] = []

    def add_result(
        self,
        category: str,
        status: str,
        message: str,
        details: str = "",
        suggestion: str = "",
    ) -> None:
        """Add a validation result."""
        self.results.append(
            ValidationResult(category, status, message, details, 0, suggestion)
        )

    def analyze_all(self) -> None:
        """Run all semantic analysis checks."""
        print(f"\n{Colors.BOLD}[7/7] AI Semantic Analysis{Colors.ENDC}")
        print_info("AI semantic analysis runs in main session")
        print_info("(Use --ai-metadata to generate metadata for main session analysis)")

    def get_results(self) -> List[ValidationResult]:
        """Get all analysis results."""
        return self.results


# =============================================================================
# SCORING SYSTEM
# =============================================================================

class SkillScorer:
    """Calculates quality score for a skill."""

    def __init__(self, results: List[ValidationResult]):
        self.results = results

    def calculate_score(self) -> int:
        """Calculate score from 0-100."""
        score = 100

        for result in self.results:
            if result.status == "critical":
                score -= 20
            elif result.status == "warning":
                score -= 10
            elif result.status == "suggestion":
                score -= 5

        return max(0, score)

    def get_grade(self) -> str:
        """Get letter grade."""
        score = self.calculate_score()
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_markdown_report(
    skill_path: Path,
    skill_name: str,
    results: List[ValidationResult],
    report_path: Path,
    duration: float,
) -> None:
    """Generate detailed Markdown report."""

    status_emoji = {
        "pass": "✅",
        "warn": "⚠️",
        "fail": "❌",
        "critical": "❌",
        "warning": "⚠️",
        "suggestion": "ℹ️",
        "info": "💡",
    }

    # Calculate summary
    scorer = SkillScorer(results)
    score = scorer.calculate_score()
    grade = scorer.get_grade()
    critical = sum(1 for r in results if r.status == "critical")
    warnings = sum(1 for r in results if r.status == "warning")
    suggestions = sum(1 for r in results if r.status == "suggestion")

    # Determine overall status
    if critical > 0:
        overall_status = "fail"
    elif warnings > 0:
        overall_status = "warn"
    else:
        overall_status = "pass"

    # Start report
    lines = [
        f"# Skill Test Report: {skill_name}",
        "",
        f"**Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Skill Path**: `{skill_path}`",
        f"**Test Duration**: {duration:.2f} seconds",
        "",
        "## Executive Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| **Overall Status** | {status_emoji.get(overall_status, '?')} {overall_status.upper()} |",
        f"| **Quality Score** | {score}/100 ({grade}) |",
        f"| **Critical Issues** | {critical} |",
        f"| **Warnings** | {warnings} |",
        f"| **Suggestions** | {suggestions} |",
        "",
        "---",
        "",
    ]

    # Group results by category
    categories: Dict[str, List[ValidationResult]] = {}
    for result in results:
        if result.category not in categories:
            categories[result.category] = []
        categories[result.category].append(result)

    # Category titles
    category_titles = {
        "naming": "1. Naming Convention",
        "structure": "2. Directory Structure",
        "yaml": "3. YAML Frontmatter",
        "content": "4. Content Quality",
        "references": "5. References",
        "scripts": "6. Scripts",
        "ai-analysis": "7. AI Semantic Analysis",
    }

    # Generate sections
    for cat, title in category_titles.items():
        if cat not in categories:
            continue

        lines.append(f"## {title}")
        lines.append("")

        for result in categories[cat]:
            icon = status_emoji.get(result.status, "•")
            status_label = result.status.capitalize()

            lines.append(f"{icon} **{status_label}**: {result.message}")

            if result.details:
                lines.append(f"  <details><summary>Details</summary>")
                lines.append(f"  ")
                lines.append(f"  {result.details}")
                lines.append(f"  </details>")

            if result.suggestion:
                lines.append(f"  💡 **Suggestion**: {result.suggestion}")

            lines.append("")

        lines.append("")

    # Add recommendations
    critical_issues = [r for r in results if r.status == "critical"]
    warning_issues = [r for r in results if r.status == "warning"]

    if critical_issues or warning_issues:
        lines.append("## Priority Recommendations")
        lines.append("")
        lines.append("### Critical (Must Fix)")
        lines.append("")

        for i, issue in enumerate(critical_issues, 1):
            lines.append(f"{i}. **{issue.message}**")
            if issue.suggestion:
                lines.append(f"   - {issue.suggestion}")
            lines.append("")

        if warning_issues:
            lines.append("### Warnings (Should Fix)")
            lines.append("")

            for i, issue in enumerate(warning_issues[:5], 1):  # Top 5 warnings
                lines.append(f"{i}. **{issue.message}**")
                if issue.suggestion:
                    lines.append(f"   - {issue.suggestion}")
                lines.append("")

        lines.append("")

    # Conclusion
    lines.append("## Conclusion")
    lines.append("")

    if overall_status == "pass":
        lines.append("✅ **The skill meets all quality standards and is ready for use.**")
    elif overall_status == "warn":
        lines.append("⚠️ **The skill has warnings that should be addressed.**")
        lines.append("")
        lines.append("The skill is functional but would benefit from the suggested improvements.")
    else:
        lines.append("❌ **The skill has critical issues that must be resolved.**")
        lines.append("")
        lines.append("Please fix all critical issues before using this skill.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Generated by skill-test*")

    # Write report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# =============================================================================
# AI METADATA GENERATION
# =============================================================================

def generate_ai_metadata(
    skill_path: Path,
    skill_name: str,
    results: List[ValidationResult],
    report_path: Path,
    metadata_path: Path,
) -> None:
    """Generate AI metadata file for main session analysis."""
    # Read YAML frontmatter and body preview
    skill_md = skill_path / "SKILL.md"
    extractor = SkillContentExtractor(skill_md)

    # Extract YAML fields
    yaml_data = {}
    for field in REQUIRED_YAML_FIELDS:
        value = extractor.get_yaml_field(field)
        if value:
            yaml_data[field] = value

    # Get body preview (first 2000 chars)
    body_text = "\n".join(extractor.body_lines)
    body_preview = body_text[:2000]

    # Summarize structural results
    critical = sum(1 for r in results if r.status == "critical")
    warnings = sum(1 for r in results if r.status == "warning")
    suggestions = sum(1 for r in results if r.status == "suggestion")

    # Build issues list
    issues = [
        {
            "category": r.category,
            "status": r.status,
            "message": r.message,
            "details": r.details,
            "suggestion": r.suggestion,
        }
        for r in results
        if r.status in ("critical", "warning", "suggestion")
    ]

    # Create metadata dict
    metadata = {
        "skill_name": skill_name,
        "skill_path": str(skill_path),
        "yaml": yaml_data,
        "body_preview": body_preview,
        "full_body_path": str(skill_md),
        "structural_results": {
            "critical": critical,
            "warnings": warnings,
            "suggestions": suggestions,
            "issues": issues[:10],  # Top 10 issues
        },
        "report_path": str(report_path),
        "timestamp": datetime.now().isoformat(),
    }

    # Write metadata file
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test and validate Claude Skills (Hybrid: Structural + AI Analysis)"
    )
    parser.add_argument("skill_path", type=Path, help="Path to the skill directory")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./reports"),
        help="Output directory for reports",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip AI semantic analysis (structural checks only)",
    )
    parser.add_argument(
        "--ai-metadata",
        type=Path,
        default=None,
        help="Output AI metadata file for main session analysis",
    )

    args = parser.parse_args()

    # Validate input path
    if not args.skill_path.exists():
        print_error(f"Skill path not found: {args.skill_path}")
        sys.exit(1)

    if not (args.skill_path / "SKILL.md").exists():
        print_error(f"SKILL.md not found in: {args.skill_path}")
        sys.exit(1)

    import time
    start_time = time.time()

    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Skill Test: {args.skill_path.name}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")

    # Phase 1: Structural Validation
    print_phase_header(1, 2, "Structural Validation (Python)")

    structural_validator = StructuralValidator(args.skill_path)
    structural_validator.validate_all()
    structural_results = structural_validator.get_results()

    # Phase 2: AI Semantic Analysis
    all_results = structural_results.copy()

    if not args.no_ai:
        print_phase_header(2, 2, "AI Semantic Analysis")
        ai_analyzer = AISemanticAnalyzer(args.skill_path)
        ai_analyzer.analyze_all()
        ai_results = ai_analyzer.get_results()
        all_results.extend(ai_results)

    duration = time.time() - start_time

    # Generate report
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_filename = f"skill-test-report-{args.skill_path.name}-{timestamp}.md"
    report_path = args.output_dir / report_filename

    generate_markdown_report(
        args.skill_path,
        args.skill_path.name,
        all_results,
        report_path,
        duration,
    )

    # Generate AI metadata if requested
    ai_metadata_path = None
    if args.ai_metadata:
        ai_metadata_path = args.ai_metadata
        generate_ai_metadata(
            args.skill_path,
            args.skill_path.name,
            all_results,
            report_path,
            ai_metadata_path,
        )

    # Calculate summary
    scorer = SkillScorer(all_results)
    score = scorer.calculate_score()
    grade = scorer.get_grade()
    critical = sum(1 for r in all_results if r.status == "critical")
    warnings = sum(1 for r in all_results if r.status == "warning")
    suggestions = sum(1 for r in all_results if r.status == "suggestion")

    if critical > 0:
        overall = "fail"
    elif warnings > 0:
        overall = "warn"
    else:
        overall = "pass"

    # Print terminal summary
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Test Completed: {args.skill_path.name}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")

    status_emoji = {"pass": "✅", "warn": "⚠️", "fail": "❌"}

    print(f"\n{status_emoji.get(overall, '?')} Status: {overall.upper()}")
    print(f"📊 Score: {score}/100 ({grade})")
    print(f"📋 Issues: {critical} Critical, {warnings} Warnings, {suggestions} Suggestions")
    print(f"📁 Report: [{report_filename}](file:///{report_path.as_posix()})")

    if critical > 0 or warnings > 0:
        print(f"\n{Colors.BOLD}Top Issues:{Colors.ENDC}")
        for r in all_results[:5]:
            if r.status in ("critical", "warning"):
                icon = status_emoji.get(r.status, "•")
                print(f"  {icon} {r.message}")

    print()

    # Output JSON for machine parsing
    json_output = {
        "status": overall,
        "score": score,
        "grade": grade,
        "report_path": str(report_path),
        "summary": {
            "critical": critical,
            "warnings": warnings,
            "suggestions": suggestions,
        },
        "top_issues": [r.message for r in all_results if r.status in ("critical", "warning")][:5],
    }

    print(f"SKILL_TEST_JSON::{json.dumps(json_output)}")

    # Output AI metadata marker if generated
    if ai_metadata_path:
        print(f"SKILL_TEST_AI_METADATA::{ai_metadata_path.as_posix()}")

    sys.exit(0 if overall != "fail" else 1)


if __name__ == "__main__":
    main()
