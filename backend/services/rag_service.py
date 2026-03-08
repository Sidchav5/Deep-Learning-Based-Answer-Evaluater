# backend/services/rag_service.py
"""
RAG (Retrieval-Augmented Generation) Service
Handles document processing, vector storage, retrieval, and Groq API integration
"""
import os
import pickle
import numpy as np
from typing import List, Dict, Optional, Tuple
import faiss
from groq import Groq

from config import Config
from models import ml_models


class Document:
    """Represents a chunk of text with metadata"""
    def __init__(self, content: str, metadata: Dict = None):
        self.content = content
        self.metadata = metadata or {}
        self.embedding = None


class VectorStore:
    """FAISS-based vector store for document retrieval"""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.documents: List[Document] = []
        self.store_path = Config.VECTOR_STORE_PATH
    
    def add_documents(self, documents: List[Document]):
        """Add documents to the vector store"""
        if not documents:
            return
        
        # Generate embeddings for all documents
        embeddings = []
        for doc in documents:
            embedding = ml_models.get_embeddings(doc.content)
            doc.embedding = embedding
            embeddings.append(embedding)
        
        # Add to FAISS index
        embeddings_array = np.array(embeddings).astype('float32')
        self.index.add(embeddings_array)
        self.documents.extend(documents)
        
        print(f"✅ Added {len(documents)} documents to vector store")
    
    def search(self, query: str, top_k: int = 3, threshold: float = 0.3) -> List[Tuple[Document, float]]:
        """Search for similar documents"""
        if self.index.ntotal == 0:
            return []
        
        # Generate query embedding
        query_embedding = ml_models.get_embeddings(query).reshape(1, -1).astype('float32')
        
        # Search in FAISS
        distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
        
        # Filter by threshold and return results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.documents):
                # Convert L2 distance to similarity score (inverse)
                similarity = 1 / (1 + dist)
                if similarity >= threshold:
                    results.append((self.documents[idx], similarity))
        
        return results
    
    def save(self, name: str = "default"):
        """Save vector store to disk"""
        os.makedirs(self.store_path, exist_ok=True)
        
        # Save FAISS index
        index_path = os.path.join(self.store_path, f"{name}_index.faiss")
        faiss.write_index(self.index, index_path)
        
        # Save documents
        docs_path = os.path.join(self.store_path, f"{name}_docs.pkl")
        with open(docs_path, 'wb') as f:
            pickle.dump(self.documents, f)
        
        print(f"✅ Vector store saved: {name}")
    
    def load(self, name: str = "default") -> bool:
        """Load vector store from disk"""
        try:
            index_path = os.path.join(self.store_path, f"{name}_index.faiss")
            docs_path = os.path.join(self.store_path, f"{name}_docs.pkl")
            
            if not os.path.exists(index_path) or not os.path.exists(docs_path):
                return False
            
            # Load FAISS index
            self.index = faiss.read_index(index_path)
            
            # Load documents
            with open(docs_path, 'rb') as f:
                self.documents = pickle.load(f)
            
            print(f"✅ Vector store loaded: {name} ({len(self.documents)} documents)")
            return True
        except Exception as e:
            print(f"❌ Error loading vector store: {e}")
            return False
    
    def clear(self):
        """Clear the vector store"""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = []


class DocumentProcessor:
    """Process and chunk documents"""
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        if not text:
            return []
        
        words = text.split()
        chunks = []
        
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunk = ' '.join(chunk_words)
            chunks.append(chunk)
            i += chunk_size - overlap
        
        return chunks
    
    @staticmethod
    def process_document(text: str, metadata: Dict = None) -> List[Document]:
        """Process a document into chunks"""
        chunks = DocumentProcessor.chunk_text(
            text,
            chunk_size=Config.RAG_CHUNK_SIZE,
            overlap=Config.RAG_CHUNK_OVERLAP
        )
        
        documents = []
        for i, chunk in enumerate(chunks):
            doc_metadata = {
                'chunk_id': i,
                'total_chunks': len(chunks),
                **(metadata or {})
            }
            documents.append(Document(content=chunk, metadata=doc_metadata))
        
        return documents


class GroqClient:
    """Groq API client for LLM inference"""
    
    def __init__(self):
        self.api_key = Config.GROQ_API_KEY
        if not self.api_key:
            print("⚠️ Groq API key not set. RAG features will be limited.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)
            print("✅ Groq client initialized")
    
    def generate_response(self, prompt: str, max_tokens: int = None, temperature: float = None) -> str:
        """Generate response using Groq API"""
        if not self.client:
            return "Groq API not configured"
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educational AI assistant that provides detailed, constructive feedback on student answers."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=Config.GROQ_MODEL,
                max_tokens=max_tokens or Config.GROQ_MAX_TOKENS,
                temperature=temperature or Config.GROQ_TEMPERATURE
            )
            
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"❌ Groq API error: {e}")
            return f"Error generating response: {str(e)}"


class RAGService:
    """Main RAG service orchestrating all components"""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.groq_client = GroqClient()
        self.processor = DocumentProcessor()
    
    def ingest_document(self, text: str, metadata: Dict = None) -> bool:
        """Ingest a study material document"""
        try:
            # Process document into chunks
            documents = self.processor.process_document(text, metadata)
            
            # Add to vector store
            self.vector_store.add_documents(documents)
            
            return True
        except Exception as e:
            print(f"❌ Error ingesting document: {e}")
            return False
    
    def retrieve_context(self, query: str, top_k: int = None) -> List[Dict]:
        """Retrieve relevant context for a query"""
        top_k = top_k or Config.RAG_TOP_K
        
        # Search vector store
        results = self.vector_store.search(
            query,
            top_k=top_k,
            threshold=Config.RAG_SIMILARITY_THRESHOLD
        )
        
        # Format results
        context_list = []
        for doc, similarity in results:
            context_list.append({
                'content': doc.content,
                'similarity': float(similarity),
                'metadata': doc.metadata
            })
        
        return context_list
    
    def generate_enhanced_feedback(
        self,
        question: str,
        model_answer: str,
        student_answer: str,
        score: float,
        max_marks: float,
        similarity: float,
        nli_label: str,
        context: List[Dict] = None
    ) -> str:
        """Generate enhanced feedback using Groq with RAG context"""
        
        # Build context string
        context_str = ""
        if context:
            context_str = "\n\n**Reference Material:**\n"
            for i, ctx in enumerate(context, 1):
                context_str += f"\n{i}. {ctx['content'][:300]}...\n"
        
        # Build prompt
        prompt = f"""As an educational AI assistant, analyze this student's answer and provide constructive feedback.

**Question:** {question}

**Model Answer:** {model_answer}

**Student Answer:** {student_answer}

**Evaluation Metrics:**
- Score: {score:.2f}/{max_marks}
- Semantic Similarity: {similarity:.2%}
- Answer Relationship: {nli_label}
{context_str}

**Instructions:**
1. Identify what the student got right
2. Point out key concepts that are missing or incorrect
3. Provide specific suggestions for improvement
4. Reference the study material context if available
5. Be encouraging and constructive

**Feedback:**"""
        
        # Generate response
        feedback = self.groq_client.generate_response(prompt)
        
        return feedback
    
    def evaluate_with_rag(
        self,
        question: str,
        model_answer: str,
        student_answer: str,
        marks: float,
        use_rag: bool = False
    ) -> Dict:
        """Evaluate answer with optional RAG enhancement"""
        
        # Get RAG context if enabled
        context = []
        if use_rag and self.vector_store.index.ntotal > 0:
            # Retrieve context based on question and student answer
            query = f"{question} {student_answer}"
            context = self.retrieve_context(query)
        
        # Return context for evaluation service to use
        return {
            'context': context,
            'rag_enabled': use_rag and len(context) > 0
        }
    
    def save_vector_store(self, name: str = "default"):
        """Save current vector store"""
        self.vector_store.save(name)
    
    def load_vector_store(self, name: str = "default") -> bool:
        """Load existing vector store"""
        return self.vector_store.load(name)
    
    def clear_vector_store(self):
        """Clear the vector store"""
        self.vector_store.clear()


# Create singleton instance
rag_service = RAGService()
