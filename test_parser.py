#!/usr/bin/env python3
"""
Test script for Parser Agent
Tests PDF parsing, data extraction, and Master CV generation
"""

import sys
import json
from parser_agent import ParserAgent
from master_cv import MasterCV, Location, Skill

def print_section(title):
    """Pretty print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_basic_extraction():
    """Test basic resume parsing from text"""
    print_section("Test 1: Basic Text Extraction")
    
    # Create sample resume text
    sample_resume = """
    JOHN DOE
    john.doe@example.com | +91 9876543210
    Bangalore, India
    
    Professional Summary:
    Senior Software Engineer with 5+ years experience in backend development.
    
    Skills:
    - Python, Java, JavaScript
    - Docker, Kubernetes, AWS
    - React, Node.js, Django
    
    Experience:
    Senior Software Engineer at Tech Corp (2021-Present)
    - Led backend team of 5 engineers
    - Designed microservices architecture
    
    Education:
    B.Tech Computer Science
    IIT Delhi (2019)
    """
    
    # Create parser
    parser = ParserAgent()
    
    # Test text sections extraction
    from parser_tools import PDFExtractor
    sections = PDFExtractor.extract_sections(sample_resume)
    
    print("Extracted sections:")
    for section, content in sections.items():
        print(f"\n[{section.upper()}]")
        print(content[:100] + "..." if len(content) > 100 else content)
    
    return True

def test_skill_extraction():
    """Test skill extraction from resume text"""
    print_section("Test 2: Skill Extraction")
    
    sample_text = """
    Technical Skills:
    - Python, Java, JavaScript, TypeScript
    - React, Vue, Angular
    - Docker, Kubernetes, AWS, Azure
    - PostgreSQL, MongoDB, Redis
    - Machine Learning, TensorFlow, PyTorch
    
    Soft Skills:
    - Team Leadership
    - Problem Solving
    - Communication
    """
    
    from parser_tools import SkillExtractor
    skills = SkillExtractor.extract_skills(sample_text)
    
    print(f"Extracted {len(skills)} skills:")
    for skill in skills[:10]:
        print(f"  • {skill.name} ({skill.proficiency}) - {skill.category}")
    
    return len(skills) > 0

def test_contact_extraction():
    """Test contact information extraction"""
    print_section("Test 3: Contact Information Extraction")
    
    sample_text = """
    John Doe
    Email: john.doe@example.com
    Phone: +91 98765 43210
    Location: Bangalore, Karnataka, India
    LinkedIn: https://linkedin.com/in/johndoe
    GitHub: https://github.com/johndoe
    """
    
    from parser_tools import ContactInfoExtractor, SocialLinkExtractor
    
    name = ContactInfoExtractor.extract_name(sample_text)
    email = ContactInfoExtractor.extract_email(sample_text)
    phone = ContactInfoExtractor.extract_phone(sample_text)
    location = ContactInfoExtractor.extract_location(sample_text)
    socials = SocialLinkExtractor.extract_social_links(sample_text)
    
    print(f"Name: {name}")
    print(f"Email: {email}")
    print(f"Phone: {phone}")
    print(f"Location: {location.city if location else 'N/A'}, {location.country if location else 'N/A'}")
    if socials:
        print(f"LinkedIn: {socials.linkedin or 'N/A'}")
        print(f"GitHub: {socials.github or 'N/A'}")
    
    return email and phone

def test_master_cv_schema():
    """Test Master CV schema validation"""
    print_section("Test 4: Master CV Schema Validation")
    
    from parser_tools import SkillExtractor
    
    # Create sample CV
    cv = MasterCV(
        name="Jane Smith",
        email="jane@example.com",
        phone="+1234567890",
        location=Location(city="San Francisco", country="USA"),
        summary="Full-stack engineer with 3 years experience",
        skills=[
            Skill(name="Python", proficiency="expert", category="technical"),
            Skill(name="React", proficiency="intermediate", category="technical"),
            Skill(name="Leadership", proficiency="intermediate", category="soft"),
        ]
    )
    
    print(f"Master CV Created:")
    print(f"  Name: {cv.name}")
    print(f"  Email: {cv.email}")
    print(f"  Location: {cv.location.city}, {cv.location.country}")
    print(f"  Skills: {len(cv.skills)}")
    
    # Calculate completion
    completion = cv.calculate_completion()
    print(f"\nCompletion: {completion}%")
    
    # Get missing fields
    missing = cv.get_missing_fields()
    print(f"Missing required fields: {missing if missing else 'None!'}")
    
    # Export to JSON
    json_export = cv.to_json()
    print(f"\nJSON Export (truncated):")
    print(json.dumps(json_export, indent=2)[:300] + "...")
    
    return True

def test_llm_parsing():
    """Test LLM-based parsing (requires API key)"""
    print_section("Test 5: LLM-based Parsing")
    
    try:
        parser = ParserAgent()
        print("[OK] ParserAgent initialized with Claude API")
        print("  Note: Full test requires a real PDF file")
        print("  Usage: parser.parse_workflow('path/to/resume.pdf')")
        return True
    except Exception as e:
        print(f"[FAIL] Error initializing ParserAgent: {e}")
        print("  Make sure ANTHROPIC_API_KEY is set in .env")
        return False

def test_validation():
    """Test CV field validation"""
    print_section("Test 6: CV Field Validation")
    
    try:
        # Test invalid email
        cv = MasterCV(
            name="Test User",
            email="invalid-email",
            phone="+1234567890",
            location=Location(city="City", country="Country")
        )
        print("[FAIL] Should have failed on invalid email")
        return False
    except ValueError as e:
        print(f"[OK] Email validation working: {e}")
    
    try:
        # Test valid email
        cv = MasterCV(
            name="Test User",
            email="test@example.com",
            phone="+1234567890",
            location=Location(city="City", country="Country")
        )
        print("[OK] Valid email accepted")
    except ValueError as e:
        print(f"[FAIL] Unexpected error: {e}")
        return False
    
    try:
        # Test invalid phone (too short)
        cv = MasterCV(
            name="Test User",
            email="test@example.com",
            phone="123",
            location=Location(city="City", country="Country")
        )
        print("[FAIL] Should have failed on short phone")
        return False
    except ValueError as e:
        print(f"[OK] Phone validation working: {e}")
    
    return True

def run_all_tests():
    """Run all tests"""
    print_section("FresherFlow Parser Agent - Test Suite")
    print("Testing resume parsing, schema validation, and LLM integration\n")
    
    tests = [
        ("Basic Text Extraction", test_basic_extraction),
        ("Skill Extraction", test_skill_extraction),
        ("Contact Extraction", test_contact_extraction),
        ("Master CV Schema", test_master_cv_schema),
        ("LLM Parsing", test_llm_parsing),
        ("Field Validation", test_validation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, "PASS" if result else "FAIL"))
        except Exception as e:
            print(f"\n[FAIL] Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, "ERROR"))
    
    # Summary
    print_section("Test Summary")
    for test_name, status in results:
        symbol = "[OK]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[WARN]"
        print(f"{symbol} {test_name}: {status}")
    
    passed = sum(1 for _, s in results if s == "PASS")
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
