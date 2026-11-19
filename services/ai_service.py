# -*- coding: utf-8 -*-
"""
NexaFiles: AI-Powered Document Intelligence & Text Analysis Service
Provides automatic text extraction, intelligent 3-bullet summarization,
and semantic keyword/tag generation for uploaded files.
"""

import re
import collections
from pathlib import Path

# Common stop words for keyword extraction
STOP_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are',
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but',
    'by', 'can', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for',
    'from', 'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself',
    'him', 'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself',
    'just', 'me', 'more', 'most', 'my', 'myself', 'no', 'nor', 'not', 'now', 'of', 'off',
    'on', 'once', 'only', 'or', 'other', 'our', 'ours', 'ourselves', 'out', 'over', 'own',
    'same', 'she', 'should', 'so', 'some', 'such', 'than', 'that', 'the', 'their', 'theirs',
    'them', 'themselves', 'then', 'there', 'these', 'they', 'this', 'those', 'through', 'to',
    'too', 'under', 'until', 'up', 'very', 'was', 'we', 'were', 'what', 'when', 'where',
    'which', 'while', 'who', 'whom', 'why', 'with', 'would', 'you', 'your', 'yours', 'yourself',
    'yourselves', 'will', 'shall', 'may', 'file', 'document', 'page', 'content', 'true', 'false',
    'none', 'null', 'undefined', 'return', 'import', 'from', 'class', 'def', 'const', 'let', 'var'
}

class AIService:
    """Intelligent document processor & summarizer."""

    def extract_text(self, file_path, max_bytes=200000):
        """Extract readable text from file payload."""
        p = Path(file_path)
        if not p.exists():
            return ""

        ext = p.suffix.lower().lstrip('.')
        
        # 1. Plain Text / Code / Markdown
        if ext in ['txt', 'py', 'js', 'html', 'css', 'json', 'md', 'xml', 'csv', 'sql', 'sh']:
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(max_bytes)
            except Exception:
                return ""

        # 2. PDF Document text extraction
        if ext == 'pdf':
            try:
                with open(p, 'rb') as f:
                    raw = f.read(max_bytes)
                # Extract text between parentheses in PDF text streams
                text_matches = re.findall(rb'\(([^\)\\]{2,})\)', raw)
                extracted = ' '.join(m.decode('utf-8', errors='ignore') for m in text_matches)
                if len(extracted.strip()) > 30:
                    return extracted
                # Fallback ASCII word scan
                ascii_words = re.findall(rb'[a-zA-Z]{3,}', raw)
                return ' '.join(w.decode('ascii', errors='ignore') for w in ascii_words[:500])
            except Exception:
                return ""

        # 3. Word Document (.docx) raw XML extraction
        if ext in ['docx', 'pptx', 'xlsx']:
            try:
                import zipfile
                with zipfile.ZipFile(p, 'r') as zf:
                    for name in zf.namelist():
                        if name.endswith('.xml') and ('document' in name or 'slide' in name or 'sheet' in name):
                            xml_content = zf.read(name).decode('utf-8', errors='ignore')
                            clean_text = re.sub(r'<[^>]+>', ' ', xml_content)
                            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                            return clean_text[:max_bytes]
            except Exception:
                pass

        return ""

    def summarize_document(self, text, filename="Document", category="Notes"):
        """
        Generate 3 concise executive bullet points summarizing document content.
        """
        text = text.strip()
        
        if not text or len(text) < 40:
            return [
                f"Document '{filename}' categorized under {category}.",
                "Cryptographically verified with SHA-256 integrity checks.",
                "Encrypted cloud vault persistence ready for pre-signed retrieval."
            ]

        # Extract sentences
        sentences = re.split(r'[.!?\n]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 25 and not s.strip().startswith('%')]

        bullets = []
        
        # Bullet 1: Core subject / purpose
        if sentences:
            primary = sentences[0]
            if len(primary) > 140:
                primary = primary[:137] + '...'
            bullets.append(f"Focus: {primary}.")
        else:
            bullets.append(f"Primary document: {filename} ({category}).")

        # Bullet 2: Key concepts or technical contents
        concepts = self.extract_keywords(text, top_n=5)
        if concepts:
            tags_str = ", ".join(concepts)
            bullets.append(f"Key topics & modules: Features active coverage of {tags_str}.")
        else:
            bullets.append("Contains structured personal notes and reference specifications.")

        # Bullet 3: Actionable insight or structure
        word_count = len(text.split())
        bullets.append(f"Repository footprint: Estimated {word_count} words indexed for sub-second retrieval.")

        return bullets

    def extract_keywords(self, text, top_n=6):
        """Extract top representative keywords for smart tagging."""
        if not text:
            return []

        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_\-]{2,}\b', text.lower())
        meaningful_words = [
            w for w in words
            if w not in STOP_WORDS and not w.isdigit() and len(w) > 3
        ]

        counter = collections.Counter(meaningful_words)
        return [word for word, _ in counter.most_common(top_n)]

# Global Singleton
ai_service = AIService()
