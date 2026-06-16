"""Parser Agent - Resume parsing using LangGraph"""

import logging
import json
from typing import Dict, Optional, Tuple
from cv_customizer.agents.llm_provider import LLMProvider, LLMResponse
from cv_customizer.agents.workflows import ParserAgentWorkflow
from cv_customizer.utils.pdf_extractor import PDFExtractor
from cv_customizer.utils.portfolio_scraper import PortfolioScraper
from cv_customizer.utils.cv_prompts import CVExtractionPrompts, DataValidationPrompts
from cv_customizer.models.master_cv import MasterCV
from cv_customizer.utils.cv_utils import CVValidator

logger = logging.getLogger(__name__)


class ParserAgent:
    """
    Agent 1: Parse resume/portfolio and create structured Master CV
    
    Uses LLM for intelligent data extraction and structuring.
    Supports PDF upload and portfolio website scraping.
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.workflow = ParserAgentWorkflow(provider)
        logger.info(f"ParserAgent initialized with provider: {provider.provider_type.value}")

    def parse_pdf(self, file_path: str) -> Tuple[Dict, float]:
        """
        Parse PDF resume and extract data
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Tuple of (extracted_cv_data, confidence_score)
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If extraction fails
        """
        logger.info(f"Parsing PDF: {file_path}")
        try:
            # Extract PDF content
            pdf_result = PDFExtractor.extract_from_file(file_path)
            cleaned_text = PDFExtractor.clean_extracted_text(pdf_result.text)
            
            logger.info(f"PDF extraction confidence: {pdf_result.confidence}")
            
            # Extract sections
            sections = PDFExtractor.extract_sections(cleaned_text)
            
            # Process with LLM
            return self._process_raw_text(cleaned_text, source="pdf")
            
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            raise

    def parse_portfolio(self, portfolio_url: str) -> Tuple[Dict, float]:
        """
        Parse portfolio website using web scraping and extract CV data
        
        Args:
            portfolio_url: URL to portfolio website
            
        Returns:
            Tuple of (extracted_cv_data, confidence_score)
            
        Raises:
            ValueError: If scraping fails
        """
        logger.info(f"Parsing portfolio: {portfolio_url}")
        try:
            # Scrape portfolio
            scraping_result = PortfolioScraper.scrape_url(portfolio_url, headless=True)
            
            if scraping_result.error:
                logger.error(f"Scraping error: {scraping_result.error}")
                raise ValueError(f"Failed to scrape portfolio: {scraping_result.error}")
            
            logger.info(f"Portfolio scraping confidence: {scraping_result.confidence}")
            
            # Extract contact info
            email = PortfolioScraper.extract_email(scraping_result.content)
            phone = PortfolioScraper.extract_phone(scraping_result.content)
            social_links = PortfolioScraper.extract_social_links(scraping_result.content)
            
            # Prepare text with extracted metadata
            text_with_metadata = f"""
            Title: {scraping_result.title}
            Email: {email}
            Phone: {phone}
            Social Links: {social_links}
            
            Sections:
            """
            for section_name, content in scraping_result.sections.items():
                text_with_metadata += f"\n{section_name.upper()}:\n{content}\n"
            
            # Process with LLM
            return self._process_raw_text(text_with_metadata, source="portfolio")
            
        except Exception as e:
            logger.error(f"Portfolio parsing failed: {e}")
            raise

    def generate_master_cv(self, extracted_data: Dict) -> Tuple[MasterCV, float]:
        """
        Generate structured Master CV from extracted data
        
        Args:
            extracted_data: Raw extracted data
            
        Returns:
            Tuple of (Master CV object, confidence_score)
            
        Raises:
            ValueError: If structuring fails
        """
        logger.info("Generating Master CV from extracted data...")
        try:
            # Build Master CV structuring prompt
            extracted_json = json.dumps(extracted_data, indent=2)
            prompt = CVExtractionPrompts.build_master_cv_structuring_prompt(extracted_json)
            
            # Call LLM to structure data
            response: LLMResponse = self.provider.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=6000
            )
            
            # Parse response
            master_cv_dict = self._parse_json_response(response.content)
            
            # Validate against schema
            master_cv = MasterCV(**master_cv_dict)
            
            # Calculate confidence
            validation = CVValidator.validate_cv(master_cv)
            confidence = validation.confidence_score
            
            logger.info(f"Master CV generated with confidence: {confidence}")
            return master_cv, confidence
            
        except Exception as e:
            logger.error(f"Master CV generation failed: {e}")
            raise

    def fill_missing_fields(self, master_cv: MasterCV) -> MasterCV:
        """
        Fill missing CV fields with null or default values
        
        Args:
            master_cv: Partial Master CV object
            
        Returns:
            Master CV with missing fields filled
        """
        logger.info("Filling missing fields...")
        
        # Validate and get missing fields
        validation = CVValidator.validate_cv(master_cv)
        
        if validation.missing_fields:
            logger.warning(f"Missing fields: {validation.missing_fields}")
        
        return master_cv

    def validate_cv_quality(self, master_cv: MasterCV) -> Dict:
        """
        Validate CV quality and provide feedback
        
        Args:
            master_cv: Master CV to validate
            
        Returns:
            Validation report with scores and recommendations
        """
        logger.info("Validating CV quality...")
        
        validation = CVValidator.validate_cv(master_cv)
        
        return {
            "is_valid": validation.is_valid,
            "missing_fields": validation.missing_fields,
            "warnings": validation.warnings,
            "confidence_score": validation.confidence_score,
        }

    def parse_complete_workflow(self, input_data: Dict) -> Dict:
        """
        Complete parsing workflow: extract, structure, validate
        
        Args:
            input_data: Input with 'file_path' or 'portfolio_url'
            
        Returns:
            Result with master_cv and metadata
        """
        logger.info("Starting complete parse workflow...")
        
        source_type = input_data.get("source_type")
        result = {
            "success": False,
            "master_cv": None,
            "confidence_score": 0,
            "errors": [],
            "warnings": [],
        }
        
        try:
            # Step 1: Extract data
            if source_type == "pdf":
                extracted, extraction_conf = self.parse_pdf(input_data["file_path"])
            elif source_type == "portfolio":
                extracted, extraction_conf = self.parse_portfolio(input_data["portfolio_url"])
            else:
                raise ValueError(f"Unknown source type: {source_type}")
            
            logger.info(f"Extraction confidence: {extraction_conf}")
            
            # Step 2: Generate Master CV
            master_cv, structuring_conf = self.generate_master_cv(extracted)
            logger.info(f"Structuring confidence: {structuring_conf}")
            
            # Step 3: Fill missing fields
            master_cv = self.fill_missing_fields(master_cv)
            
            # Step 4: Validate quality
            validation = self.validate_cv_quality(master_cv)
            
            result.update({
                "success": True,
                "master_cv": master_cv,
                "confidence_score": (extraction_conf + structuring_conf) / 2,
                "validation": validation,
                "missing_fields": validation["missing_fields"],
                "warnings": validation["warnings"],
            })
            
            logger.info(f"Parse workflow completed. Confidence: {result['confidence_score']}")
            
        except Exception as e:
            logger.error(f"Parse workflow failed: {e}")
            result["errors"].append(str(e))
        
        return result

    def _process_raw_text(self, raw_text: str, source: str = "unknown") -> Tuple[Dict, float]:
        """Process raw text with LLM extraction"""
        logger.info(f"Processing raw text from {source}...")
        
        # Build extraction prompt
        prompt = CVExtractionPrompts.build_initial_parsing_prompt(raw_text)
        
        # Call LLM to extract
        response: LLMResponse = self.provider.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=4000
        )
        
        # Parse JSON response
        extracted_data = self._parse_json_response(response.content)
        
        # Estimate confidence based on completeness
        confidence = self._estimate_extraction_confidence(extracted_data)
        
        logger.info(f"Extraction confidence: {confidence}")
        return extracted_data, confidence

    def _parse_json_response(self, response_text: str) -> Dict:
        """Parse JSON from LLM response"""
        try:
            # Remove markdown formatting if present
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            text = text.strip()
            parsed = json.loads(text)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return {}

    def _estimate_extraction_confidence(self, extracted_data: Dict) -> float:
        """Estimate extraction confidence based on data completeness"""
        if not extracted_data:
            return 0.0
        
        confidence = 0.0
        factors = 0
        
        # Check for key sections
        if extracted_data.get("personal_info"):
            confidence += 0.2
        factors += 1
        
        if extracted_data.get("professional_summary"):
            confidence += 0.2
        factors += 1
        
        if extracted_data.get("experience"):
            confidence += 0.2
        factors += 1
        
        if extracted_data.get("education"):
            confidence += 0.2
        factors += 1
        
        if extracted_data.get("skills"):
            confidence += 0.2
        factors += 1
        
        return min(1.0, confidence / 5 if factors > 0 else 0)
