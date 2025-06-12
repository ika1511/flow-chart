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

# --- Sidebar Controls ---
st.sidebar.title("🛠 Settings")
mode = st.sidebar.radio("Choose output mode", ["Generate Diagram", "Elaborate Description"])

examples = {
    "Login Flow": "User enters email → System checks → Show dashboard or error",
    "Class Diagram": "Class Vehicle → subclass Car and Bike → Car has engineType",
    "Gantt Chart": "Design (3d), Develop (5d), Test (2d)"
}
selected = st.sidebar.selectbox("Try an example", [""] + list(examples.keys()))
if selected:
    st.session_state["description"] = examples[selected]

if st.sidebar.button("Clear"):
    st.session_state["mermaid_code"] = None
    st.session_state["description"] = ""

# --- Claude API call ---
def call_claude(description: str, mode: str) -> str:
    if mode == "Generate Diagram":
        prompt = (
            "Based on the following user description, generate a Mermaid diagram. "
            "You may choose from flowchart, sequence, class, gantt, state, or ER diagram. "
            "Output only valid Mermaid code — no extra explanation.\n\n"
            f"{description.strip()}"
        )
    elif mode == "Elaborate Description":
        prompt = (
            "Take the following brief process description and elaborate on it. "
            "List the logical steps clearly and explain what happens at each stage.\n\n"
            f"{description.strip()}"
        )

    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN,
        region_name=REGION
    )
    client = session.client("bedrock-runtime")

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

# --- Sanitize Mermaid output ---
def sanitize_mermaid(raw: str) -> str:
    code = raw.strip()
    code = re.sub(r"^```mermaid", "", code, flags=re.IGNORECASE).strip()
    code = re.sub(r"```$", "", code).strip()
    return code

# --- Convert to PNG ---
def get_mermaid_image(mermaid_code: str) -> bytes:
    resp = requests.post("https://kroki.io/mermaid/png", data=mermaid_code.encode("utf-8"))
    if resp.status_code == 200:
        return resp.content
    raise RuntimeError(f"Kroki failed with status code {resp.status_code}")

# --- Session init ---
if "mermaid_code" not in st.session_state:
    st.session_state["mermaid_code"] = None
if "description" not in st.session_state:
    st.session_state["description"] = ""

# --- Main input ---
description = st.text_area(
    "What would you like to visualize or elaborate on?",
    value=st.session_state["description"],
    placeholder="e.g. User logs in → system verifies → show dashboard or error",
    height=200
)

# --- Run button ---
if st.button("Run"):
    with st.spinner("Calling Claude 3.5..."):
        try:
            raw_output = call_claude(description, mode)
            st.session_state["description"] = description

            if mode == "Elaborate Description":
                st.subheader("Elaborated Logic")
                st.write(raw_output)

            else:
                code = sanitize_mermaid(raw_output)
                st.session_state["mermaid_code"] = code

        except Exception as e:
            st.error("Something went wrong. Please try again.")

# --- Diagram output ---
code = st.session_state["mermaid_code"]
if code and mode == "Generate Diagram":
    st.subheader("Mermaid Code")
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

    st.download_button("Download .mmd file", data=code, file_name="diagram.mmd", mime="text/plain")

    try:
        img_data = get_mermaid_image(code)
        st.download_button("Download PNG", data=img_data, file_name="diagram.png", mime="image/png")
    except Exception as e:
        st.error(f"Failed to generate PNG: {e}")

    encoded = base64.b64encode(code.encode()).decode()
    live_url = f"https://mermaid.live/edit#pako={encoded}"
    st.markdown(f"[Open in Mermaid Live Editor →]({live_url})", unsafe_allow_html=True)
