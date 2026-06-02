import re
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

    def _should_skip(self, file_path: Path) -> bool:
        """Excludes the compliance guard itself to prevent self-scan false positives."""
        return file_path.name == "test_architectural_compliance.py"

    def _clean_content(self, content: str) -> str:
        """Strips comments to prevent false positives in comments or docstrings."""
        lines = []
        for line in content.splitlines():
            if "#" in line:
                line = line.split("#", 1)[0]
            lines.append(line)
        return "\n".join(lines)

    def verify_timezone_standard(self) -> List[ComplianceFinding]:
        """Flags deprecated naive datetime calls to protect timezone-aware updates."""
        findings = []
        for py_file in self.root_path.glob("**/*.py"):
            if self._should_skip(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                clean_content = self._clean_content(content)
                if "utcnow()" in clean_content:
                    findings.append(ComplianceFinding(
                        rule_id="RULE-TIME-001",
                        target_file=str(py_file.relative_to(self.root_path)),
                        status="NON-COMPLIANT",
                        description="File utilizes deprecated naive datetime.utcnow() function.",
                        remediation="Replace with modern timezone-aware execution utilizing datetime.now(timezone.utc)."
                    ))
            except IOError:
                continue
        return findings

    def verify_flat_file_constraint(self) -> List[ComplianceFinding]:
        """Prevents the introduction of database engines to protect zero-cost hosting."""
        findings = []
        for py_file in self.root_path.glob("**/*.py"):
            if self._should_skip(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                clean_content = self._clean_content(content)
                # Detect forbidden database engines or ORM drivers
                if re.search(r"sqlite3|sqlalchemy|psycopg2|mysql", clean_content, re.IGNORECASE):
                    findings.append(ComplianceFinding(
                        rule_id="RULE-STOR-001",
                        target_file=str(py_file.relative_to(self.root_path)),
                        status="NON-COMPLIANT",
                        description="File introduces SQL database components or external storage drivers.",
                        remediation="Remove database libraries, persist state exclusively within version-controlled flat JSON files."
                    ))
            except IOError:
                continue
        return findings

    def verify_non_evasion_posture(self) -> List[ComplianceFinding]:
        """Flags evasion tactics to protect the document-the-block legal posture."""
        findings = []
        for py_file in self.root_path.glob("**/*.py"):
            if self._should_skip(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                clean_content = self._clean_content(content)
                # Detect proxy rotations or subdivision logic that attempts evasion
                if re.search(r"rotate_proxy|proxy_pool|recursive_subdivision", clean_content, re.IGNORECASE):
                    findings.append(ComplianceFinding(
                        rule_id="RULE-EVAS-001",
                        target_file=str(py_file.relative_to(self.root_path)),
                        status="NON-COMPLIANT",
                        description="File introduces active proxy rotation or network evasion tactics.",
                        remediation="Halt execution on blocks, log the firewall block as public records legal evidence."
                    ))
            except IOError:
                continue
        return findings

    def verify_gitops_pipeline(self) -> List[ComplianceFinding]:
        """Validates that automated tasks commit data directly to the active code branch."""
        findings = []
        workflow_dir = self.root_path / ".github" / "workflows"
        if workflow_dir.exists():
            for yaml_file in workflow_dir.glob("*.yml"):
                try:
                    content = yaml_file.read_text(encoding="utf-8")
                    clean_content = self._clean_content(content)
                    # Ensure workflows execute direct repository data updates
                    if "git commit" in clean_content and "gh-pages" in clean_content:
                        findings.append(ComplianceFinding(
                            rule_id="RULE-PIPE-001",
                            target_file=str(yaml_file.relative_to(self.root_path)),
                            status="NON-COMPLIANT",
                            description="Workflow isolates data updates onto a separate deployment branch.",
                            remediation="Commit updated data files directly back to the active repository to trigger Pages compilation."
                        ))
                except IOError:
                    continue
        return findings

    def execute_guard_suite(self) -> ComplianceReport:
        """Runs all compliance checks concurrently against the repository path."""
        all_findings = []
        all_findings.extend(self.verify_timezone_standard())
        all_findings.extend(self.verify_flat_file_constraint())
        all_findings.extend(self.verify_non_evasion_posture())
        all_findings.extend(self.verify_gitops_pipeline())

        total_files = len(list(self.root_path.glob("**/*")))
        
        return ComplianceReport(
            files_evaluated=total_files,
            violations_found=len(all_findings),
            findings=all_findings
        )


def test_repository_architectural_compliance():
    """Asserts that the codebase satisfies all strict repository compliance rules."""
    repo_root = Path(__file__).resolve().parent.parent
    guard = RepositoryArchitecturalGuard(str(repo_root))
    report = guard.execute_guard_suite()
    
    if report.violations_found > 0:
        details = "\n".join(
            f"- {f.rule_id} in {f.target_file}: {f.description} (Remediation: {f.remediation})"
            for f in report.findings
        )
        assert False, f"Codebase violated repository architectural rules:\n{details}"

    assert report.violations_found == 0
