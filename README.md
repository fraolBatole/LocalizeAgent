To execute LocalizeAgent:

1.  Install CrewAI: `pip install crewai`
2.  Navigate to the LocalizeAgent directory: `cd localize_agent`
3.  Create a `.env` file and add your model and API key:

    ```
    MODEL="your_model_name"
    MODEL_NAME_API_KEY="your_api_key"
    ```

    e.g.,

    ```
    MODEL=gemini/gemini-1.5-flash
    GEMINI_API_KEY="your_gemini_api_key"
    ```
4.  Run the agent: `crewai run`
