# backend/services/__init__.py
from .evaluation_service import evaluation_service, EvaluationService
from .rag_service import rag_service, RAGService

__all__ = ['evaluation_service', 'EvaluationService', 'rag_service', 'RAGService']
