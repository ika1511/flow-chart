import streamlit as st
import boto3
import json
import re
import uuid
import urllib.parse
import base64
import requests

# Page setup
st.set_page_config(layout="wide")
st.title("Claude 3.5 → Mermaid Flowchart Generator")

# AWS credentials
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

    prompt = (
        "Convert the following process into a Mermaid flowchart. "
        "Return only valid Mermaid code starting with 'flowchart TD'. No explanation, no formatting.\n\n"
        f"{logic_text}"
    )

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

# Sanitize Mermaid output
def sanitize_mermaid(raw: str):
    code = raw.strip()
    code = re.sub(r"^```mermaid", "", code, flags=re.IGNORECASE).strip()
    code = re.sub(r"```$", "", code).strip()
    if not code.startswith("flowchart TD"):
        match = re.search(r"(flowchart\s+TD.*)", code, re.IGNORECASE | re.DOTALL)
        if match:
            code = match.group(1)
    return code

# Generate PNG image using Kroki API
def get_mermaid_image(mermaid_code):
    url = "https://kroki.io/mermaid/png"
    response = requests.post(url, data=mermaid_code.encode("utf-8"))
    if response.status_code == 200:
        return response.content  # PNG bytes
    else:
        raise RuntimeError(f"Kroki failed with status code {response.status_code}")

# Text input
default = "steps involved in a description of string"
logic_text = st.text_area("Enter a process description:", value=default, height=200)

# Trigger
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
        label="Download as .mmd file",
        data=mermaid_code,
        file_name="flowchart.mmd",
        mime="text/plain"
    )

    st.subheader("Download Diagram Image")
    try:
        img_data = get_mermaid_image(mermaid_code)
        st.download_button(
            label="Download as PNG",
            data=img_data,
            file_name="flowchart.png",
            mime="image/png"
        )
    except Exception as e:
        st.error(f"❌ Failed to generate diagram image: {str(e)}")

    # Mermaid Live link
    st.subheader("Open in Mermaid Live")
    encoded = base64.b64encode(mermaid_code.encode("utf-8")).decode("utf-8")
    live_url = f"https://mermaid.live/edit#pako={encoded}"
    st.markdown(f"[Click here to view in Mermaid Live →]({live_url})", unsafe_allow_html=True)

    st.markdown(
        """
        📥 **Tip:** On the Mermaid Live site, click the download icon to export as PNG, SVG, or PDF.
        """
    )
