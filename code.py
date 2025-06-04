import streamlit as st
import boto3
import json
import uuid
import re

# Streamlit config
st.set_page_config(layout="wide")
st.title("Claude 3.5 → Mermaid Flowchart Generator")

# AWS credentials
AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
AWS_SESSION_TOKEN = st.secrets["AWS_SESSION_TOKEN"]
REGION = "us-west-2"
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# Claude call
def call_claude(logic_text):
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN,
        region_name=REGION
    )
    client = session.client("bedrock-runtime")

    prompt = (
        "Convert the following phrase into a Mermaid flowchart representing the steps involved. "
        "Return only the diagram code. Start with 'flowchart TD'. No explanation, no formatting.\n\n"
        f"{logic_text}"
    )

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    }

    response = client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload)
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]

# Clean Claude output
def sanitize_mermaid_code(raw_code: str) -> str:
    code = raw_code.strip()
    code = re.sub(r"^```mermaid", "", code, flags=re.IGNORECASE).strip()
    code = re.sub(r"```$", "", code).strip()
    code = re.sub(r"--\s*>", "-->", code)
    code = re.sub(r"==>", "-->", code)
    code = re.sub(r"-{3,}>", "-->", code)
    code = re.sub(r"-->\s*\|(.*?)\|\s*", r"-- \1 -->", code)
    diagram_start = re.search(r"(flowchart\s+TD|graph\s+TD)", code, re.IGNORECASE)
    if diagram_start:
        code = code[diagram_start.start():]
    return code

# User input
default_prompt = "steps involved in a description of string"
logic_text = st.text_area("Enter a process description:", value=default_prompt, height=200)

# Track diagram
mermaid_code = None

# Generate button
if st.button("Generate Mermaid Diagram"):
    with st.spinner("Calling Claude 3.5..."):
        try:
            raw_output = call_claude(logic_text)
            mermaid_code = sanitize_mermaid_code(raw_output)

            st.subheader("Mermaid Code")
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
            st.error(f"Error: {str(e)}")

# Show download button only if code exists
if mermaid_code:
    st.subheader("Download Mermaid Diagram")
    st.download_button(
        label="Download Mermaid Code (.mmd)",
        data=mermaid_code,
        file_name="flowchart.mmd",
        mime="text/plain"
    )

    st.markdown(
        "To convert this into an image, paste the code at [https://mermaid.live](https://mermaid.live) "
        "and use the Export menu to save as PNG or SVG."
    )
