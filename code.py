import streamlit as st
import boto3
import json
import re
import uuid
import urllib.parse
import subprocess

# Streamlit setup
st.set_page_config(layout="wide")
st.title("Claude 3.5 → Mermaid Flowchart Generator")

# AWS credentials from secrets
AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
AWS_SESSION_TOKEN = st.secrets["AWS_SESSION_TOKEN"]
REGION = "us-west-2"
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# Claude API call
def call_claude(logic_text):
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN,
        region_name=REGION
    )
    client = session.client("bedrock-runtime")

    prompt = logic_text

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.2,
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

# Clean diagram
def sanitize_mermaid(raw):
    code = raw.strip()
    code = re.sub(r"^```mermaid", "", code, flags=re.IGNORECASE).strip()
    code = re.sub(r"```$", "", code).strip()
    if not code.startswith("flowchart TD"):
        match = re.search(r"(flowchart\s+TD.*)", code, re.IGNORECASE | re.DOTALL)
        if match:
            code = match.group(1)
    return code

# Generate diagram image using mermaid-cli
def generate_diagram_image(code: str, filename="flowchart.png"):
    with open("diagram.mmd", "w") as f:
        f.write(code)
    subprocess.run(["mmdc", "-i", "diagram.mmd", "-o", filename], check=True)
    with open(filename, "rb") as f:
        return f.read()

# Text input (use original prompt)
def_prompt = "steps involved in a description of string"
logic_text = st.text_area("Enter your process description (prompt):", value=def_prompt, height=200)

# Generate diagram
mermaid_code = None
if st.button("Generate Diagram"):
    with st.spinner("Calling Claude 3.5..."):
        try:
            raw_output = call_claude(logic_text)
            mermaid_code = sanitize_mermaid(raw_output)

            st.subheader("Mermaid Code")
            st.code(mermaid_code, language="mermaid")

            st.subheader("Diagram")
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
            st.error(f"❌ Error: {str(e)}")

# If diagram exists
if mermaid_code:
    st.subheader("Download Mermaid Code")
    st.download_button(
        label="Download .mmd file",
        data=mermaid_code,
        file_name="diagram.mmd",
        mime="text/plain"
    )

    st.subheader("Download Diagram as PNG (requires mermaid-cli)")
    try:
        image_bytes = generate_diagram_image(mermaid_code)
        st.download_button(
            label="Download Diagram as PNG",
            data=image_bytes,
            file_name="flowchart.png",
            mime="image/png"
        )
    except Exception as e:
        st.error(f"Diagram rendering failed: {e}")

    st.subheader("Open in Mermaid Live")
    encoded = urllib.parse.quote(mermaid_code)
    live_url = f"https://mermaid.live/edit#code={encoded}"
    st.markdown(f"[Click here to view in Mermaid Live →]({live_url})", unsafe_allow_html=True)

