"""PDF Resume Extraction Utilities"""

import logging
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PDFExtractionResult:
    """Result from PDF extraction"""
    text: str
    num_pages: int
    metadata: Dict
    extraction_method: str
    confidence: float


class PDFExtractor:
    """Extract text and data from PDF resumes"""

    SUPPORTED_FORMATS = [".pdf"]

    @classmethod
    def extract_from_file(cls, file_path: str) -> PDFExtractionResult:
        """
        Extract text from PDF file
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            PDFExtractionResult with extracted text
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format not supported
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in cls.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {ext}")

        logger.info(f"Extracting from PDF: {file_path}")
        
        try:
            return cls._extract_with_pdfplumber(file_path)
        except ImportError:
            logger.warning("pdfplumber not available, trying PyPDF2")
            try:
                return cls._extract_with_pypdf(file_path)
            except ImportError:
                raise RuntimeError("No PDF extraction library available")

    @classmethod
    def _extract_with_pdfplumber(cls, file_path: str) -> PDFExtractionResult:
        """Extract using pdfplumber (preferred)"""
        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                text_parts = []
                metadata = {}
                
                # Extract metadata
                if pdf.metadata:
                    metadata = {
                        "title": pdf.metadata.get("Title"),
                        "author": pdf.metadata.get("Author"),
                        "subject": pdf.metadata.get("Subject"),
                    }

                # Extract text from all pages
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        text = page.extract_text()
                        if text:
                            text_parts.append(f"--- Page {page_num} ---\n{text}")
                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num}: {e}")

                full_text = "\n".join(text_parts)
                
                logger.info(
                    f"Extracted {len(pdf.pages)} pages, {len(full_text)} chars"
                )

                return PDFExtractionResult(
                    text=full_text,
                    num_pages=len(pdf.pages),
                    metadata=metadata,
                    extraction_method="pdfplumber",
                    confidence=0.95,
                )
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            raise

    @classmethod
    def _extract_with_pypdf(cls, file_path: str) -> PDFExtractionResult:
        """Fallback extraction using PyPDF2"""
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(file_path)
            text_parts = []

            for page_num, page in enumerate(reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(f"--- Page {page_num} ---\n{text}")
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num}: {e}")

            full_text = "\n".join(text_parts)
            
            logger.info(
                f"Extracted {len(reader.pages)} pages, {len(full_text)} chars"
            )

            return PDFExtractionResult(
                text=full_text,
                num_pages=len(reader.pages),
                metadata={},
                extraction_method="pypdf",
                confidence=0.85,
            )
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            raise

    @classmethod
    def clean_extracted_text(cls, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove extra whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        # Remove common artifacts
        text = text.replace("Page ", "")
        text = text.replace("pdf", "")

        return text

    @classmethod
    def extract_sections(cls, text: str) -> Dict[str, str]:
        """
        Extract common resume sections from text
        
        Returns:
            Dictionary mapping section names to content
        """
        sections = {}
        
        section_keywords = {
            "summary": ["SUMMARY", "OBJECTIVE", "PROFESSIONAL SUMMARY"],
            "experience": ["EXPERIENCE", "WORK HISTORY", "EMPLOYMENT"],
            "education": ["EDUCATION", "ACADEMIC", "QUALIFICATIONS"],
            "skills": ["SKILLS", "COMPETENCIES", "TECHNICAL SKILLS"],
            "certifications": ["CERTIFICATIONS", "LICENSES", "CREDENTIALS"],
            "projects": ["PROJECTS", "PORTFOLIO"],
            "awards": ["AWARDS", "ACHIEVEMENTS", "HONORS"],
            "languages": ["LANGUAGES", "FLUENCY"],
        }

        text_lines = text.split("\n")
        current_section = None
        current_content = []

        for line in text_lines:
            line_upper = line.upper().strip()
            
            # Check if line is a section header
            found_section = False
            for section_name, keywords in section_keywords.items():
                if any(keyword in line_upper for keyword in keywords):
                    # Save previous section
                    if current_section:
                        sections[current_section] = "\n".join(current_content).strip()
                    
                    current_section = section_name
                    current_content = []
                    found_section = True
                    break
            
            # Add line to current section if not a header
            if not found_section and current_section:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections
