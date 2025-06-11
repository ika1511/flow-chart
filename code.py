import streamlit as st
import boto3
import json
import re
import uuid
import base64
import requests

# --- Page setup ---
st.set_page_config(
    page_title="Mermaid Diagram Generator",
    layout="wide"
)
st.title("Claude 3.5 → Mermaid Diagram Generator")

# --- AWS credentials ---
AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
AWS_SESSION_TOKEN = st.secrets["AWS_SESSION_TOKEN"]
REGION = "us-west-2"
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# --- Claude API call ---
def call_claude(description: str) -> str:
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN,
        region_name=REGION
    )
    client = session.client("bedrock-runtime")

    prompt = (
        "Convert the following description into an appropriate Mermaid diagram "
        "(flowchart, sequence, class, gantt, state, ER, etc.). "
        "Return only valid Mermaid code with no extra text or formatting.\n\n"
        f"{description}"
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
def sanitize_mermaid(raw: str) -> str:
    code = raw.strip()
    code = re.sub(r"^```mermaid", "", code, flags=re.IGNORECASE).strip()
    code = re.sub(r"```$", "", code).strip()
    return code

# --- Generate PNG from Mermaid via Kroki.io ---
def get_mermaid_image(mermaid_code: str) -> bytes:
    resp = requests.post("https://kroki.io/mermaid/png", data=mermaid_code.encode("utf-8"))
    if resp.status_code == 200:
        return resp.content
    raise RuntimeError(f"Kroki failed with status code {resp.status_code}")

# --- Session state ---
if "mermaid_code" not in st.session_state:
    st.session_state["mermaid_code"] = None
if "description" not in st.session_state:
    st.session_state["description"] = ""

# --- Input ---
description = st.text_area(
    "Describe the process, system, or interaction you’d like visualised:",
    value=st.session_state["description"],
    height=200
)

# --- Generate diagram ---
if st.button("Create Diagram"):
    with st.spinner("Generating…"):
        try:
            raw = call_claude(description)
            st.session_state["mermaid_code"] = sanitize_mermaid(raw)
            st.session_state["description"] = description
        except Exception as e:
            st.error(f"Error: {e}")

# --- Display + downloads ---
code = st.session_state["mermaid_code"]
if code:
    st.subheader("Diagram Code")
    st.code(code, language="mermaid")

    st.subheader("Rendered Diagram")
    uid = uuid.uuid4().hex
    st.components.v1.html(
        f"""
        <div id="mermaid-{uid}">
          <pre class="mermaid">{code}</pre>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>mermaid.initialize({{ startOnLoad: true }});</script>
        """,
        height=500,
        scrolling=True
    )

    st.download_button(
        "Download .mmd file",
        data=code,
        file_name="diagram.mmd",
        mime="text/plain"
    )

    try:
        img_data = get_mermaid_image(code)
        st.download_button(
            "Download PNG",
            data=img_data,
            file_name="diagram.png",
            mime="image/png"
        )
    except Exception as e:
        st.error(f"Failed to generate PNG: {e}")

    encoded = base64.b64encode(code.encode()).decode()
    live_url = f"https://mermaid.live/edit#pako={encoded}"
    st.markdown(f"[Open in Mermaid Live Editor →]({live_url})", unsafe_allow_html=True)

