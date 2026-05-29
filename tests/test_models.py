from models import PMD_DESIGN_RULES, PmdFinding, RefactoringTarget


def test_pmd_design_rules_count():
    assert len(PMD_DESIGN_RULES) >= 5


def test_pmd_finding_model():
    finding = PmdFinding(
        rule="GodClass",
        message="Too big",
        file_path="Foo.java",
        line=1,
    )
    assert finding.rule == "GodClass"


def test_refactoring_target():
    target = RefactoringTarget(
        class_name="Foo",
        function_name="bar",
        refactoring_type="move method",
        rationale="High coupling",
        rank=1,
    )
    assert target.rank == 1
