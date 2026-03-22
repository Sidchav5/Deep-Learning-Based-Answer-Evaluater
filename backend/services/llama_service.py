"""
Llama Pipeline Service
Bridges backend evaluation flow with external Colab/Kaggle FastAPI Llama pipeline.
"""
import json
from typing import Dict, Optional
from urllib import request as urllib_request
from urllib import error as urllib_error

from config import Config


class LlamaService:
    """Client for external Llama evaluator API"""

    def __init__(self):
        self.base_url = (Config.LLAMA_API_BASE_URL or '').strip().rstrip('/')
        self.timeout = Config.LLAMA_TIMEOUT_SECONDS

    def is_available(self) -> bool:
        """Whether service is configured"""
        return bool(self.base_url)

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(self, method: str, path: str, payload: Optional[Dict] = None) -> Optional[Dict]:
        if not self.is_available():
            return None

        data = None
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'ngrok-skip-browser-warning': 'true'
        }

        if payload is not None:
            data = json.dumps(payload).encode('utf-8')

        req = urllib_request.Request(
            url=self._url(path),
            data=data,
            headers=headers,
            method=method
        )

        try:
            with urllib_request.urlopen(req, timeout=self.timeout) as response:
                response_body = response.read().decode('utf-8')
                if not response_body:
                    return {}

                try:
                    return json.loads(response_body)
                except json.JSONDecodeError:
                    print(f"Llama API returned non-JSON response on {path}: {response_body[:300]}")
                    return {'raw_response': response_body}
        except urllib_error.HTTPError as exc:
            try:
                body = exc.read().decode('utf-8')
            except Exception:
                body = ''
            print(f"Llama API HTTP error {exc.code} on {path}: {body}")
            return None
        except Exception as exc:
            print(f"Llama API request failed on {path}: {exc}")
            return None

    def health(self) -> Optional[Dict]:
        """Health check for external llama service"""
        return self._request('GET', '/health')

    def generate_answer(self, question: str, marks: int = 5) -> Optional[Dict]:
        """Generate reference answer from llama API"""
        payload = {
            'question': question,
            'marks': marks
        }
        return self._request('POST', '/generate-answer', payload)

    def evaluate_answer(
        self,
        question: str,
        student_answer: str,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> Optional[Dict]:
        """Evaluate a single student answer via external API"""
        payload = {
            'question': question,
            'student_answer': student_answer,
            'semantic_weight': semantic_weight,
            'keyword_weight': keyword_weight
        }
        return self._request('POST', '/evaluate', payload)

    def batch_evaluate(self, question: str, answers: Dict[str, str]) -> Optional[Dict]:
        """Batch evaluation endpoint wrapper"""
        payload = {
            'question': question,
            'answers': answers
        }
        return self._request('POST', '/batch-evaluate', payload)


llama_service = LlamaService()
