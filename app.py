import streamlit as st
import pandas as pd
import groq
from groq import Groq
import os
import json
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# --- PART 1: THE DATA BACKEND (Our "Tool") ---

def search_companies(
    company_type=None,
    min_employees=None,
    max_employees=None,
    min_turnover=None,
    max_turnover=None,
    geography=None,
    sni_code=None,
    exclude_company_type=None, # New parameter for negative filtering
    **kwargs, # Accept and ignore any other unexpected arguments
):
    """
    Searches and filters a DataFrame of Swedish companies based on multiple criteria.
    
    Returns:
        str: A JSON string of the search results, required for the tool API.
    """
    try:
        # Use a relative path that works with Streamlit's execution environment
        file_path = "sample_rows.csv"
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        return json.dumps([{"error": f"Data file 'sample_row.csv' not found."}])

    results = df.copy()

    # Sanitize all inputs to handle bad data from the LLM
    if not isinstance(min_employees, (int, float)) or min_employees == '':
        min_employees = None
    if not isinstance(max_employees, (int, float)) or max_employees == '':
        max_employees = None
    if not isinstance(min_turnover, (int, float)) or min_turnover == '':
        min_turnover = None
    if not isinstance(max_turnover, (int, float)) or max_turnover == '':
        max_turnover = None
    if not isinstance(geography, str) or geography.strip() == '':
        geography = None
    if not isinstance(sni_code, str) or sni_code.strip() == '':
        sni_code = None
    if not isinstance(company_type, str) or company_type.strip() == '':
        company_type = None
    if not isinstance(exclude_company_type, str) or exclude_company_type.strip() == '':
        exclude_company_type = None

    # Apply filters
    if company_type:
        results = results[results["Entity type"].str.contains(company_type, case=False, na=False)]
    
    # --- FIX: Added logic for negative filtering ---
    if exclude_company_type:
        results = results[~results["Entity type"].str.contains(exclude_company_type, case=False, na=False)]
    
    if min_employees is not None:
        results = results[results["2024- Employees"] >= int(min_employees)]
    if max_employees is not None:
        results = results[results["2024- Employees"] <= int(max_employees)]
    if min_turnover is not None:
        results = results[results["2024- Turnover"] >= int(min_turnover)]
    if max_turnover is not None:
        results = results[results["2024- Turnover"] <= int(max_turnover)]
    if sni_code:
        results = results[results["SNI"].astype(str).str.contains(sni_code, na=False)]
    if geography:
        geo_cols = ["Company visiting county", "Company visiting postal area", "Munipality of seat"]
        for col in geo_cols:
            results[col] = results[col].fillna('')
        results = results[
            results["Company visiting county"].str.contains(geography, case=False) |
            results["Company visiting postal area"].str.contains(geography, case=False) |
            results["Munipality of seat"].str.contains(geography, case=False)
        ]

    if not results.empty:
        output_columns = [
            'Organization number', 'Company name', '2024- Employees', 
            '2024- Turnover', 'Profit', 'Entity type', 'Company visiting address', 
            'Company visiting postal area', 'Munipality of seat', 'SNI'
        ]
        output_columns = [col for col in output_columns if col in results.columns]
        output_df = results.head(10)[output_columns]
        return output_df.to_json(orient='records')
    else:
        return json.dumps([])


# --- PART 2: STREAMLIT UI AND CHATBOT LOGIC ---

st.set_page_config(page_title="Swedish Company Prospecting Chatbot", layout="wide")

st.title("🇸🇪 Swedish Company Prospecting Chatbot")
st.caption("Ask me to find companies based on size, turnover, location, and more!")

# --- API Key Management (from .env file) ---
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    st.error("`GROQ_API_KEY` not found.")
    st.info("Please create a `.env` file in the app's root directory and add your Groq API key to it. For example: `GROQ_API_KEY='gsk_...'`")
    st.stop()

client = Groq(api_key=groq_api_key)

# --- Chat History Management ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant for finding Swedish companies. You can filter by various criteria. You also support negative filtering for company types."
        },
        {
            "role": "assistant",
            "content": "How can I help you find Swedish companies today?"
        }
    ]

# Display chat messages
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# --- Helper function to process the stream ---
def stream_generator(stream):
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

# --- Main Chat Input and Logic ---
if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=st.session_state.messages,
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "search_companies",
                        "description": "Searches for Swedish companies. Supports filtering by type, employees, turnover, geography, and SNI code. Also supports excluding a company type.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "company_type": {"type": "string", "description": "The legal form to include (e.g., 'Aktiebolag')."},
                                "exclude_company_type": {"type": "string", "description": "A company type to exclude from the search."},
                                "min_employees": {"type": "integer", "description": "Minimum number of employees."},
                                "max_employees": {"type": "integer", "description": "Maximum number of employees."},
                                "min_turnover": {"type": "integer", "description": "Minimum turnover value."},
                                "max_turnover": {"type": "integer", "description": "Maximum turnover value."},
                                "geography": {"type": "string", "description": "A location like a city or county."},
                                "sni_code": {"type": "string", "description": "An SNI industry code."},
                            },
                        },
                    },
                }],
                tool_choice="auto",
            )
            response_message = response.choices[0].message

        except groq.APIError as e:
            st.error(f"An API error occurred: {e}")
            st.stop()

        if response_message.tool_calls:
            assistant_message_dict = {
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [
                    {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in response_message.tool_calls
                ]
            }
            st.session_state.messages.append(assistant_message_dict)
            
            tool_call = response_message.tool_calls[0]
            function_name = tool_call.function.name

            if function_name == "search_companies":
                function_args = json.loads(tool_call.function.arguments)
                
                # --- FIX: Map the new negative filter argument ---
                arg_map = {
                    'entity_type_neq': 'exclude_company_type',
                    'exclude_company_type': 'exclude_company_type',
                    'company_type': 'company_type',
                    'geography': 'geography',
                    'min_employees': 'min_employees',
                    'max_employees': 'max_employees',
                    'min_turnover': 'min_turnover',
                    'max_turnover': 'max_turnover',
                    'sni_code': 'sni_code'
                }
                mapped_args = {arg_map.get(k, k): v for k, v in function_args.items()}

                function_response_json = search_companies(**mapped_args)
                function_response_data = json.loads(function_response_json)

                if not function_response_data or (isinstance(function_response_data, list) and len(function_response_data) > 0 and isinstance(function_response_data[0], dict) and "error" in function_response_data[0]):
                    final_response = "I couldn't find any companies matching your criteria." if not function_response_data else f"🛑 Error: {function_response_data[0]['error']}"
                    st.markdown(final_response)
                    st.session_state.messages.append({"role": "assistant", "content": final_response})
                else:
                    st.session_state.messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response_json,
                    })
                    
                    stream = client.chat.completions.create(
                        model="llama3-70b-8192",
                        messages=st.session_state.messages,
                        stream=True,
                    )
                    
                    full_response = st.write_stream(stream_generator(stream))
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
        else:
            st.markdown(response_message.content)
            st.session_state.messages.append({"role": "assistant", "content": response_message.content})
