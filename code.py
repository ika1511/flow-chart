import streamlit as st
import boto3
import json
import uuid
import re

# Streamlit UI config
st.set_page_config(layout="wide")
st.title("Claude 3.5 → Mermaid Flowchart Generator")

# AWS credentials from Streamlit secrets
AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
AWS_SESSION_TOKEN = st.secrets["AWS_SESSION_TOKEN"]
REGION = "us-west-2"
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# Claude 3.5 API call
def call_claude(logic_text):
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN,
        region_name=REGION
    )

    client = session.client("bedrock-runtime")

    prompt = (
        "Convert the following logic into a Mermaid flowchart. "
        "Return only the Mermaid code. Do not include explanations or introductory text. "
        "The output must begin with 'flowchart TD' or 'graph TD'.\n\n"
        f"{logic_text}"
    )

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.3,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt}
                ]
            }
        ]
    }

    response = client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload)
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]

# Clean and extract Mermaid code only
def sanitize_mermaid_code(raw_code: str) -> str:
    code = raw_code.strip()

    # Extract from first valid line starting with 'flowchart TD' or 'graph TD'
    diagram_start = re.search(r"(flowchart\s+TD|graph\s+TD)", code, re.IGNORECASE)
    if diagram_start:
        code = code[diagram_start.start():]

    # Normalize arrows
    code = re.sub(r"--\s*>", "-->", code)
    code = re.sub(r"==>", "-->", code)
    code = re.sub(r"-{3,}>", "-->", code)
    code = re.sub(r"-->\s*\|(.*?)\|\s*", r"-- \1 -->", code)

    return code

# UI input and rendering
logic_text = st.text_area("Enter a logical process description:", height=200)

if st.button("Generate Mermaid Diagram"):
    if logic_text.strip():
        with st.spinner("Calling Claude 3.5..."):
            try:
                raw_output = call_claude(logic_text)
                mermaid_code = sanitize_mermaid_code(raw_output)

                st.subheader("Mermaid Code (Cleaned)")
                st.code(mermaid_code, language="mermaid")

                st.subheader("Rendered Diagram")
                unique_id = str(uuid.uuid4()).replace("-", "")
                st.components.v1.html(f"""
                    <div id="mermaid-{unique_id}">
                      <pre class="mermaid">
{mermaid_code}
                      </pre>
                    </div>
                    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
                    <script>mermaid.initialize({{ startOnLoad: true }});</script>
                """, height=500, scrolling=True)
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
    else:
        st.warning("Please enter a process description first.")
