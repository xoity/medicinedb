from browser_use import Agent
import json
import logging
import traceback

logger = logging.getLogger(__name__)


class MedicineInfoAgent:
    def __init__(self, llm, medicine_name: str):
        self.llm = llm
        self.medicine_name = medicine_name

    def _build_task(self) -> str:
        # Task to navigate to drugs.com and extract required information
        task = f"""
        Navigate to drugs.com and search for the medicine "{self.medicine_name}".
        Once on the search results page, click on the most relevant result for the medicine.
        Extract the following information from the page:
        - Generic name
        - Brand names
        - Dosage forms
        - Drug class
        Format the extracted information into a structured JSON object with the following keys:
        {{
            "generic_name": "",
            "brand_names": "",
            "dosage_forms": "",
            "drug_class": ""
        }}
        If any of the fields are not available, use "N/A" as the value.
        """
        return task

    async def run(self):
        task = self._build_task()
        agent = Agent(
            task=task,
            llm=self.llm,
            max_actions_per_step=5,
        )

        result = await agent.run(max_steps=50)
        return self._process_result(result)

    def _process_result(self, result):
        """Process the structured result from the agent"""
        try:
            # Check if the result contains the expected JSON structure
            if hasattr(result, "final_result") and callable(getattr(result, "final_result")):
                final_result = result.final_result()
                if final_result:
                    return json.loads(final_result)

            # Fallback: Try to extract JSON from the agent's steps
            if hasattr(result, "__iter__"):
                for step in result:
                    if hasattr(step, "action") and isinstance(step.action, dict) and "done" in step.action:
                        done_data = step.action.get("done", {})
                        if isinstance(done_data, dict) and done_data.get("success") and "text" in done_data:
                            try:
                                return json.loads(done_data["text"])
                            except json.JSONDecodeError:
                                continue

            return None
        except Exception as e:
            logger.error(f"Error processing result: {str(e)}")
            logger.error(traceback.format_exc())
            return None


class SqliteMcpAgent:
    def __init__(self, llm, prompt):
        self.llm = llm
        self.prompt = prompt

    async def run(self):
        task = f"""
        You are an expert in SQL and database analysis. Use the SQLite MCP to help with the following request:
        
        {self.prompt}
        
        Remember to:
        1. Use read_query for SELECT queries to retrieve data
        2. Use write_query for INSERT, UPDATE, or DELETE operations
        3. Use create_table if you need to create a new table
        4. Use list_tables to see what tables are available
        5. Use describe_table to understand the schema of a table
        6. Use append_insight to record important insights discovered
        
        Provide clear explanations before and after running queries, and summarize the findings in a helpful way.
        """
        
        agent = Agent(
            task=task,
            llm=self.llm,
            max_actions_per_step=5,
        )
        
        result = await agent.run(max_steps=50)
        return result
