import ast
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


class CountMethodsInput(BaseModel):
    """Input for the CountMethods tool."""
    source_code: str = Field(..., description="The source code to analyze.")

class CountMethods(BaseTool):
    name: str = "Count Methods in Source Code"
    description: str = "Counts the number of methods in a given source code."
    args_schema: Type[BaseModel] = CountMethodsInput

    def _run(self, source_code: str) -> str:
        try:
            tree = ast.parse(source_code)
            method_count = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
            return f"The source code contains {method_count} methods."
        except Exception as e:
            return f"Error processing source code: {e}"
