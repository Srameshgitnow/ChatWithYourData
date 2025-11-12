# Embeddings & Models (stable new packages)
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_openai.chat_models import ChatOpenAI

# Text splitters
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter

# Vectorstore and loaders (community)
from langchain_community.vectorstores import DocArrayInMemorySearch
from langchain_community.document_loaders import TextLoader, PyPDFLoader

import warnings
warnings.filterwarnings("ignore", message="`pydantic.error_wrappers:ValidationError`")

# Chains and Memory — try multiple paths for compatibility
import openai

from dotenv import load_dotenv
import getpass
import os
load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")

def load_db(file, chain_type, k):
    """
    Load PDF, split, embed, create DocArrayInMemorySearch and return a qa callable.
    The returned callable mimics the RetrievalQA/ConversationalRetrievalChain output:
      result = qa({"question": "...", "chat_history": [...]})
    """
    # 1) load documents
    loader = PyPDFLoader(file)
    documents = loader.load()
    # 2) split documents
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    docs = text_splitter.split_documents(documents)
    # 3) define embedding
    embeddings = OpenAIEmbeddings()
    # 4) create vector database from data
    db = DocArrayInMemorySearch.from_documents(docs, embeddings)
    # 5) retriever (we'll use similarity_search directly)
    # retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": k})

    # Build and return a callable that performs retrieval + OpenAI call
    def qa_callable(inputs):
        """
        inputs: dict with keys "question" (str) and optional "chat_history" (list)
        returns: dict with 'answer', 'generated_question', 'source_documents'
        """
        question = inputs.get("question", "")
        chat_history = inputs.get("chat_history", [])

        # Retrieve top-k docs (similarity_search available on the vectorstore)
        try:
            retrieved_docs = db.similarity_search(question, k=k)
        except Exception:
            # fallback to retriever if needed
            retr = getattr(db, "as_retriever", None)
            if retr:
                retrieved_docs = retr().get_relevant_documents(question)[:k]
            else:
                retrieved_docs = []

        # Prepare context: join short snippets from retrieved docs
        context_snippets = []
        for i, d in enumerate(retrieved_docs):
            text = getattr(d, "page_content", str(d))
            meta = getattr(d, "metadata", {})
            # keep snippet reasonably short
            snippet = (text[:1200] + "...") if len(text) > 1200 else text
            ctx = f"Source {i+1} ({meta.get('source', meta.get('filename', f'doc_{i+1}'))}):\n{snippet}"
            context_snippets.append(ctx)

        context = "\n\n".join(context_snippets) if context_snippets else "No relevant context found."

        # Craft a compact prompt for the Chat model
        system_prompt = (
            "You are a helpful assistant. Answer the question using only the provided context. "
            "If the answer is not present, say you don't know. Keep answers concise (max 3 sentences)."
        )
        user_prompt = f"CONTEXT:\n{context}\n\nQuestion: {question}\n\nHelpful Answer:"

        # Call OpenAI's ChatCompletion API directly (works reliably)
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",   # you can change to llm_name var if desired
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            max_tokens=300,
        )

        answer = resp["choices"][0]["message"]["content"].strip()

        # The generated_question field: here we simply echo back a cleaned question or short paraphrase
        generated_question = question  # you can create a paraphrase if you want

        # Return a structure similar to RetrievalQA/ConversationalRetrievalChain result
        return {
            "answer": answer,
            "generated_question": generated_question,
            "source_documents": retrieved_docs,
            "raw_response": resp
        }

    return qa_callable



import panel as pn
import param
pn.extension() 

class cbfs(param.Parameterized):
    chat_history = param.List([])
    answer = param.String("")
    db_query  = param.String("")
    db_response = param.List([])
    
    def __init__(self,  **params):
        super(cbfs, self).__init__( **params)
        self.panels = []
        self.loaded_file = "docs/learning-and-teaching-prompt-templates.pdf"
        self.qa = load_db(self.loaded_file,"stuff", 4)
    
    def call_load_db(self, count):
        if count == 0 or file_input.value is None:  # init or no file specified :
            return pn.pane.Markdown(f"Loaded File: {self.loaded_file}")
        else:
            file_input.save("temp.pdf")  # local copy
            self.loaded_file = file_input.filename
            button_load.button_style="outline"
            self.qa = load_db("temp.pdf", "stuff", 4)
            button_load.button_style="solid"
        self.clr_history()
        return pn.pane.Markdown(f"Loaded File: {self.loaded_file}")

    def convchain(self, query):
        if not query:
            return pn.WidgetBox(pn.Row('User:', pn.pane.Markdown("", width=600)), scroll=True)
        result = self.qa({"question": query, "chat_history": self.chat_history})
        self.chat_history.extend([(query, result["answer"])])
        self.db_query = result["generated_question"]
        self.db_response = result["source_documents"]
        self.answer = result['answer'] 
        self.panels.extend([
            pn.Row('User:', pn.pane.Markdown(query, width=600)),
            pn.Row('ChatBot:', pn.pane.Markdown(self.answer, width=600, style={'background-color': '#F6F6F6'}))
        ])
        inp.value = ''  #clears loading indicator when cleared
        return pn.WidgetBox(*self.panels,scroll=True)

    @param.depends('db_query ', )
    def get_lquest(self):
        if not self.db_query :
            return pn.Column(
                pn.Row(pn.pane.Markdown(f"Last question to DB:", styles={'background-color': '#F6F6F6'})),
                pn.Row(pn.pane.Str("no DB accesses so far"))
            )
        return pn.Column(
            pn.Row(pn.pane.Markdown(f"DB query:", styles={'background-color': '#F6F6F6'})),
            pn.pane.Str(self.db_query )
        )

    @param.depends('db_response', )
    def get_sources(self):
        if not self.db_response:
            return 
        rlist=[pn.Row(pn.pane.Markdown(f"Result of DB lookup:", styles={'background-color': '#F6F6F6'}))]
        for doc in self.db_response:
            rlist.append(pn.Row(pn.pane.Str(doc)))
        return pn.WidgetBox(*rlist, width=600, scroll=True)

    @param.depends('convchain', 'clr_history') 
    def get_chats(self):
        if not self.chat_history:
            return pn.WidgetBox(pn.Row(pn.pane.Str("No History Yet")), width=600, scroll=True)
        rlist=[pn.Row(pn.pane.Markdown(f"Current Chat History variable", styles={'background-color': '#F6F6F6'}))]
        for exchange in self.chat_history:
            rlist.append(pn.Row(pn.pane.Str(exchange)))
        return pn.WidgetBox(*rlist, width=600, scroll=True)

    def clr_history(self,count=0):
        self.chat_history = []
        return 


cb = cbfs()

file_input = pn.widgets.FileInput(accept='.pdf')
button_load = pn.widgets.Button(name="Load DB", button_type='primary')
button_clearhistory = pn.widgets.Button(name="Clear History", button_type='warning')
button_clearhistory.on_click(cb.clr_history)
inp = pn.widgets.TextInput( placeholder='Enter text here…')

bound_button_load = pn.bind(cb.call_load_db, button_load.param.clicks)
conversation = pn.bind(cb.convchain, inp) 

jpg_pane = pn.pane.Image( './img/convchain.jpg')

tab1 = pn.Column(
    pn.Row(inp),
    pn.layout.Divider(),
    pn.panel(conversation,  loading_indicator=True, height=300),
    pn.layout.Divider(),
)
tab2= pn.Column(
    pn.panel(cb.get_lquest),
    pn.layout.Divider(),
    pn.panel(cb.get_sources ),
)
tab3= pn.Column(
    pn.panel(cb.get_chats),
    pn.layout.Divider(),
)
tab4=pn.Column(
    pn.Row( file_input, button_load, bound_button_load),
    pn.Row( button_clearhistory, pn.pane.Markdown("Clears chat history. Can use to start a new topic" )),
    pn.layout.Divider(),
    pn.Row(jpg_pane.clone(width=400))
)
dashboard = pn.Column(
    pn.Row(pn.pane.Markdown('# ChatWithYourData_Bot')),
    pn.Tabs(('Conversation', tab1), ('Database', tab2), ('Chat History', tab3),('Configure', tab4))
)
dashboard

# --- Run Panel app if executed directly ---
if __name__ == "__main__":
    print("🚀 Launching ChatWithYourData_Bot Panel App ...")
    try:
        pn.serve(dashboard, title="ChatWithYourData_Bot", show=True, port=5006)
    except Exception as e:
        print("⚠️ Could not start Panel server automatically.")
        print("Reason:", e)
        print("👉 You can still run it manually with:")
        print("   panel serve src/chat_with_data.py --show")