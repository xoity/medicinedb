import streamlit as st
import os
import asyncio
import json
from datetime import datetime
import sqlite3

import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from pydantic import SecretStr
import traceback
import logging
import io
import requests
import aiohttp


from src.utils import initialize_database, add_medicine, get_all_medicines, export_to_csv
from src.agent_runner import MedicineInfoAgent
from src.models import Medicine  # Import the Medicine model
from src.export_to_prolog import export_to_prolog  # Import the Prolog export function

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize database
initialize_database()

# Configure page settings
st.set_page_config(
    page_title="Medicine Information Assistant",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom CSS
st.markdown(
    """
<style>
    .main {
        padding: 2rem;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e6f7ff;
    }
    .bot-message {
        background-color: #f0f2f6;
    }
    .stButton button {
        width: 100%;
    }
    .sql-box {
        background-color: #2b2b2b;
        color: #f8f8f8;
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Courier New', monospace;
    }
    .insight-card {
        background-color: #f0f7ff;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        border-left: 4px solid #4285f4;
    }
    .muted-text {
        color: #666;
        font-size: 0.8rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY", "")
if "messages" not in st.session_state:
    st.session_state.messages = []
if "model_choice" not in st.session_state:
    st.session_state.model_choice = "Gemini"
if "medicines" not in st.session_state:
    st.session_state.medicines = []
if "mcp_messages" not in st.session_state:
    st.session_state.mcp_messages = []

# Function to check if Ollama is running
def is_ollama_running():
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

# Function to initialize LLM based on model choice
def get_llm(model_choice="Gemini"):
    if model_choice == "Ollama":
        if not is_ollama_running():
            st.error("Ollama is not running. Please start Ollama and try again.")
            return None
        return ChatOllama(model="llama3", num_ctx=32000)
    else:  # Default to Gemini
        api_key = st.session_state.api_key
        if not api_key:
            st.error("Please enter your Gemini API key in the Settings section.")
            return None
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp", api_key=SecretStr(api_key)
        )

# Function to run medicine info search
async def search_medicine_info(medicine_name):
    llm = get_llm(st.session_state.model_choice)
    if not llm:
        return None

    agent = MedicineInfoAgent(llm=llm, medicine_name=medicine_name)
    result = await agent.run()

    if result:
        logger.info(f"Agent returned results: {result}")
        
        # Create a new Medicine object
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Default values for required fields
        name = result.get("name", medicine_name)
        brand = result.get("brand", "N/A") 
        category = result.get("category", "N/A")
        dosage = result.get("dosage", "N/A")
        
        # Create medicine object with all required fields
        medicine = Medicine(
            name=name,
            brand=brand,
            price=0.0,  # Default price since not extracted
            dosage=dosage,
            form="Various",  # Default form
            otc=False,  # Default to prescription required
            description=f"Information extracted from drugs.com: {name} in category {category}",
            side_effects="Please consult your healthcare provider for side effects information.",
            category=category,
            date_added=today
        )
        
        # Log the created medicine object
        logger.info(f"Created medicine object: {medicine.model_dump()}")

        # Add the medicine to the database
        add_medicine(medicine)
        
        # Automatically reload medicines list after adding to database
        load_medicines()
        
        # Return the medicine for display
        return medicine

    return None

# Function to run SQLite MCP query
async def run_mcp_query(prompt):
    """Execute a query on the SQLite database through the MCP server API.

    The function determines the appropriate endpoint based on the query type:
    - Queries containing write operations (e.g., INSERT, UPDATE, DELETE, CREATE, ALTER, DROP) are sent to the write_query endpoint.
    - All other queries are sent to the read_query endpoint.

    If the prompt is not a valid SQL query, an error message will be returned.
    """
    # Default to read query endpoint since it's safer
    endpoint = "http://127.0.0.1:8000/mcp/read_query"
    
    # Check if query is a write operation (INSERT, UPDATE, DELETE, etc.)
    write_operations = ["INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"]
    if any(op in prompt.upper() for op in write_operations):
        endpoint = "http://127.0.0.1:8000/mcp/write_query"
    
    try:
        # Send request to MCP server
        async with aiohttp.ClientSession() as session, session.post(
            endpoint,
            json={"query": prompt},
            headers={"Content-Type": "application/json"}
        ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": f"Error {response.status}: {error_text}"}
    except aiohttp.ClientConnectorError:
        return {
            "error": "Cannot connect to MCP server. Please make sure it's running with: uvicorn mcp_server:app --reload"
        }
    except Exception as e:
        return {"error": f"Error executing query: {str(e)}"}

# Function to load medicines from database
def load_medicines():
    try:
        medicines_db = get_all_medicines()
        if medicines_db and medicines_db.medicines:
            st.session_state.medicines = medicines_db.medicines
            return True
        return False
    except Exception as e:
        st.error(f"Error loading medicines: {e}")
        return False

# Define the get_selected_category function

def get_selected_category(df):
    if 'category' in df.columns:
        categories = ["All"] + sorted(df['category'].unique().tolist())
        return st.selectbox("Filter by Category", categories, key="filter_category")
    return "All"

# Sidebar
with st.sidebar:
    st.title("Medicine Info Assistant")

    # Settings section
    with st.expander("Settings"):
        st.text_input(
            "API Key",
            value=st.session_state.api_key,
            key="input_api_key",
            type="password",
            help="Enter your Gemini API key (only needed for Gemini model)",
        )
        
        # Model selection dropdown
        model_options = ["Gemini", "Ollama"]
        selected_model = st.selectbox(
            "Choose LLM Model",
            options=model_options,
            index=model_options.index(st.session_state.model_choice),
            help="Select Gemini (cloud) or Ollama (local)",
            key="model_choice_select"
        )
        
        if st.button("Apply Settings"):
            st.session_state.api_key = st.session_state.input_api_key
            st.session_state.model_choice = st.session_state.model_choice_select
            st.success("Settings applied!")

    # Database section
    with st.expander("Database"):
        if st.button("Load Medicines"):
            if load_medicines():
                st.success(f"Loaded {len(st.session_state.medicines)} medicines!")
            else:
                st.warning("No medicines found in database.")
                
        if st.button("Export to CSV"):
            csv_path = export_to_csv()
            if csv_path:
                with open(csv_path, "rb") as f:
                    st.download_button(
                        label="Download CSV",
                        data=f,
                        file_name="medicines.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("No data to export.")
        
        if st.button("Export to Prolog"):
            try:
                output_file = os.path.join(os.getcwd(), "medicines.pl")
                export_to_prolog("medicine.db", output_file)
                st.success(f"Exported medicine data to Prolog file: medicines.pl")
                with open(output_file, "r") as f:
                    prolog_content = f.read()
                    st.download_button(
                        label="Download Prolog File",
                        data=prolog_content,
                        file_name="medicines.pl",
                        mime="text/plain"
                    )
            except Exception as e:
                st.error(f"Error exporting to Prolog: {e}")

# Main content
# Create tabs for different functionalities
tab1, tab2 = st.tabs(["Medicine Search & Database", "SQLite MCP Server"])

# Tab 1: Medicine Search
with tab1:
    st.header("Medicine Information Search")
    st.markdown("""
    Use this tool to search for information about medications. Enter a medicine name below and the AI will search
    for details like price, dosage, and whether it's available over-the-counter. Results can be automatically 
    added to the SQLite database.
    
    Try searching for medicines like:
    - Ibuprofen
    - Lisinopril
    - Amoxicillin
    - Metformin
    """)
    
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        medicine_name = st.text_input("Enter medicine name", key="medicine_search")
    
    with search_col2:
        extract_data = st.checkbox("Extract structured data", value=True)
        search_button = st.button("Search", type="primary", use_container_width=True)
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "medicine_data" in message:
                medicine_data = message["medicine_data"]
                with st.expander("View structured medicine data"):
                    st.json(medicine_data.model_dump())
                    if st.button("Add to Database", key=f"add_{medicine_data.name}"):
                        try:
                            add_medicine(medicine_data)
                            st.success(f"Added {medicine_data.name} to database!")
                            # Reload medicines list
                            load_medicines()
                        except Exception as e:
                            st.error(f"Error adding medicine: {e}")
    
    # Handle search button click
    if search_button and medicine_name:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": f"Find information about {medicine_name}"})
        
        # Show assistant is thinking
        with st.chat_message("assistant"):
            thinking = st.empty()
            thinking.markdown("Searching for medicine information...")
            
            try:
                # Run medicine info search
                result = asyncio.run(search_medicine_info(medicine_name))
                
                if result:
                    if extract_data and hasattr(result, "medicines") and result.medicines:
                        # Process structured medicine data
                        medicine = result  
                        medicine_info = f"""
                        ### {medicine.name}
                        
                        **Brand**: {medicine.brand}  
                        **Price**: ${medicine.price:.2f}  
                        **Dosage**: {medicine.dosage}  
                        **Form**: {medicine.form}  
                        **Prescription Required**: {"No" if medicine.otc else "Yes"}
                        
                        **Description**:  
                        {medicine.description}
                        
                        **Side Effects**:  
                        {medicine.side_effects}
                        
                        **Category**: {medicine.category}
                        """
                        
                        # Add assistant message with structured data
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": medicine_info,
                            "medicine_data": medicine
                        })
                        
                        # Update the thinking message with the result
                        thinking.markdown(medicine_info)
                        
                        with st.expander("View structured medicine data"):
                            st.json(medicine.model_dump())
                            if st.button("Add to Database"):
                                try:
                                    add_medicine(medicine)
                                    st.success(f"Added {medicine.name} to database!")
                                    # Reload medicines list
                                    load_medicines()
                                except Exception as e:
                                    st.error(f"Error adding medicine: {e}")
                    else:
                        # Handle unstructured result (narrative response)
                        response = "I couldn't find structured information about this medicine."
                        
                        if hasattr(result, "__iter__"):
                            # Try to extract narrative response from agent steps
                            for step in result:
                                if isinstance(step, tuple) and len(step) > 1 and isinstance(step[1], dict) and "done" in step[1]:
                                    if isinstance(step, dict) and "action" in step:
                                        done_data = step["action"].get("done", {})
                                    else:
                                        done_data = {}
                                    if isinstance(done_data, dict) and done_data.get("success") and "text" in done_data:
                                        response = done_data["text"]
                                        break
                        
                        # Add assistant message without structured data
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": response
                        })
                        
                        # Update the thinking message with the result
                        thinking.markdown(response)
                else:
                    error_message = "Sorry, I couldn't find information about this medicine."
                    st.session_state.messages.append({"role": "assistant", "content": error_message})
                    thinking.markdown(error_message)
            
            except Exception as e:
                error_message = f"Error searching for medicine information: {str(e)}"
                st.session_state.messages.append({"role": "assistant", "content": error_message})
                thinking.markdown(error_message)
                st.error(traceback.format_exc())
    
    # Display medicine database
    st.subheader("Medicine Database")
    
    # Load medicines if not already loaded
    if not st.session_state.medicines:
        load_medicines()
    
    if st.session_state.medicines:
        # Convert to DataFrame for display
        medicines_data = [m.model_dump() for m in st.session_state.medicines]
        df = pd.DataFrame(medicines_data)
        
        # Filter options
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        with filter_col1:
            filter_otc = st.checkbox("OTC Only", value=False, key="filter_otc")
        with filter_col2:
            selected_category = get_selected_category(df)
        with filter_col3:
            sort_option = st.selectbox("Sort by", ["Name", "Price (Low to High)", "Price (High to Low)"], key="sort_option")
        
        # Apply filters
        filtered_df = df.copy()
        
        if filter_otc:
            filtered_df = filtered_df[filtered_df['otc']]
            
        if selected_category != "All":
            filtered_df = filtered_df[filtered_df['category'] == selected_category]
            
        # Apply sorting
        if sort_option == "Name":
            filtered_df = filtered_df.sort_values(by="name")
        elif sort_option == "Price (Low to High)":
            filtered_df = filtered_df.sort_values(by="price")
        elif sort_option == "Price (High to Low)":
            filtered_df = filtered_df.sort_values(by="price", ascending=False)
        
        # Display the filtered DataFrame
        st.dataframe(filtered_df, use_container_width=True)
        
        # Export options
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            if st.button("Export Filtered Data to CSV"):
                csv_buffer = io.StringIO()
                filtered_df.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue().encode("utf-8")
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name="filtered_medicines.csv",
                    mime="text/csv",
                )
    else:
        st.info("No medicines in database. Use the search function to add medicines.")

# Tab 2: SQLite MCP Server
with tab2:
    st.header("SQLite MCP Server")
    st.markdown("""
    This tab provides access to the SQLite Model Context Protocol (MCP) server for advanced database operations and analysis. 
    You can execute SQL queries, analyze medicine data, and generate insights.
    
    **Available Tools:**
    - **read_query**: Execute SELECT queries to read data from the database
    - **write_query**: Execute INSERT, UPDATE, or DELETE queries to modify data
    - **create_table**: Create new tables in the database
    - **list_tables**: Get a list of all tables in the database
    - **describe-table**: View schema information for a specific table
    - **append_insight**: Add new business insights to the memo resource
    
    **Examples:**
    - "Show me all over-the-counter medicines that cost less than $10"
    - "What are the most common medicine categories in our database?"
    - "Create a summary of price ranges by medicine category"
    """)
    
    mcp_prompt = st.text_area("Enter your SQLite MCP instruction", height=100, 
                              placeholder="Example: Show me all medicines sorted by price")
    
    mcp_button = st.button("Run MCP Query", type="primary")
    
    # Display MCP chat history
    for message in st.session_state.mcp_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Handle MCP button click
    if mcp_button and mcp_prompt:
        # Add user message
        st.session_state.mcp_messages.append({"role": "user", "content": mcp_prompt})
        
        # Show assistant is thinking
        with st.chat_message("assistant"):
            thinking = st.empty()
            thinking.markdown("Processing your request...")
            
            try:
                # Run MCP query
                result = asyncio.run(run_mcp_query(mcp_prompt))
                
                if result:
                    # Process the direct JSON response from the MCP server
                    if "error" in result:
                        # Handle error response
                        error_message = result["error"]
                        st.session_state.mcp_messages.append({"role": "assistant", "content": f"Error: {error_message}"})
                        thinking.markdown(f"Error: {error_message}")
                    elif "results" in result:
                        # Handle successful read_query response
                        results = result["results"]
                        if results:
                            # Convert results to DataFrame for better display
                            # First, get column names from the database
                            conn = sqlite3.connect('medicine.db')
                            cursor = conn.cursor()
                            cursor.execute(f"PRAGMA table_info(medicines)")
                            columns = [info[1] for info in cursor.fetchall()]
                            conn.close()
                            
                            # Create DataFrame with column names
                            df = pd.DataFrame(results, columns=columns)
                            
                            # Format response
                            response = "**Query Results:**\n\n"
                            response += df.to_markdown()
                            
                            st.session_state.mcp_messages.append({"role": "assistant", "content": response})
                            thinking.markdown(response)
                        else:
                            response = "Query executed successfully, but no results were returned."
                            st.session_state.mcp_messages.append({"role": "assistant", "content": response})
                            thinking.markdown(response)
                    elif "message" in result:
                        # Handle successful write_query response
                        message = result["message"]
                        st.session_state.mcp_messages.append({"role": "assistant", "content": message})
                        thinking.markdown(message)
                    else:
                        # Fallback for unexpected response format
                        response = f"Received response: {json.dumps(result, indent=2)}"
                        st.session_state.mcp_messages.append({"role": "assistant", "content": response})
                        thinking.markdown(response)
                else:
                    error_message = "Sorry, I couldn't process your request."
                    st.session_state.mcp_messages.append({"role": "assistant", "content": error_message})
                    thinking.markdown(error_message)
            
            except Exception as e:
                error_message = f"Error processing MCP request: {str(e)}"
                st.session_state.mcp_messages.append({"role": "assistant", "content": error_message})
                thinking.markdown(error_message)
                st.error(traceback.format_exc())

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center;'><small>Medicine Information Assistant • Powered by SQLite MCP</small></div>", unsafe_allow_html=True)
