import json
import logging
import traceback

from browser_use import Agent

logger = logging.getLogger(__name__)

class MedicineInfoAgent:
    def __init__(self, llm, medicine_name: str):
        self.llm = llm
        self.medicine_name = medicine_name

    def _build_task(self) -> str:
        # Task to navigate to drugs.com and extract required information
        task = f"""
        Navigate to https://drugs.com/{self.medicine_name}.html.
        wait 2 seconds
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
            data = None
            # Check if the result contains the expected JSON structure
            if hasattr(result, "final_result") and callable(getattr(result, "final_result")):
                final_result = result.final_result()
                if final_result:
                    # Extract JSON from the final result text
                    # First try to find a JSON string within the text
                    import re
                    json_match = re.search(r'\{.*\}', final_result, re.DOTALL)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(0))
                        except json.JSONDecodeError:
                            logger.warning("Found JSON-like text but couldn't parse it")
            
            # Fallback: Try to extract JSON from the agent's steps
            if data is None and hasattr(result, "__iter__"):
                for step in result:
                    if hasattr(step, "action") and isinstance(step.action, dict) and "done" in step.action:
                        done_data = step.action.get("done", {})
                        if isinstance(done_data, dict) and done_data.get("success") and "text" in done_data:
                            try:
                                # Look for JSON within the text
                                import re
                                json_match = re.search(r'\{.*\}', done_data["text"], re.DOTALL)
                                if json_match:
                                    data = json.loads(json_match.group(0))
                                    break
                                
                                # If no JSON pattern found, try parsing the entire text
                                data = json.loads(done_data["text"])
                                break
                            except json.JSONDecodeError:
                                # Try to extract from Step 3 extraction content
                                continue
            
            # Process data to conform to the Medicine model requirements
            if data:
                # Convert list fields to strings
                if "brand_names" in data and isinstance(data["brand_names"], list):
                    data["brand"] = ", ".join(data["brand_names"])
                    del data["brand_names"]
                
                if "dosage_forms" in data and isinstance(data["dosage_forms"], list):
                    data["dosage"] = "; ".join(data["dosage_forms"])
                    del data["dosage_forms"]
                    
                if "drug_class" in data:
                    data["category"] = data["drug_class"]
                    del data["drug_class"]
                
                if "generic_name" in data:
                    # Make sure we have the name field populated
                    if "name" not in data:
                        data["name"] = data["generic_name"]
                    del data["generic_name"]
                
                return data

            return None
        except Exception as e:
            logger.error(f"Error processing result: {str(e)}")
            logger.error(traceback.format_exc())
            return None
