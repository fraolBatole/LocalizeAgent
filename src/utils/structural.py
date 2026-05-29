"""Fan-in/out, call relationships (ACR), variable usage (AVU), class coupling (ACC)."""

from __future__ import annotations

from pathlib import Path

from models import (
    CallRelationship,
    ClassCoupling,
    ClassVariableUsage,
    FanMetrics,
    MethodVariableUsage,
    StructuralAnalysis,
)

try:
    import tree_sitter_java as tsjava
    from tree_sitter import Language, Parser
except ImportError:  # pragma: no cover
    tsjava = None
    Language = None
    Parser = None

_TYPE_NODES = ("class_declaration", "interface_declaration", "enum_declaration")
_METHOD_NODES = ("method_declaration", "constructor_declaration")


def _java_language():
    if Language is None or tsjava is None:
        raise ImportError(
            "tree-sitter and tree-sitter-java are required. "
            "Install with: pip install tree-sitter tree-sitter-java"
        )
    return Language(tsjava.language())


def run_structural_analysis(
    source_code: str, *, file_path: str = "<inline>"
) -> StructuralAnalysis:
    """Run fan-in/out, ACR, AVU, and ACC on Java source."""
    parser = Parser(_java_language())
    tree = parser.parse(bytes(source_code, "utf-8"))
    root = tree.root_node

    method_calls: dict[str, set[str]] = {}
    call_edges: list[CallRelationship] = []
    fan_metrics: list[FanMetrics] = []
    variable_usage: list[ClassVariableUsage] = []
    class_coupling: list[ClassCoupling] = []

    for type_node in root.children:
        if type_node.type not in _TYPE_NODES:
            continue
        class_name = _type_name(type_node, source_code)
        body = type_node.child_by_field_name("body")
        if not body:
            continue

        field_count = sum(1 for c in body.children if c.type == "field_declaration")
        method_locals: list[MethodVariableUsage] = []

        for child in body.children:
            if child.type not in _METHOD_NODES:
                continue
            method_name = _method_name(child, source_code)
            key = f"{class_name}.{method_name}"
            callees = _extract_method_calls(child, source_code)
            method_calls[key] = callees
            for callee in sorted(callees):
                call_edges.append(
                    CallRelationship(
                        caller=key,
                        callee=callee,
                        file_path=file_path,
                    )
                )
            method_locals.append(
                MethodVariableUsage(
                    method_name=method_name,
                    local_variable_count=_count_local_variables(child),
                )
            )

        variable_usage.append(
            ClassVariableUsage(
                class_name=class_name,
                field_count=field_count,
                methods=method_locals,
            )
        )
        refs = _collect_type_refs(type_node, source_code, class_name)
        class_coupling.append(
            ClassCoupling(
                class_name=class_name,
                referenced_types=refs,
                coupling_degree=len(refs),
                file_path=file_path,
            )
        )

    fan_by_key = _compute_fan_metrics(method_calls)
    for key, metrics in sorted(fan_by_key.items()):
        class_name, method_name = key.split(".", 1)
        fan_metrics.append(
            FanMetrics(
                method_key=key,
                class_name=class_name,
                method_name=method_name,
                fan_in=metrics["fan_in"],
                fan_out=metrics["fan_out"],
                file_path=file_path,
            )
        )

    return StructuralAnalysis(
        file_path=file_path,
        fan_metrics=fan_metrics,
        call_relationships=call_edges,
        variable_usage=variable_usage,
        class_coupling=class_coupling,
    )


def run_structural_analysis_file(path: Path) -> StructuralAnalysis:
    source = path.read_text(encoding="utf-8")
    return run_structural_analysis(source, file_path=str(path.resolve()))


def merge_fan_metrics_into_code_facts(code_facts, structural: StructuralAnalysis):
    """Attach fan-in/out from structural analysis onto MethodFact entries."""
    if not code_facts or not structural.fan_metrics:
        return code_facts

    fan_by_key = {m.method_key: m for m in structural.fan_metrics}
    updated_classes = []
    for cls in code_facts.classes:
        updated_methods = []
        for method in cls.methods:
            key = f"{cls.name}.{method.name}"
            fan = fan_by_key.get(key)
            if fan:
                updated_methods.append(
                    method.model_copy(
                        update={"fan_in": fan.fan_in, "fan_out": fan.fan_out}
                    )
                )
            else:
                updated_methods.append(method)
        updated_classes.append(cls.model_copy(update={"methods": updated_methods}))
    return code_facts.model_copy(update={"classes": updated_classes})


def _compute_fan_metrics(method_calls: dict[str, set[str]]) -> dict[str, dict[str, int]]:
    fan: dict[str, dict[str, int]] = {
        key: {"fan_in": 0, "fan_out": len(callees)}
        for key, callees in method_calls.items()
    }
    for caller, callees in method_calls.items():
        for callee in callees:
            simple = callee.split(".")[-1]
            targets = [k for k in method_calls if k.endswith("." + simple)]
            if len(targets) == 1:
                fan[targets[0]]["fan_in"] += 1
    return fan


def _extract_method_calls(method_node, source: str) -> set[str]:
    calls: set[str] = set()
    for node in _walk(method_node):
        if node.type != "method_invocation":
            continue
        name_node = node.child_by_field_name("name")
        if not name_node:
            continue
        method_name = _node_text(name_node, source)
        obj_node = node.child_by_field_name("object")
        if obj_node:
            obj_text = _node_text(obj_node, source)
            calls.add(f"{obj_text}.{method_name}")
        else:
            calls.add(method_name)
    return calls


def _count_local_variables(method_node) -> int:
    count = 0
    for node in _walk(method_node):
        if node.type == "local_variable_declaration":
            for child in node.children:
                if child.type == "variable_declarator":
                    count += 1
    return count


def _collect_type_refs(node, source: str, self_name: str) -> list[str]:
    refs: set[str] = set()
    for child in _walk(node):
        if child.type not in ("type_identifier", "scoped_type_identifier"):
            continue
        text = _node_text(child, source)
        if text and text.split(".")[-1] != self_name:
            refs.add(text.split(".")[-1])
    return sorted(refs)


def _type_name(node, source: str) -> str:
    name_node = node.child_by_field_name("name")
    return _node_text(name_node, source) if name_node else "Unknown"


def _method_name(node, source: str) -> str:
    name_node = node.child_by_field_name("name")
    return _node_text(name_node, source) if name_node else "unknown"


def _node_text(node, source: str) -> str:
    return source[node.start_byte : node.end_byte]


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)
