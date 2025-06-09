import streamlit as st
import boto3
import json
import re
import uuid
import base64
import requests

# --- Page setup ---
st.set_page_config(
    page_title="Flowchart Generator",
    page_icon="🧩",  # You can use a favicon emoji or replace with "favicon.png"
    layout="wide"
)
st.title("Claude 3.5 → Mermaid Flowchart Generator")

# --- AWS credentials ---
AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
AWS_SESSION_TOKEN = st.secrets["AWS_SESSION_TOKEN"]
REGION = "us-west-2"
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# --- Claude API call ---
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

# --- Clean Claude output ---
def sanitize_mermaid(raw: str):
    code = raw.strip()
    code = re.sub(r"^```mermaid", "", code, flags=re.IGNORECASE).strip()
    code = re.sub(r"```$", "", code).strip()
    if not code.startswith("flowchart TD"):
        match = re.search(r"(flowchart\s+TD.*)", code, re.IGNORECASE | re.DOTALL)
        if match:
            code = match.group(1)
    return code

# --- Generate PNG from Mermaid via Kroki.io ---
def get_mermaid_image(mermaid_code):
    url = "https://kroki.io/mermaid/png"
    response = requests.post(url, data=mermaid_code.encode("utf-8"))
    if response.status_code == 200:
        return response.content
    else:
        raise RuntimeError(f"Kroki failed with status code {response.status_code}")

# --- Initialize session state ---
if "mermaid_code" not in st.session_state:
    st.session_state["mermaid_code"] = None

if "logic_text" not in st.session_state:
    st.session_state["logic_text"] = "steps involved in a description of string"

# --- Text input UI ---
logic_text = st.text_area(
    "Describe your process:",
    value=st.session_state["logic_text"],
    height=200
)

# --- Generate diagram ---
if st.button("Create Flowchart"):
    with st.spinner("Calling Claude 3.5..."):
        try:
            raw_output = call_claude(logic_text)
            st.session_state["mermaid_code"] = sanitize_mermaid(raw_output)
            st.session_state["logic_text"] = logic_text  # Save text area content
        except Exception as e:
            st.error(f"Error: {str(e)}")

# --- Show diagram + download options ---
if st.session_state["mermaid_code"]:
    code = st.session_state["mermaid_code"]

    st.subheader("Flowchart Code")
    st.code(code, language="mermaid")

    st.subheader("Diagram")
    unique_id = str(uuid.uuid4()).replace("-", "")
    st.components.v1.html(f"""
        <div id="mermaid-{unique_id}">
        <pre class="mermaid">
{code}
        </pre>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>mermaid.initialize({{ startOnLoad: true }});</script>
    """, height=500, scrolling=True)

    # --- Download .mmd code ---
    st.download_button(
        label="Download as .mmd file",
        data=code,
        file_name="flowchart.mmd",
        mime="text/plain"
    )

    # --- Download PNG image via Kroki ---
    try:
        img_data = get_mermaid_image(code)
        st.download_button(
            label="Download as PNG",
            data=img_data,
            file_name="flowchart.png",
            mime="image/png"
        )
    except Exception as e:
        st.error(f"Failed to generate diagram image: {str(e)}")

    # --- Mermaid Live Editor ---
    encoded = base64.b64encode(code.encode("utf-8")).decode("utf-8")
    live_url = f"https://mermaid.live/edit#pako={encoded}"
    st.subheader("Edit in Mermaid Live")
    st.markdown(f"[Open in Mermaid Live Editor →]({live_url})", unsafe_allow_html=True)

