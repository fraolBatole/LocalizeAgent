from localize_agent.analyzers.correlator import correlate_evidence, format_evidence_text
from localize_agent.models import ClassFact, CodeFact, MethodFact, PmdFinding


def test_correlate_finding_to_class_by_line():
    code_facts = CodeFact(
        language="java",
        file_path="Foo.java",
        classes=[
            ClassFact(
                name="Foo",
                start_line=1,
                end_line=50,
                method_count=2,
                methods=[
                    MethodFact(
                        class_name="Foo",
                        name="bar",
                        start_line=10,
                        end_line=20,
                        parameter_count=3,
                    )
                ],
            )
        ],
        total_methods=2,
    )
    findings = [
        PmdFinding(
            rule="ExcessiveParameterList",
            message="Too many parameters",
            file_path="Foo.java",
            line=12,
            method_name="bar",
            class_name="Foo",
        )
    ]
    correlated = correlate_evidence(findings, code_facts)
    assert len(correlated) == 1
    assert correlated[0].class_fact is not None
    assert correlated[0].method_fact is not None
    assert correlated[0].method_fact.name == "bar"
    text = format_evidence_text(correlated, code_facts)
    assert "ExcessiveParameterList" in text
