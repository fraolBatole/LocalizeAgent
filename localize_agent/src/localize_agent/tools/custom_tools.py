import javalang  
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import re

class CodeAnalysisInput(BaseModel):
    """Input for the tools that analyze Java source code."""
    source_code: str = Field(..., description="The Java source code to analyze.")

class CountMethods(BaseTool):
    name: str = "CountMethods"
    description: str = "Counts the number of methods in a given Java source code."
    args_schema: Type[BaseModel] = CodeAnalysisInput

    def _run(self, source_code: str) -> str:
        try:
            print("Debug: Starting to clean up the Java source code.")
            # Remove comments and import statements
            source_code = re.sub(r"//.*?$|/\*.*?\*/|^\s*import\s+.*?;", "", source_code, flags=re.DOTALL | re.MULTILINE)
            print("Debug: Cleaned up the Java source code.")

            print("Debug: Starting to parse the Java source code.")
            # Parse the Java source
            tree = javalang.parse.parse(source_code)
            print("Debug: Successfully parsed the Java source code.")

            # Traverse top-level type declarations and count methods
            method_count = 0
            for type_decl in tree.types:
                print(f"Debug: Processing type declaration: {type_decl.name if hasattr(type_decl, 'name') else 'Unknown'}")
                
                # You can handle ClassDeclaration, InterfaceDeclaration, EnumDeclaration, etc.
                if hasattr(type_decl, 'methods'):
                    method_count += len(type_decl.methods)
                    print(f"Debug: Found {len(type_decl.methods)} methods in {type_decl.name if hasattr(type_decl, 'name') else 'Unknown'}.")

            print(f"Debug: Total methods counted: {method_count}")
            return f"The source code contains {method_count} methods."
        except Exception as e:
            print(f"Debug: Error encountered - {e}")
            return f"Error processing Java source code: {e}"

class VariableUsage(BaseTool):
    name: str = "VariableUsage"
    description: str = "Analyzes variable usage (fields vs. local variables) in the given Java source code."
    args_schema: Type[BaseModel] = CodeAnalysisInput

    def _run(self, source_code: str) -> str:
        try:
            # Remove comments and import statements
            source_code = re.sub(r"//.*?$|/\*.*?\*/|^\s*import\s+.*?;", "", source_code, flags=re.DOTALL | re.MULTILINE)

            # Parse the Java source code into an AST
            tree = javalang.parse.parse(source_code)

            # Prepare a data structure to hold the counts
            variable_usage = {
                "global": 0,
                "methods": {}
            }

            # Go through top-level type declarations
            for type_decl in tree.types:
                # Accumulate fields declared at the class/enum/interface level
                if hasattr(type_decl, 'fields'):
                    for field_decl in type_decl.fields:
                        variable_usage["global"] += len(field_decl.declarators)

                # Look at each method and filter for LocalVariableDeclarations
                if hasattr(type_decl, 'methods'):
                    for method in type_decl.methods:
                        method_name = method.name
                        method_var_count = 0

                        # javalang allows us to filter nodes in the AST of this method
                        for _, node in method.filter(javalang.tree.LocalVariableDeclaration):
                            method_var_count += len(node.declarators)

                        variable_usage["methods"][method_name] = method_var_count

            return f"Variable Usage: {variable_usage}"
        except Exception as e:
            return f"Error processing Java source code: {e}"

class FanInFanOutAnalysis(BaseTool):
    name: str = "FanInFanOutAnalysis"
    description: str = (
        "Analyzes methods in the Java source code and computes a naive fan-in/fan-out."
        " Fan-out = number of distinct methods that a method calls; "
        " Fan-in = number of times a method is called by other methods in the same file."
    )
    args_schema: Type[BaseModel] = CodeAnalysisInput

    def _run(self, source_code: str) -> str:
        try:
            # Strip out comments and import statements for cleaner parsing
            source_code = re.sub(
                r"//.*?$|/\*.*?\*/|^\s*import\s+.*?;",
                "",
                source_code,
                flags=re.DOTALL | re.MULTILINE
            )

            # Parse the Java source code
            tree = javalang.parse.parse(source_code)

            # A dictionary mapping "ClassName.methodName" -> set of called method names
            method_calls = {}

            # Gather all top-level types (classes, interfaces, enums)
            for type_decl in tree.types:
                # If it's something that can contain methods
                if hasattr(type_decl, 'methods'):
                    for method in type_decl.methods:
                        # Build a unique key, e.g. "MyClass.myMethod"
                        class_and_method = f"{type_decl.name}.{method.name}"
                        method_calls[class_and_method] = set()

                        # For each method invocation inside, record the called method name
                        for _, node in method.filter(javalang.tree.MethodInvocation):
                            # 'node.member' is the method name being called
                            method_calls[class_and_method].add(node.member)

            # Prepare a structure to hold the final fan-in/fan-out per method
            fan_metrics = {}
            for method_key in method_calls.keys():
                fan_metrics[method_key] = {
                    "fanIn": 0,
                    "fanOut": 0
                }

            # 1) Compute the fan-out = size of the distinct calls
            for method_key, calls in method_calls.items():
                fan_metrics[method_key]["fanOut"] = len(calls)

            # 2) Compute the fan-in by inverting the calls:
            #    for each method that calls X, increment X's fan-in
            for caller, called_methods in method_calls.items():
                for called_m in called_methods:
                    # Find all possible methods that end with ".<called_m>"
                    # (Naive approach: if there's exactly 1 match, that’s our target.)
                    possible_targets = [
                        k for k in method_calls.keys() 
                        if k.endswith("." + called_m)
                    ]
                    if len(possible_targets) == 1:
                        callee_key = possible_targets[0]
                        fan_metrics[callee_key]["fanIn"] += 1

            # Format a human-readable summary
            lines = ["Fan-In / Fan-Out Analysis:"]
            for m_key, data in fan_metrics.items():
                lines.append(
                    f"Method {m_key}: fanIn={data['fanIn']}, fanOut={data['fanOut']}"
                )

            return "\n".join(lines)

        except Exception as e:
            return f"Error processing Java source code: {e}"
        

class ClassCouplingAnalysis(BaseTool):
    name: str = "ClassCouplingAnalysis"
    description: str = (
        "By assessing class dependencies, this analysis provides insights into system"
        " modularity and potential areas for improving design quality. This tool identifies"
        " each class in the source file and detects the other classes it references."
    )
    args_schema: Type[BaseModel] = CodeAnalysisInput

    def _run(self, source_code: str) -> str:
        try:
            # Remove comments and imports for simpler parsing
            source_code = re.sub(
                r"//.*?$|/\*.*?\*/|^\s*import\s+.*?;",
                "",
                source_code,
                flags=re.DOTALL | re.MULTILINE
            )

            tree = javalang.parse.parse(source_code)

            # Dictionary of the form: { "ClassName": set([ReferencedClassName1, ...]) }
            class_references = {}

            # Process each top-level type (class, interface, enum)
            for type_decl in tree.types:
                # We only care about declarations that have a .name attribute (e.g., classes, interfaces)
                if not hasattr(type_decl, 'name'):
                    continue

                current_class_name = type_decl.name
                class_references[current_class_name] = set()

                # Traverse the AST nodes within this type declaration and look for type references
                for _, node in type_decl.filter(javalang.tree.Type):
                    if node.name and (node.name != current_class_name):
                        class_references[current_class_name].add(node.name)

            # Format a readable summary
            lines = ["Class Coupling Analysis:"]
            for class_name, references in class_references.items():
                coupling_count = len(references)
                lines.append(
                    f"  - Class {class_name} references: {sorted(list(references)) or 'None'}"
                    f" -> Coupling = {coupling_count}"
                )

            return "\n".join(lines)

        except Exception as e:
            return f"Error processing Java source code: {e}"