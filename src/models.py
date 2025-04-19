from pydantic import BaseModel, Field
from typing import List


class Medicine(BaseModel):
    name: str = Field(description="The name of the medicine")
    brand: str = Field(description="The brand or manufacturer of the medicine")
    price: float = Field(description="The price of the medicine")
    dosage: str = Field(description="The recommended dosage for adults")
    form: str = Field(description="Form of medicine (e.g., tablet, liquid, injection)")
    otc: bool = Field(description="Whether the medicine is available over-the-counter (True) or requires prescription (False)")
    description: str = Field(description="Brief description of the medicine's purpose")
    side_effects: str = Field(description="Common side effects of the medicine")
    category: str = Field(description="Category or type of medicine")
    date_added: str = Field(description="Date when the medicine was added to the database")


class MedicineDatabase(BaseModel):
    medicines: List[Medicine] = Field(description="List of medicines in the database")
    

class MedicineInsight(BaseModel):
    insight: str = Field(description="Business insight discovered from medicine data")
    category: str = Field(description="Category of the insight (e.g., pricing, trends, availability)")
    date_created: str = Field(description="Date when the insight was created")