#!/usr/bin/env python
import sys
import warnings
import os
from localize_agent.crew import LocalizeAgent

os.environ["OTEL_SDK_DISABLED"] = "true"

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def get_file_path(default_path=None):
    """
    Prompt user for file path or use the provided default.
    """
    if default_path and os.path.exists(default_path):
        use_default = input(f"Use default file path ({default_path})? (y/n): ").lower() == 'y'
        if use_default:
            return default_path
    
    while True:
        file_path = input("Enter the path to your source code file: ")
        if os.path.exists(file_path):
            return file_path
        else:
            print(f"File not found: {file_path}")

def run():
    """
    Run the crew.
    """
    default_path = '/Users/fraolbatole/Documents/GitHub/LocalizeAgent/localize_agent/src/localize_agent/datasets/test_input.java'
    file_path = get_file_path(default_path)
    
    with open(file_path, 'r') as f:
        source_code = f.read()
    
    inputs = {
        "code": source_code
    }

    try:
        LocalizeAgent().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    file_path = get_file_path()
    
    with open(file_path, 'r') as f:
        source_code = f.read()
    
    inputs = {
        "code": source_code
    }
    try:
        LocalizeAgent().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        LocalizeAgent().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    file_path = get_file_path()
    
    with open(file_path, 'r') as f:
        source_code = f.read()
    
    inputs = {
        "code": source_code
    }
    try:
        LocalizeAgent().crew().test(n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")
