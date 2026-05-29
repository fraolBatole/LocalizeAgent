"""Tree-sitter based Java code fact extraction."""

from __future__ import annotations

from pathlib import Path

from models import ClassFact, CodeFact, MethodFact

try:
    import tree_sitter_java as tsjava
    from tree_sitter import Language, Parser
except ImportError:  # pragma: no cover
    tsjava = None
    Language = None
    Parser = None


def _java_language():
    if Language is None or tsjava is None:
        raise ImportError(
            "tree-sitter and tree-sitter-java are required. "
            "Install with: pip install tree-sitter tree-sitter-java"
        )
    return Language(tsjava.language())


class JavaTreeSitterAnalyzer:
    """Extract structured code facts from Java source via Tree-sitter."""

    def __init__(self) -> None:
        self._parser = Parser(_java_language())

    def analyze_source(
        self, source_code: str, *, file_path: str = "<inline>"
    ) -> CodeFact:
        tree = self._parser.parse(bytes(source_code, "utf-8"))
        root = tree.root_node
        classes: list[ClassFact] = []

        for node in root.children:
            if node.type in ("class_declaration", "interface_declaration", "enum_declaration"):
                classes.append(self._extract_type(node, source_code))

        total_methods = sum(c.method_count for c in classes)

        return CodeFact(
            language="java",
            file_path=file_path,
            classes=classes,
            total_methods=total_methods,
        )

    def analyze_file(self, path: Path) -> CodeFact:
        source = path.read_text(encoding="utf-8")
        return self.analyze_source(source, file_path=str(path.resolve()))

    def _extract_type(self, node, source: str) -> ClassFact:
        name_node = node.child_by_field_name("name")
        name = _node_text(name_node, source) if name_node else "Unknown"
        methods: list[MethodFact] = []
        field_count = 0
        public_count = 0

        body = node.child_by_field_name("body")
        if body:
            for child in body.children:
                if child.type == "field_declaration":
                    field_count += 1
                    if _has_modifier(child, "public", source):
                        public_count += _count_declarators(child)
                elif child.type in ("method_declaration", "constructor_declaration"):
                    methods.append(self._extract_method(child, source, name))
                    if _has_modifier(child, "public", source):
                        public_count += 1

        return ClassFact(
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            method_count=len(methods),
            field_count=field_count,
            public_member_count=public_count,
            referenced_types=_collect_type_refs(node, source, name),
            methods=methods,
        )

    def _extract_method(self, node, source: str, class_name: str) -> MethodFact:
        name_node = node.child_by_field_name("name")
        name = _node_text(name_node, source) if name_node else "unknown"
        params = node.child_by_field_name("parameters")
        param_count = 0
        signature = name
        if params:
            param_text = _node_text(params, source)
            inner = param_text.strip("()").strip()
            param_count = 0 if not inner else inner.count(",") + 1
            signature = f"{name}{param_text}"

        return MethodFact(
            class_name=class_name,
            name=name,
            signature=signature,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameter_count=param_count,
            is_public=_has_modifier(node, "public", source),
        )


def _collect_type_refs(node, source: str, self_name: str) -> list[str]:
    refs: set[str] = set()
    for child in _walk(node):
        if child.type in ("type_identifier", "scoped_type_identifier"):
            text = _node_text(child, source)
            if text and text.split(".")[-1] != self_name:
                refs.add(text.split(".")[-1])
    return sorted(refs)


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def _node_text(node, source: str) -> str:
    return source[node.start_byte : node.end_byte]


def _has_modifier(node, modifier: str, source: str) -> bool:
    for child in node.children:
        if child.type == "modifiers":
            return modifier in _node_text(child, source)
    return False


def _count_declarators(field_node) -> int:
    count = 0
    for child in field_node.children:
        if child.type == "variable_declarator":
            count += 1
    return max(count, 1)

