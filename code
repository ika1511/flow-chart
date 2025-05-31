import streamlit as st
import boto3
import json
import uuid

AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
AWS_SESSION_TOKEN = st.secrets["AWS_SESSION_TOKEN"]
REGION = "us-west-2"
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

def call_claude(logic_text):
    client = boto3.client(
        "bedrock-runtime",
        region_name=REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN,
    )

    prompt = f"""
You are a helpful assistant. Convert the following logic into a Mermaid flowchart.

Logic:
{logic_text}

Only return the Mermaid code block inside ```mermaid ... ``` — no explanation or anything else.
"""

    payload = {
        "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
        "max_tokens_to_sample": 1024,
        "temperature": 0.3,
        "top_k": 250,
        "top_p": 1,
        "stop_sequences": ["\n\nHuman:"]
    }

    response = client.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(payload),
        contentType="application/json",
        accept="application/json",
    )

    result = json.loads(response["body"].read())
    return result["completion"]

st.set_page_config(layout="wide")
st.title("Claude 3.5 → Mermaid Flowchart Generator")

logic_text = st.text_area("Enter your logical explanation:", height=200)

if st.button("Generate Mermaid Diagram"):
    if logic_text.strip():
        with st.spinner("Calling Claude 3.5..."):
            raw_output = call_claude(logic_text)

            mermaid_code = raw_output.strip().replace("```mermaid", "").replace("```", "")

        st.markdown("### 🔍 Mermaid Code")
        st.code(mermaid_code, language="mermaid")

        st.markdown("### 🖼️ Rendered Diagram")
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
    else:
        st.warning("Please enter a valid logical description.")
