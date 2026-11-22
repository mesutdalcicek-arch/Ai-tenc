import ast
import traceback
import httpx

class AIHealer:
    def __init__(self, api_url="http://127.0.0.1:11434/api/generate"):
        # Ollama local endpoint (veya OpenAI/Anthropic API'ye çevrilebilir)
        self.api_url = api_url
        self.model = "codellama" # veya "deepseek-coder", "llama3"

    def _check_syntax(self, code: str):
        """AST ile syntax hatası var mı kontrol et."""
        try:
            ast.parse(code)
            return None
        except SyntaxError as e:
            return str(e)

    async def fix(self, code: str):
        """Kodu analiz et, hatalıysa LLM ile düzelt."""
        error = self._check_syntax(code)
        if not error:
            return code, 0

        prompt = f"""
        You are an expert Python debugger.
        Fix the following Python code.
        Error: {error}
        
        Code:
        {code}
        
        Return ONLY the fixed Python code. No markdown, no explanations.
        """

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.api_url,
                json={"model": self.model, "prompt": prompt, "stream": False}
            )
            
        if response.status_code == 200:
            fixed_code = response.json().get("response", "").strip()
            # Markdown bloklarını temizle (eğer LLM eklediyse)
            if fixed_code.startswith("```python"):
                fixed_code = fixed_code[9:]
            if fixed_code.endswith("```"):
                fixed_code = fixed_code[:-3]
            return fixed_code.strip(), 1
            
        return code, 0
