"""
Llama Pipeline Service
Bridges backend evaluation flow with external Colab FastAPI Llama pipeline.
"""
import json
import socket
import time
from typing import Dict, List, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

from config import Config


class LlamaServiceError(Exception):
    """Raised when Colab API call fails — carries a human-readable reason."""
    pass


class LlamaService:
    """Client for external Llama evaluator API"""

    def __init__(self):
        self.base_url = (Config.LLAMA_API_BASE_URL or '').strip().rstrip('/')
        self.timeout          = Config.LLAMA_TIMEOUT_SECONDS
        self.evaluate_timeout = int(getattr(Config, 'LLAMA_EVALUATE_TIMEOUT_SECONDS', max(self.timeout, 300)))
        self.generate_timeout = int(getattr(Config, 'LLAMA_GENERATE_TIMEOUT_SECONDS', max(self.timeout, 900)))
        self.batch_timeout    = int(getattr(Config, 'LLAMA_BATCH_TIMEOUT_SECONDS',    max(self.timeout, 600)))
        self.retry_count      = int(getattr(Config, 'LLAMA_RETRY_COUNT', 1))

    def is_available(self) -> bool:
        return bool(self.base_url)

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict] = None,
        timeout_override: Optional[int] = None,
        silent_status_codes: Optional[List[int]] = None,
        raise_on_error: bool = False        # ← new flag used by batch_evaluate
    ) -> Optional[Dict]:
        """
        Make an HTTP request to the Colab API.

        raise_on_error=True  → raises LlamaServiceError instead of returning None,
                               so the caller can tell WHY it failed.
        raise_on_error=False → original behaviour (returns None on any error).
        """
        if not self.is_available():
            if raise_on_error:
                raise LlamaServiceError(
                    'Llama API base URL is not configured. '
                    'Set LLAMA_API_BASE_URL in backend/.env.'
                )
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

        timeout_value = int(timeout_override) if timeout_override else self.timeout
        retries = max(0, int(self.retry_count))

        last_error = None
        for attempt in range(retries + 1):
            is_last_attempt = attempt >= retries
            try:
                with urllib_request.urlopen(req, timeout=timeout_value) as response:
                    body = response.read().decode('utf-8')
                    if not body:
                        return {}
                    try:
                        return json.loads(body)
                    except json.JSONDecodeError:
                        print(f"[llama_service] Non-JSON response on {path}: {body[:300]}")
                        return {'raw_response': body}

            except urllib_error.HTTPError as exc:
                if silent_status_codes and exc.code in silent_status_codes:
                    return None
                try:
                    err_body = exc.read().decode('utf-8')
                except Exception:
                    err_body = ''
                msg = (
                    f"Colab returned HTTP {exc.code} on {path}. "
                    + (f"Detail: {err_body[:200]}" if err_body else '')
                )
                print(f"[llama_service] {msg}")
                last_error = LlamaServiceError(msg)
                if is_last_attempt:
                    if raise_on_error:
                        raise last_error
                    return None

            except socket.timeout:
                msg = (
                    f"Colab request timed out on {path} after {timeout_value}s "
                    f"(attempt {attempt + 1}/{retries + 1}). "
                    "Is the Colab notebook still running?"
                )
                print(f"[llama_service] {msg}")
                last_error = LlamaServiceError(msg)
                if is_last_attempt:
                    if raise_on_error:
                        raise last_error
                    return None
                time.sleep(min(1.5 * (attempt + 1), 3.0))

            except Exception as exc:
                msg = (
                    f"Colab request failed on {path}: {exc}. "
                    "Check LLAMA_API_BASE_URL and that the ngrok tunnel is active."
                )
                print(f"[llama_service] {msg}")
                last_error = LlamaServiceError(msg)
                if is_last_attempt:
                    if raise_on_error:
                        raise last_error
                    return None
                time.sleep(min(1.5 * (attempt + 1), 3.0))

        return None

    # ── Public methods ─────────────────────────────────────────────────────────

    def health(self) -> Optional[Dict]:
        return self._request('GET', '/health')

    def generate_answer(self, question: str, marks: int = 5) -> Optional[Dict]:
        return self._request(
            'POST', '/generate-answer',
            {'question': question, 'marks': marks},
            timeout_override=self.generate_timeout
        )

    def evaluate_answer(
        self,
        question: str,
        student_answer: str,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> Optional[Dict]:
        return self._request(
            'POST', '/evaluate',
            {
                'question': question,
                'student_answer': student_answer,
                'semantic_weight': semantic_weight,
                'keyword_weight': keyword_weight
            },
            timeout_override=self.evaluate_timeout
        )

    def batch_evaluate(
        self,
        question: str,
        answers: Dict[str, str],
        reference_answer: Optional[str] = None
    ) -> Dict:
        """
        Call /batch-evaluate on Colab.

        Unlike other methods this raises LlamaServiceError instead of
        returning None so workflow_routes can show a precise error message
        rather than the generic 'endpoint unavailable' fallback.

        Returns the full response dict (never None).
        """
        payload: Dict = {'question': question, 'answers': answers}
        if reference_answer:
            payload['reference_answer'] = reference_answer

        # raise_on_error=True means _request raises LlamaServiceError
        # instead of swallowing the error and returning None
        result = self._request(
            'POST', '/batch-evaluate',
            payload,
            timeout_override=self.batch_timeout,
            raise_on_error=True          # ← key change
        )

        # Defensive: _request shouldn't return None with raise_on_error=True,
        # but guard anyway
        if result is None:
            raise LlamaServiceError(
                'Colab /batch-evaluate returned an empty response. '
                'Check that the Colab notebook is running and '
                '/batch-evaluate is registered.'
            )
        return result

    # ── Assignment workflow pass-through methods (unchanged) ──────────────────

    def create_assignment(self, teacher_id: str, title: str, questions: List[Dict]) -> Optional[Dict]:
        return self._request('POST', '/assignments/create',
                             {'teacher_id': teacher_id, 'title': title, 'questions': questions})

    def list_teacher_assignments(self, teacher_id: str) -> Optional[Dict]:
        return self._request('GET', f'/assignments/teacher/{teacher_id}')

    def get_assignment_submissions(self, assignment_id: str) -> Optional[Dict]:
        return self._request('GET', f'/assignments/{assignment_id}/submissions')

    def get_student_submission(self, assignment_id: str, student_id: str) -> Optional[Dict]:
        return self._request('GET', f'/assignments/{assignment_id}/submissions/{student_id}')

    def evaluate_student_submission(self, assignment_id: str, student_id: str) -> Optional[Dict]:
        return self._request('POST', f'/assignments/{assignment_id}/evaluate-student',
                             {'student_id': student_id})

    def evaluate_all_submissions(self, assignment_id: str) -> Optional[Dict]:
        return self._request('POST', f'/assignments/{assignment_id}/evaluate-all', {})

    def list_student_assignments(self) -> Optional[Dict]:
        return self._request('GET', '/assignments/student/list')

    def get_assignment_questions(self, assignment_id: str) -> Optional[Dict]:
        return self._request('GET', f'/assignments/{assignment_id}/questions')

    def submit_assignment_answers(
        self,
        assignment_id: str,
        student_id: str,
        student_name: str,
        answers: List[str]
    ) -> Optional[Dict]:
        return self._request('POST', f'/assignments/{assignment_id}/submit',
                             {'student_id': student_id, 'student_name': student_name, 'answers': answers})

    def get_submission_status(self, assignment_id: str, student_id: str) -> Optional[Dict]:
        return self._request('GET', f'/assignments/{assignment_id}/submission-status/{student_id}')


llama_service = LlamaService()