"""
Service client for external Llama-based evaluation pipeline.
"""
from typing import Dict, Optional

import requests

from config import Config


class LlamaApiError(Exception):
    """Raised when the external Llama API call fails."""


class LlamaService:
    """HTTP client for external Llama API."""

    def __init__(self):
        self.base_url = (Config.LLAMA_API_BASE_URL or '').strip().rstrip('/')
        self.timeout = int(Config.LLAMA_TIMEOUT_SECONDS)
        self.health_path = (Config.LLAMA_HEALTH_PATH or '/health').strip() or '/health'
        self.generate_path = (Config.LLAMA_GENERATE_PATH or '/generate-answer').strip() or '/generate-answer'
        self.evaluate_path = (Config.LLAMA_EVALUATE_PATH or '/evaluate').strip() or '/evaluate'
        self.batch_evaluate_path = (Config.LLAMA_BATCH_EVALUATE_PATH or '/batch-evaluate').strip() or '/batch-evaluate'
        self.prefer_batch = bool(Config.LLAMA_PREFER_BATCH_EVALUATE)

    def is_available(self) -> bool:
        return bool(self.base_url)

    @staticmethod
    def _candidate_paths(path: str):
        normalized = path if path.startswith('/') else f'/{path}'
        candidates = [normalized]
        if not normalized.startswith('/api/'):
            candidates.append(f'/api{normalized}')
        return candidates

    def _post(self, path: str, payload: Dict) -> Optional[Dict]:
        if not self.is_available():
            return None

        tried_paths = []
        last_error = None

        for candidate_path in self._candidate_paths(path):
            tried_paths.append(candidate_path)
            url = f"{self.base_url}{candidate_path}"
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )

                # Try alternate route style if this endpoint is not found.
                if response.status_code == 404:
                    last_error = LlamaApiError(
                        f"Llama API HTTP 404 at {candidate_path}. Body: {((response.text or '').strip().replace('\\n', ' '))[:220]}"
                    )
                    continue

                response.raise_for_status()
                try:
                    return response.json()
                except ValueError:
                    body_preview = (response.text or '').strip().replace('\n', ' ')[:220]
                    raise LlamaApiError(
                        f"Llama API returned non-JSON response at {candidate_path} (status {response.status_code}). "
                        f"Body: {body_preview}"
                    )
            except requests.exceptions.Timeout:
                raise LlamaApiError(f"Llama API timeout after {self.timeout}s at {candidate_path}")
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else 'unknown'
                ngrok_code = ''
                if e.response is not None:
                    ngrok_code = str(e.response.headers.get('Ngrok-Error-Code', '')).strip()
                body_preview = ((e.response.text if e.response is not None else '') or '').strip().replace('\n', ' ')[:220]
                if ngrok_code == 'ERR_NGROK_3200':
                    raise LlamaApiError(
                        'Llama tunnel is offline (ERR_NGROK_3200). Restart your ngrok/Colab service and update LLAMA_API_BASE_URL.'
                    )
                raise LlamaApiError(
                    f"Llama API HTTP {status} at {candidate_path}. Body: {body_preview}"
                )
            except requests.exceptions.RequestException as e:
                raise LlamaApiError(f"Llama API network error at {candidate_path}: {str(e)}")

        if last_error:
            raise LlamaApiError(
                f"Llama API route not found. Tried paths: {', '.join(tried_paths)}"
            )
        return None

    def evaluate_batch(self, question: str, answers: Dict[str, str], reference: Optional[str] = None) -> Optional[Dict]:
        """Batch evaluate one question for multiple student answers."""
        payload = {
            'question': question,
            'answers': answers or {}
        }
        if reference:
            payload['reference_answer'] = reference

        try:
            return self._post(self.batch_evaluate_path, payload)
        except LlamaApiError as e:
            error_text = str(e).lower()
            if 'route not found' in error_text or 'http 404' in error_text:
                return self._post('/batch-evaluate', payload)
            raise

    def evaluate_answer(
        self,
        question: str,
        reference: Optional[str],
        student: str,
        marks: float,
        use_generated_reference: bool = False
    ) -> Optional[Dict]:
        """Evaluate one answer through external Llama API."""

        # Preferred path for v2 API: /batch-evaluate with a single answer entry.
        if self.prefer_batch:
            batch_reference = None if use_generated_reference else reference
            batch_result = self.evaluate_batch(
                question=question,
                answers={'single': student},
                reference=batch_reference
            )
            if isinstance(batch_result, dict):
                results = batch_result.get('results', {})
                if isinstance(results, dict):
                    single_result = results.get('single')
                    if isinstance(single_result, dict):
                        # Normalize to the same shape consumed by evaluation_service.
                        normalized = dict(single_result)
                        normalized.setdefault('reference_answer', batch_result.get('reference_answer', reference))
                        return normalized

        # Direct single-answer endpoint compatibility.
        evaluate_payload = {
            'question': question,
            'student_answer': student,
            'semantic_weight': 0.7,
            'keyword_weight': 0.3
        }

        if not use_generated_reference and reference:
            # Extra compatibility fields used by some implementations.
            evaluate_payload['reference_answer'] = reference
            evaluate_payload['marks'] = float(marks)

        legacy_payload = {
            'question': question,
            'reference_answer': reference or '',
            'student_answer': student,
            'marks': float(marks)
        }

        payload = {
            'question': question,
            'reference_answer': reference,
            'student_answer': student,
            'marks': float(marks)
        }
        try:
            return self._post(self.evaluate_path, evaluate_payload)
        except LlamaApiError as e:
            error_text = str(e).lower()
            if 'route not found' in error_text or 'http 404' in error_text:
                try:
                    return self._post('/evaluate', evaluate_payload)
                except LlamaApiError as e2:
                    error_text2 = str(e2).lower()
                    if 'route not found' in error_text2 or 'http 404' in error_text2:
                        return self._post('/evaluate-answer', legacy_payload)
                    raise
            raise

    def generate_answer(self, question: str, marks: float = 5) -> Optional[Dict]:
        """Generate a model/reference answer for a question."""
        payload = {
            'question': question,
            'marks': float(marks)
        }
        try:
            return self._post(self.generate_path, payload)
        except LlamaApiError as e:
            error_text = str(e).lower()
            if 'route not found' in error_text or 'http 404' in error_text:
                return self._post('/generate-answer', payload)
            raise

    def health(self) -> Dict:
        """Check external Llama service health."""
        if not self.is_available():
            return {'status': 'unconfigured'}

        tried_paths = []
        for candidate_path in self._candidate_paths(self.health_path):
            tried_paths.append(candidate_path)
            try:
                response = requests.get(f"{self.base_url}{candidate_path}", timeout=self.timeout)
                if response.status_code == 404:
                    continue
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict):
                    return data
                return {'status': 'ok'}
            except Exception:
                continue

        return {
            'status': 'error',
            'message': f"Health endpoint not found. Tried: {', '.join(tried_paths)}"
        }


llama_service = LlamaService()
