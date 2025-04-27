import openai
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate
from openai import OpenAI
from ..config import OPENAI_MODEL

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize LangChain components
chat = ChatOpenAI(
    model="gpt-4o-mini", temperature=0.7, api_key=os.getenv("OPENAI_API_KEY")
)

# Create a conversation template
template = """The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context.

Current conversation:
{history}
Human: {input}
AI:"""

prompt = PromptTemplate(input_variables=["history", "input"], template=template)

# Initialize conversation memory
memory = ConversationBufferMemory(return_messages=True, memory_key="history")


def get_conversation_chain():
    """Get a configured conversation chain for chat interactions."""
    return ConversationChain(llm=chat, memory=memory, prompt=prompt, verbose=True)


def get_openai_client(model: str | None = None):
    # Check if it's a Grok model
    if model and model.startswith("grok"):
        return OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")

    # Default to OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_chat_model():
    """Get the LangChain chat model instance."""
    return chat


def get_memory():
    """Get the conversation memory instance."""
    return memory


def get_prompt_template():
    """Get the prompt template for conversations."""
    return prompt
