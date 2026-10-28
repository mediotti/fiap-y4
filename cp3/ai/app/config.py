import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    api_key: str = ""
    fast_model: str = "google/gemini-2.5-flash"
    deep_model: str = "anthropic/claude-sonnet-4.5"
    fallback_model: str = "openai/gpt-4.1-mini"
    context_window: int = 16384
    input_budget: int = 6000
    output_budget: int = 1000
    data_dir: Path = Path("data")

    def __post_init__(self):
        if self.input_budget < 3000 or not 128 <= self.output_budget <= 2000:
            raise ValueError("Orçamentos: entrada >= 3000; saída entre 128 e 2000.")
        if self.input_budget + self.output_budget + 512 > self.context_window:
            raise ValueError("Orçamentos excedem a janela de contexto (incluindo margem de 512).")

    @classmethod
    def from_env(cls):
        return cls(
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            fast_model=os.getenv("MODEL_FAST", cls.fast_model),
            deep_model=os.getenv("MODEL_DEEP", cls.deep_model),
            fallback_model=os.getenv("MODEL_FALLBACK", cls.fallback_model),
            context_window=int(os.getenv("MODEL_CONTEXT_WINDOW", "16384")),
            input_budget=int(os.getenv("INPUT_TOKEN_BUDGET", "6000")),
            output_budget=int(os.getenv("OUTPUT_TOKEN_BUDGET", "1000")),
            data_dir=Path(os.getenv("DATA_DIR", "data")),
        )
