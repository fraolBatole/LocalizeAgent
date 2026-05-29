from localize_agent.models import PMD_DESIGN_RULES, PmdFinding, RefactoringTarget


def test_pmd_design_rules_count():
    assert len(PMD_DESIGN_RULES) == 8
    assert "GodClass" in PMD_DESIGN_RULES


def test_pmd_finding_model():
    f = PmdFinding(
        rule="GodClass",
        message="Possible God class",
        file_path="Foo.java",
        line=10,
    )
    assert f.line == 10


def test_refactoring_target():
    t = RefactoringTarget(
        class_name="Foo",
        function_name="bar",
        refactoring_type="move method",
        rationale="High coupling",
        rank=1,
    )
    assert t.rank == 1
