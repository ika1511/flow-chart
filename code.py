import streamlit as st
import boto3
import json
import uuid

# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("Claude 3.5 → Mermaid Flowchart Generator")

# --- AWS Credentials from Streamlit Secrets ---
AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
AWS_SESSION_TOKEN = st.secrets["AWS_SESSION_TOKEN"]
REGION = "us-west-2"
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# --- Claude 3.5 via Bedrock ---
def call_claude(logic_text):
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
        "temperature": 0.3,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Convert the following process logic into a Mermaid flowchart. "
                            "Only return the Mermaid diagram inside a ```mermaid``` code block.\n\n"
                            f"{logic_text}"
                        )
                    }
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

# --- UI Logic ---
logic_text = st.text_area("Enter a logical description of a process (as a string):", height=200)

if st.button("Generate Mermaid Diagram"):
    if logic_text.strip():
        with st.spinner("Calling Claude 3.5 via AWS Bedrock..."):
            try:
                raw_mermaid = call_claude(logic_text)
                # Strip code block wrapper if present
                mermaid_code = raw_mermaid.replace("```mermaid", "").replace("```", "").strip()

                st.subheader("📋 Mermaid Code")
                st.code(mermaid_code, language="mermaid")

                # Render Mermaid live using HTML/JS injection
                st.subheader("🖼️ Rendered Diagram")
                unique_id = str(uuid.uuid4()).replace("-", "")
                st.components.v1.html(f"""
                    <div id="mermaid-{unique_id}">
                      <pre class="mermaid">
{mermaid_code}
                      </pre>
                    </div>
                    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
                    <script>mermaid.initialize({{startOnLoad:true}});</script>
                """, height=500, scrolling=True)

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    else:
        st.warning("Please enter some process logic.")
