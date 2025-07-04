# import pandas as pd
# from groq import Groq
# import os
# import json

# # --- PART 1: THE DATA BACKEND (Our "Tool") ---

# def search_companies(
#     company_type=None,
#     min_employees=None,
#     max_employees=None,
#     min_turnover=None,
#     max_turnover=None,
#     geography=None,
#     sni_code=None,
# ):
#     """
#     Searches and filters a DataFrame of Swedish companies based on multiple criteria.
    
#     Returns:
#         list: A list of dictionaries representing the search results.
#     """
#     try:
#         script_dir = os.path.dirname(os.path.abspath(__file__))
#         # Corrected the filename to match the uploaded file
#         file_path = os.path.join(script_dir, "sample_rows.csv")
#         df = pd.read_csv(file_path)
#     except FileNotFoundError:
#         return [{"error": f"Data file 'sample_rows.csv' could not be found at the expected path: {file_path}"}]

#     results = df.copy()

#     # --- FIX: Sanitize numeric inputs to handle bad data from the LLM ---
#     # The LLM sometimes sends empty strings "" instead of numbers. This converts them to None.
#     if min_employees == '' or not isinstance(min_employees, (int, float)):
#         min_employees = None
#     if max_employees == '' or not isinstance(max_employees, (int, float)):
#         max_employees = None
#     if min_turnover == '' or not isinstance(min_turnover, (int, float)):
#         min_turnover = None
#     if max_turnover == '' or not isinstance(max_turnover, (int, float)):
#         max_turnover = None
#     # --- End of sanitization fix ---

#     # Apply filters based on the arguments provided
#     if company_type:
#         results = results[results["Entity type"].str.contains(company_type, case=False, na=False)]

#     if min_employees is not None:
#         results = results[results["2024- Employees"] >= int(min_employees)]

#     if max_employees is not None:
#         results = results[results["2024- Employees"] <= int(max_employees)]

#     if min_turnover is not None:
#         results = results[results["2024- Turnover"] >= int(min_turnover)]

#     if max_turnover is not None:
#         results = results[results["2024- Turnover"] <= int(max_turnover)]

#     if sni_code:
#         results = results[results["SNI"].astype(str).str.contains(sni_code, na=False)]

#     if geography:
#         geo_cols = ["Company visiting county", "Company visiting postal area", "Munipality of seat"]
#         for col in geo_cols:
#             results[col] = results[col].fillna('')
            
#         results = results[
#             results["Company visiting county"].str.contains(geography, case=False) |
#             results["Company visiting postal area"].str.contains(geography, case=False) |
#             results["Munipality of seat"].str.contains(geography, case=False)
#         ]

#     if not results.empty:
#         output_df = results[['Company name', '2024- Employees', '2024- Turnover', 'Entity type', 'Munipality of seat']]
#         return output_df.to_dict(orient='records')
#     else:
#         return []


# # --- PART 2: THE LLM INTEGRATION (The "Brain") ---

# def run_chatbot():
#     """
#     Initializes the Groq model and runs the main interactive chat loop.
#     """
#     try:
#         client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
#     except Exception:
#         print("🛑 Error: GROQ_API_KEY environment variable not set.")
#         return

#     print("🤖 Chatbot initialized with Groq. Ask me to find companies in Sweden!")
#     print("   Type 'exit' to end the conversation.")

#     messages = []

#     while True:
#         user_input = input("You: ")
#         if user_input.lower() == 'exit':
#             print("👋 Goodbye!")
#             break

#         messages.append({"role": "user", "content": user_input})

#         try:
#             # --- FIX: Wrap the API call in a try-except block to prevent crashes ---
#             response = client.chat.completions.create(
#                 model="llama3-70b-8192",
#                 messages=messages,
#                 tools=[
#                     {
#                         "type": "function",
#                         "function": {
#                             "name": "search_companies",
#                             "description": "Searches and filters a database of Swedish companies based on criteria.",
#                             "parameters": {
#                                 "type": "object",
#                                 "properties": {
#                                     "company_type": {"type": "string", "description": "The legal form of the company, e.g., 'Aktiebolag'"},
#                                     "min_employees": {"type": "integer", "description": "The minimum number of employees."},
#                                     "max_employees": {"type": "integer", "description": "The maximum number of employees."},
#                                     "min_turnover": {"type": "integer", "description": "The minimum turnover value."},
#                                     "max_turnover": {"type": "integer", "description": "The maximum turnover value."},
#                                     "geography": {"type": "string", "description": "A location like a city, county, or postal area."},
#                                     "sni_code": {"type": "string", "description": "An SNI industry code."},
#                                 },
#                             },
#                         },
#                     }
#                 ],
#                 tool_choice="auto",
#             )
#             response_message = response.choices[0].message
        
#         except Groq.BadRequestError as e:
#             print("Bot: I had trouble understanding that. Could you please rephrase your request?")
#             # Remove the last message that caused the error to avoid a loop
#             messages.pop()
#             continue # Skip the rest of the loop and ask for new input

#         if response_message.tool_calls:
#             print(f"🧠 LLM wants to call a tool...")
            
#             tool_call = response_message.tool_calls[0]
#             function_name = tool_call.function.name
            
#             if function_name == "search_companies":
#                 function_args = json.loads(tool_call.function.arguments)
#                 print(f"   Function: search_companies")
#                 print(f"   Arguments: {function_args}")
                
#                 results_data = search_companies(**function_args)
                
#                 print("Bot: ")
#                 if results_data:
#                     if isinstance(results_data[0], dict) and "error" in results_data[0]:
#                         print(f"🛑 Error: {results_data[0]['error']}")
#                     else:
#                         print("I found the following companies matching your criteria:")
#                         for company in results_data:
#                             print(f"  - Name: {company.get('Company name', 'N/A')}")
#                             print(f"    Employees: {company.get('2024- Employees', 'N/A')}")
#                             print(f"    Turnover: {company.get('2024- Turnover', 'N/A')}")
#                             print(f"    Location: {company.get('Munipality of seat', 'N/A')}")
#                             print(f"    SNI Code: {company.get('SNI', 'N/A')}")
#                             print("-" * 20)
#                 else:
#                     print("I couldn't find any companies that match your criteria.")

#         else:
#             final_answer = response_message.content
#             print(f"Bot: {final_answer}")
#             messages.append({"role": "assistant", "content": final_answer})

# # --- PART 3: RUN THE APPLICATION ---
# if __name__ == "__main__":
#     run_chatbot()


import streamlit as st
import pandas as pd
from groq import Groq
import os
import json

# --- PART 1: THE DATA BACKEND (Our "Tool") ---
# This function is the same as before, it searches the local CSV file.

def search_companies(
    company_type=None,
    min_employees=None,
    max_employees=None,
    min_turnover=None,
    max_turnover=None,
    geography=None,
    sni_code=None,
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
        return json.dumps([{"error": f"Data file 'sample_rows.csv' not found."}])

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
    if not geography or geography.strip() == '':
        geography = None
    if not sni_code or sni_code.strip() == '':
        sni_code = None
    if not company_type or company_type.strip() == '':
        company_type = None

    # Apply filters
    if company_type:
        results = results[results["Entity type"].str.contains(company_type, case=False, na=False)]
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

# --- API Key Management in Sidebar ---
with st.sidebar:
    st.header("Configuration")
    groq_api_key = st.text_input("Groq API Key", type="password")
    if not groq_api_key:
        st.info("Please add your Groq API key to continue.")
        st.stop()

client = Groq(api_key=groq_api_key)

# --- Chat History Management ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that helps users find information about Swedish companies. When you receive data from a tool, present it to the user in a clear and friendly summary. If no results are found, say so politely."
        },
        {
            "role": "assistant",
            "content": "How can I help you find Swedish companies today?"
        }
    ]

# Display chat messages from history
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# --- Helper function to process the stream for st.write_stream ---
def stream_generator(stream):
    """
    This generator function extracts the text content from the Groq stream
    and yields it, so st.write_stream can display it correctly.
    """
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
                        "description": "Searches and filters a database of Swedish companies.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "company_type": {"type": "string", "description": "The legal form of the company."},
                                "min_employees": {"type": "integer", "description": "The minimum number of employees."},
                                "max_employees": {"type": "integer", "description": "The maximum number of employees."},
                                "min_turnover": {"type": "integer", "description": "The minimum turnover value."},
                                "max_turnover": {"type": "integer", "description": "The maximum turnover value."},
                                "geography": {"type": "string", "description": "A location like a city or county."},
                                "sni_code": {"type": "string", "description": "An SNI industry code."},
                            },
                        },
                    },
                }],
                tool_choice="auto",
            )
            response_message = response.choices[0].message

        except Groq.APIError as e:
            st.error(f"An API error occurred: {e}")
            st.stop()

        if response_message.tool_calls:
            st.session_state.messages.append(response_message)
            tool_call = response_message.tool_calls[0]
            function_name = tool_call.function.name

            if function_name == "search_companies":
                function_args = json.loads(tool_call.function.arguments)
                
                function_response_json = search_companies(**function_args)
                function_response_data = json.loads(function_response_json)

                if not function_response_data or (isinstance(function_response_data[0], dict) and "error" in function_response_data[0]):
                    if not function_response_data:
                        final_response = "I searched the data but couldn't find any companies that match your criteria."
                    else:
                        final_response = f"🛑 Error: {function_response_data[0]['error']}"
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
                    
                    # Use the new generator with st.write_stream
                    full_response = st.write_stream(stream_generator(stream))
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
        else:
            st.markdown(response_message.content)
            st.session_state.messages.append({"role": "assistant", "content": response_message.content})
