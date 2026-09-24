import os
import re
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor

STARTER_MESSAGES = [
    "aur bhai log kya haal chaal?",
    "kya chal raha hai sabka?",
    "koi online hai kya abhi?",
    "aaj ka din kaisa raha sabka?",
    "kisine koi nayi movie ya web series dekhi kya?",
    "kya scene hai aaj ka guys?",
    "bhai bohot bore ho raha hu koi achi game batao",
    "sab itne shaant kyu ho group me aaj haha",
    "yo what's everyone up to right now?",
    "chai peene ka time ho gaya dosto",
    "kya plan hai weekend ka sabka?",
    "aaj mausam kaisa hai waha?",
    "bhai koi badhiya gana recommend karo na",
    "kya chal raha hai idhar koi batao",
    "hello guys sab badhiya?",
    "aaj ka match kis kis ne dekha?",
    "bhai koi active hai chat me?",
    "kya haal hai dosto sab theek?",
    "aaj bohot thakan ho gayi yar",
    "kuch naya batao yaar sab log",
    "shaam ka kya plan hai dosto?",
    "koi achi comedy video suggest karo",
    "kya baat hai aaj group me sannata kyu hai?",
    "bhai log khana peena ho gaya sabka?"
]

FALLBACK_REPLIES = [
    "bas bhai sab badhiya, tu bata kya haal hai?",
    "kuch khaas nahi yaar, bas chal raha hai",
    "sahi baat hai bhai, bilkul agree",
    "haha haan yaar sahi me",
    "are badhiya! aur batao kya naya hai",
    "mast bhai, sab changa si",
    "haan yaar ye to sach me hai",
    "tu bata bro tera kya chal raha?",
    "kya baat hai bro, badhiya laga sunke",
    "sahi me bhai relate kar gaya",
    "chal badhiya hai fir toh",
    "haan bilkul, 100% agreed",
    "aur batao sab theek thaak?",
    "sahi scene hai bhai fir to",
    "are wah bhai ye toh mast hai",
    "sahi bol rahe ho bilkul",
    "haha ye bhi theek hai bro",
    "chal theek hai milte hai fir",
    "ha yar main bhi wahi soch raha tha"
]

FORBIDDEN_WORDS = [
    "naturally", "responding", "assistant", "telegram", "language model", 
    "ai", "babe", "mind you", "bot", "user:", "reply:"
]

def clean_response(text: str) -> str:
    if not text:
        return ""
    text = text.strip()

    # Remove robotic prefixes
    prefixes = [
        r"^naturally responding:?",
        r"^response:?",
        r"^reply:?",
        r"^assistant:?",
        r"^member:?",
        r"^friend:?",
        r"^user:?",
        r"^bot:?",
        r"^me:?",
        r"^chat:?"
    ]
    for p in prefixes:
        text = re.sub(p, "", text, flags=re.IGNORECASE).strip()

    # Remove surrounding quotes
    text = text.strip('"\'`')

    # Remove duplicate punctuation / symbols / emoji chains
    text = re.sub(r'([^\w\s])\1{2,}', r'\1', text)

    # Max 1-2 lines
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return ""
    return " ".join(lines[:2]).strip()


class LocalLLM:
    def __init__(self):
        self.model = None
        self.repo_id = "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
        self.filename = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
        self.model_path = os.path.join(os.getcwd(), "models", self.filename)
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.is_downloading = False

    async def initialize(self):
        if self.model is not None:
            return True

        if not os.path.exists(self.model_path):
            self.is_downloading = True
            try:
                from huggingface_hub import hf_hub_download
                print(f"Downloading {self.filename}... This may take a while.")
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                downloaded_path = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: hf_hub_download(repo_id=self.repo_id, filename=self.filename, local_dir=os.path.dirname(self.model_path))
                )
                print(f"Downloaded model to {downloaded_path}")
            except Exception as e:
                print(f"Error downloading model: {e}")
                self.is_downloading = False
                return False
            self.is_downloading = False

        try:
            from llama_cpp import Llama
            self.model = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: Llama(
                    model_path=self.model_path,
                    n_ctx=2048,
                    n_threads=4,
                    verbose=False
                )
            )
            print("Local LLM Initialized successfully.")
            return True
        except Exception as e:
            print(f"Failed to load local LLM: {e}")
            return False

    async def generate(self, prompt, max_tokens=50):
        if not self.model:
            success = await self.initialize()
            if not success:
                return ""

        def run_inference():
            output = self.model(
                prompt,
                max_tokens=max_tokens,
                stop=["<|user|>", "<|assistant|>", "\n\n", "Member:", "User:", "Assistant:", "\n"],
                echo=False,
                temperature=0.85,
                repeat_penalty=1.35,
                top_p=0.9
            )
            return output["choices"][0]["text"].strip()

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, run_inference
            )
            return clean_response(result)
        except Exception as e:
            print(f"LLM generation error: {e}")
            return ""

    async def generate_initial_message(self):
        # Always pick from realistic human starters pool to avoid weird bot intros
        return random.choice(STARTER_MESSAGES)

    async def generate_reply(self, last_message, recent_messages=None):
        if not last_message:
            return random.choice(FALLBACK_REPLIES)

        prompt = (
            "<|system|>\n"
            "You are a real Indian friend casually chatting in a Telegram group with friends in Hinglish. "
            "Reply naturally to the friend's message. Max 1 short sentence (under 10 words). "
            "Never repeat what the friend said. Never mention bots, ai, or models.\n\n"
            "Examples:\n"
            "Friend: aur bhai kya chal raha hai?\n"
            "Reply: bas badhiya bhai, tu bata kya scene hai?\n"
            "Friend: shaam ko ghumne chalte hai\n"
            "Reply: ha done, kahan milna hai bata?\n"
            "Friend: apne regular spot par aaja\n"
            "Reply: theek hai 10 min me pauhachta hu\n"
            "Friend: bore ho raha hu bohot\n"
            "Reply: chal koi game khelte hai fir\n"
            "<|user|>\n"
            f"Friend: {last_message}\n"
            "Reply:\n"
            "<|assistant|>\n"
        )
        response = await self.generate(prompt, max_tokens=25)
        
        # Guard against empty, repetitive, or hallucinated responses
        lower_resp = response.lower() if response else ""
        if (not response 
            or len(response) < 4 
            or lower_resp == last_message.lower()
            or any(w in lower_resp for w in FORBIDDEN_WORDS)):
            return random.choice(FALLBACK_REPLIES)

        # Check against recent messages to prevent repeating
        if recent_messages and any(lower_resp == m.lower() for m in recent_messages):
            available = [r for r in FALLBACK_REPLIES if r.lower() not in [m.lower() for m in recent_messages]]
            return random.choice(available) if available else random.choice(FALLBACK_REPLIES)

        return response

llm = LocalLLM()
