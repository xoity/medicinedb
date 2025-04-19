# Medicine Information Assistant

A comprehensive tool for managing medicine information with an intelligent search system and SQLite database integration.

## Features

- **Medicine Search & Database**: Search for detailed medicine information and automatically store it in a SQLite database
- **SQLite MCP Server**: Execute SQL queries directly against your medicine database
- **Dual LLM Support**: Choose between Google's Gemini API (cloud) or Ollama (local) for AI interactions
- **Data Export**: Export your medicine database to CSV format for external use

## Prerequisites

- Python 3.10+ (3.13 recommended)
- Gemini API key (optional, only for Gemini model)
- Ollama installation (optional, for local LLM support)

## Installation

### Setup Steps

1. Clone this repository
2. Create a virtual environment:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

1. Install dependencies:

```bash
pip install -r requirements.txt
```

### Setting up your API Key (Optional)

For Gemini model usage:

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Create a `.env` file in the project root with your API key:

``` bash
GEMINI_API_KEY=your_api_key_here
```

### Setting up Ollama (Optional)

For local LLM support:

1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull the required model:

```bash
ollama pull llama3
```

## Usage

### Start the MCP Server

Before starting the main application, start the FastAPI MCP server:

```bash
uvicorn mcp_server:app --reload
```

This starts the MCP server on <http://127.0.0.1:8000>, which handles SQL queries for the database.

### Start the Streamlit Application

In a new terminal (with your virtual environment activated):

```bash
streamlit run app.py
```

This will open a web browser with the Medicine Information Assistant interface.

## Application Tabs

### 1. Medicine Search & Database

This tab allows you to:

- Search for medicine information using either Gemini or Ollama
- View and add structured medicine data to your database
- Filter medicines by category, OTC status, etc.
- Export medicine data to CSV format

**Example Searches:**

- Ibuprofen
- Lisinopril
- Amoxicillin
- Metformin

### 2. SQLite MCP Server

This tab enables direct interaction with your medicine database through SQL queries:

- Execute SQL queries against your medicine database
- View formatted results in the interface
- Perform both read and write operations

**Example SQL Queries:**

```sql
-- Basic queries
SELECT * FROM medicines;
SELECT name, price, dosage FROM medicines WHERE otc = 1;

-- Advanced queries
SELECT category, AVG(price) as avg_price FROM medicines GROUP BY category;
INSERT INTO medicines (name, brand, price) VALUES ('Aspirin', 'Bayer', 5.99);
```

## API Access

The MCP server also provides REST API endpoints that can be called directly:

```bash
# Execute a read query
curl -X POST "http://127.0.0.1:8000/mcp/read_query" \
     -H "Content-Type: application/json" \
     -d '{"query": "SELECT * FROM medicines;"}'

# Execute a write query
curl -X POST "http://127.0.0.1:8000/mcp/write_query" \
     -H "Content-Type: application/json" \
     -d '{"query": "INSERT INTO medicines (name, brand, price) VALUES (\"Paracetamol\", \"Tylenol\", 4.99);"}'
```

## Troubleshooting

### MCP Server Connection Issues

If you encounter errors connecting to the MCP server:

1. Ensure the MCP server is running with `uvicorn mcp_server:app --reload`
2. Check that it's running on port 8000
3. Verify there are no firewall or network issues blocking local connections

### API Key Issues

If you see authentication errors with Gemini:

1. Verify your API key is correct in the `.env` file
2. Check that the API key is entered in the Settings section of the app
3. Ensure your API key has the necessary permissions

## License

[MIT](LICENSE)
