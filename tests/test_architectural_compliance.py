import io
import re
import subprocess
import tokenize
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

# =====================================================================
# HARD ARCHITECTURAL COMPLIANCE SCHEMAS
# =====================================================================


class ComplianceFinding(BaseModel):
    """Encapsulates a verified deviation from core repository architectural rules."""

    rule_id: str = Field(..., description="The unique architectural rule identifier")
    target_file: str = Field(..., description="The relative path of the scanned asset")
    status: str = Field(..., description="The compliance validation state")
    description: str = Field(..., description="Technical details of the validation failure")
    remediation: str = Field(..., description="Explicit correction step to preserve core design")


class ComplianceReport(BaseModel):
    """Validates the consolidated output of the architectural guard execution."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    files_evaluated: int = Field(..., ge=0)
    violations_found: int = Field(..., ge=0)
    findings: List[ComplianceFinding] = Field(default_factory=list)


# =====================================================================
# ARCHITECTURAL GUARD ENGINE
# =====================================================================


class RepositoryArchitecturalGuard:
    """Validates codebase elements to prevent drift from strict GitOps constraints."""

    def __init__(self, repository_root: str) -> None:
        self.root_path = Path(repository_root)
        self._tracked_python_files_cache: List[Path] | None = None

    def _should_skip(self, file_path: Path) -> bool:
        """Excludes the compliance guard itself to prevent self-scan false positives."""
        return file_path.name == "test_architectural_compliance.py"

    def _tracked_python_files(self) -> List[Path]:
        """Python files tracked by git. Untracked scratch files and build
        artifacts must not pollute (or silently pass) the scan."""
        if self._tracked_python_files_cache is None:
            out = subprocess.run(
                ["git", "-C", str(self.root_path), "ls-files", "--", "*.py"],
                capture_output=True,
                text=True,
                check=True,
            )
            self._tracked_python_files_cache = [self.root_path / rel for rel in out.stdout.splitlines() if rel]
        return self._tracked_python_files_cache

    def _clean_content(self, content: str) -> str:
        """Strip Python comments while preserving '#' inside string literals.

        Implemented with tokenize: only COMMENT tokens are dropped, so '#' in
        strings (URLs, color codes, regexes) survives. Docstrings are NOT
        removed (the old implementation split lines on '#', which mangled
        string contents and never touched docstrings either).
        """
        try:
            return "".join(
                tok.string
                for tok in tokenize.generate_tokens(io.StringIO(content).readline)
                if tok.type != tokenize.COMMENT
            )
        except (tokenize.TokenError, IndentationError, SyntaxError):
            # Unparseable input: return it unscanned rather than mangled.
            return content

    def _strip_yaml_comments(self, content: str) -> str:
        """Strip YAML comments: '#' at line start or preceded by whitespace.
        Preserves '#' inside quoted scalars such as "a#b"."""
        return re.sub(r"(?m)(^|\s)#.*$", r"\1", content)

    def verify_timezone_standard(self) -> List[ComplianceFinding]:
        """Flags deprecated naive datetime calls to protect timezone-aware updates."""
        findings = []
        for py_file in self._tracked_python_files():
            if self._should_skip(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                clean_content = self._clean_content(content)
                if "utcnow()" in clean_content:
                    findings.append(
                        ComplianceFinding(
                            rule_id="RULE-TIME-001",
                            target_file=str(py_file.relative_to(self.root_path)),
                            status="NON-COMPLIANT",
                            description="File utilizes deprecated naive datetime.utcnow() function.",
                            remediation="Replace with modern timezone-aware execution utilizing datetime.now(timezone.utc).",
                        )
                    )
            except IOError:
                continue
        return findings

    def verify_flat_file_constraint(self) -> List[ComplianceFinding]:
        """Keeps the Python pipeline off every database.

        Repository state persists exclusively in version-controlled flat JSON.
        Supabase is reachable only from the Node service in `backend/`, which
        this guard does not scan. The scan catches the Python side reaching for
        a database directly, `supabase` included, so the boundary stays one-way.
        """
        findings = []
        for py_file in self._tracked_python_files():
            if self._should_skip(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                clean_content = self._clean_content(content)
                # Detect forbidden database engines, ORM drivers, and the
                # Supabase client inside the Python pipeline.
                if re.search(r"sqlite3|sqlalchemy|psycopg2|mysql|supabase", clean_content, re.IGNORECASE):
                    findings.append(
                        ComplianceFinding(
                            rule_id="RULE-STOR-001",
                            target_file=str(py_file.relative_to(self.root_path)),
                            status="NON-COMPLIANT",
                            description="File introduces a database client or external storage driver into the Python pipeline.",
                            remediation="Remove the database library from Python. Persist state in version-controlled flat JSON, or route database access through the Node service in backend/.",
                        )
                    )
            except IOError:
                continue
        return findings

    def verify_non_evasion_posture(self) -> List[ComplianceFinding]:
        """Flags evasion tactics to protect the document-the-block legal posture."""
        findings = []
        for py_file in self._tracked_python_files():
            if self._should_skip(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                clean_content = self._clean_content(content)
                # Detect proxy rotations or subdivision logic that attempts evasion
                if re.search(r"rotate_proxy|proxy_pool|recursive_subdivision", clean_content, re.IGNORECASE):
                    findings.append(
                        ComplianceFinding(
                            rule_id="RULE-EVAS-001",
                            target_file=str(py_file.relative_to(self.root_path)),
                            status="NON-COMPLIANT",
                            description="File introduces active proxy rotation or network evasion tactics.",
                            remediation="Halt execution on blocks, log the firewall block as public records legal evidence.",
                        )
                    )
            except IOError:
                continue
        return findings

    def verify_gitops_pipeline(self) -> List[ComplianceFinding]:
        """Validates that automated tasks commit data directly to the active code branch."""
        findings = []
        workflow_dir = self.root_path / ".github" / "workflows"
        if workflow_dir.exists():
            yaml_files = sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml"))
            for yaml_file in yaml_files:
                try:
                    content = yaml_file.read_text(encoding="utf-8")
                    clean_content = self._strip_yaml_comments(content)
                    # A gh-pages *publish target* (branch/ref config or the
                    # gh-pages deploy action) alongside a data-commit step
                    # means data is published off-branch. A bare mention in
                    # prose (e.g. "no gh-pages branch needed") is not one.
                    publishes_off_branch = re.search(
                        r"(?im)^\s*(?:branch|branches|ref|target_branch|publish_branch)\s*:[^\n]*gh-pages"
                        r"|\bpeaceiris/actions-gh-pages\b",
                        clean_content,
                    )
                    if "git commit" in clean_content and publishes_off_branch:
                        findings.append(
                            ComplianceFinding(
                                rule_id="RULE-PIPE-001",
                                target_file=str(yaml_file.relative_to(self.root_path)),
                                status="NON-COMPLIANT",
                                description="Workflow isolates data updates onto a separate deployment branch.",
                                remediation="Commit updated data files directly back to the active repository to trigger Pages compilation.",
                            )
                        )
                except IOError:
                    continue
        return findings

    def execute_guard_suite(self) -> ComplianceReport:
        """Runs all compliance checks sequentially against the repository path."""
        all_findings = []
        all_findings.extend(self.verify_timezone_standard())
        all_findings.extend(self.verify_flat_file_constraint())
        all_findings.extend(self.verify_non_evasion_posture())
        all_findings.extend(self.verify_gitops_pipeline())

        # Count only the tracked Python files the verifiers actually scanned.
        total_files = len(self._tracked_python_files())

        return ComplianceReport(files_evaluated=total_files, violations_found=len(all_findings), findings=all_findings)


def test_repository_architectural_compliance():
    """Asserts that the codebase satisfies all strict repository compliance rules."""
    repo_root = Path(__file__).resolve().parent.parent
    guard = RepositoryArchitecturalGuard(str(repo_root))
    report = guard.execute_guard_suite()

    if report.violations_found > 0:
        details = "\n".join(
            f"- {f.rule_id} in {f.target_file}: {f.description} (Remediation: {f.remediation})" for f in report.findings
        )
        raise AssertionError(f"Codebase violated repository architectural rules:\n{details}")


def _rule_stor_001_findings(tmp_path, filename: str, content: str) -> List[ComplianceFinding]:
    """Run RULE-STOR-001 against a throwaway repository holding one file.

    The guard enumerates files with `git ls-files`, so the fixture has to be a
    real repository rather than a bare directory.
    """
    (tmp_path / filename).write_text(content, encoding="utf-8")
    subprocess.run(["git", "-c", "init.defaultBranch=main", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "--", filename], cwd=tmp_path, check=True)
    return RepositoryArchitecturalGuard(str(tmp_path)).verify_flat_file_constraint()


def test_rule_stor_001_flags_supabase_in_python(tmp_path):
    """RULE-STOR-001 must catch the Supabase client, not only named SQL drivers.

    Regression guard. `supabase` was absent from the pattern until 2026-09-22,
    so a Python module could import the Supabase client, pass this guard, and
    still violate the rule's intent that the Python pipeline never reaches a
    database. Supabase access is confined to the Node service in `backend/`.
    """
    findings = _rule_stor_001_findings(tmp_path, "offender.py", "from supabase import create_client\n")

    assert [f.rule_id for f in findings] == ["RULE-STOR-001"]
    assert findings[0].target_file == "offender.py"


def test_rule_stor_001_allows_plain_http_pipeline_code(tmp_path):
    """RULE-STOR-001 must not fire on ordinary pipeline code.

    A pattern widened without bound would be as useless as one that misses the
    real case, so the guard has to keep letting the httpx-based scrapers past.
    """
    findings = _rule_stor_001_findings(tmp_path, "scraper_module.py", "import httpx\n")

    assert findings == []
