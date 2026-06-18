"""
Flask API endpoints for Parser Agent
Handles resume upload and parsing
"""

from flask import Blueprint, request, jsonify
import os
import tempfile
from parser_agent import ParserAgent
from master_cv import MasterCV

parser_bp = Blueprint('parser', __name__, url_prefix='/api/parser')
parser_agent = ParserAgent()


@parser_bp.route('/parse-pdf', methods=['POST'])
def parse_pdf():
    """
    Parse uploaded PDF resume and extract Master CV
    
    Request:
    - file: PDF file (multipart/form-data)
    - user_input: Optional JSON object with missing fields
    
    Response:
    {
        "status": "success|error",
        "data": {Master CV JSON},
        "missing_fields": ["name", "email", ...],
        "completion": 75
    }
    """
    try:
        # Check file in request
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "Empty filename"}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"status": "error", "message": "Only PDF files supported"}), 400
        
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            file.save(tmp.name)
            temp_path = tmp.name
        
        try:
            # Get optional user input
            user_input = None
            if request.form.get('user_input'):
                import json
                user_input = json.loads(request.form.get('user_input'))
            
            # Parse PDF
            cv = parser_agent.parse_workflow(temp_path, user_input)
            
            return jsonify({
                "status": "success",
                "data": cv.to_json(),
                "missing_fields": cv.metadata.nullFields,
                "completion": cv.metadata.completionPercentage
            }), 200
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@parser_bp.route('/validate-cv', methods=['POST'])
def validate_cv():
    """
    Validate and fill missing fields in Master CV
    
    Request:
    {
        "cv": {Master CV object},
        "user_input": {fields to update}
    }
    
    Response:
    {
        "status": "success|error",
        "data": {Updated Master CV},
        "missing_fields": ["field1", ...],
        "completion": 85
    }
    """
    try:
        data = request.get_json()
        
        if not data.get("cv"):
            return jsonify({"status": "error", "message": "No CV data provided"}), 400
        
        # Reconstruct CV from JSON
        cv_data = data["cv"]
        cv = MasterCV(**cv_data)
        
        # Fill missing fields
        user_input = data.get("user_input", {})
        cv = parser_agent.fill_missing_fields(cv, user_input)
        
        return jsonify({
            "status": "success",
            "data": cv.to_json(),
            "missing_fields": cv.metadata.nullFields,
            "completion": cv.metadata.completionPercentage
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@parser_bp.route('/parse-portfolio', methods=['POST'])
def parse_portfolio():
    """
    Parse resume from portfolio URL
    
    Request:
    {
        "portfolio_url": "https://example.com"
    }
    
    Response:
    {
        "status": "success|error",
        "data": {Master CV JSON},
        "message": "Portfolio parsing not yet implemented"
    }
    """
    try:
        data = request.get_json()
        portfolio_url = data.get("portfolio_url")
        
        if not portfolio_url:
            return jsonify({"status": "error", "message": "No URL provided"}), 400
        
        # Parse from portfolio
        cv = parser_agent.extract_from_portfolio(portfolio_url)
        
        return jsonify({
            "status": "success",
            "data": cv.to_json(),
            "missing_fields": cv.metadata.nullFields,
            "message": "Portfolio parsing is experimental. Please fill missing fields manually."
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@parser_bp.route('/health', methods=['GET'])
def health():
    """Health check for parser service"""
    return jsonify({
        "status": "healthy",
        "service": "parser-agent",
        "version": "1.0"
    }), 200
