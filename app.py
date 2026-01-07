"""
SkyWrite AI - Python Backend with Flask
Grammar correction and writing enhancement using Google's Gemini API
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables from .env file explicitly
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)
print(f"[DEBUG] Loading .env from: {env_path}")
print(f"[DEBUG] .env exists: {os.path.exists(env_path)}")
# Optional Google Generative AI SDK. If not installed, use a local fallback so the
# web UI can run without the external dependency during development.
try:
    import google.generativeai as genai
    HAS_GEMINI_SDK = True
except Exception:
    genai = None
    HAS_GEMINI_SDK = False

# Create Flask app with explicit template folder
script_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(script_dir, 'templates')
print(f"[DEBUG] Script dir: {script_dir}")
print(f"[DEBUG] Template dir: {template_dir}")
print(f"[DEBUG] Template dir exists: {os.path.exists(template_dir)}")
app = Flask(__name__, template_folder=template_dir)
CORS(app)

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'your-api-key-here')
print(f"[DEBUG] HAS_GEMINI_SDK: {HAS_GEMINI_SDK}")
print(f"[DEBUG] GEMINI_API_KEY set: {bool(GEMINI_API_KEY and GEMINI_API_KEY != 'your-api-key-here')}")
if HAS_GEMINI_SDK and GEMINI_API_KEY and GEMINI_API_KEY != 'your-api-key-here':
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print(f"[DEBUG] Gemini API configured successfully")
    except Exception as e:
        print(f"[DEBUG] Error configuring Gemini: {e}")

# Writing tone options
WRITING_TONES = {
    'original': 'Maintain the original tone and style',
    'professional': 'Use a professional and formal tone',
    'casual': 'Use a casual and friendly tone',
    'academic': 'Use an academic and scholarly tone'
}

def apply_local_grammar_correction(text, tone='original', show_explanations=True):
    """
    Apply comprehensive grammar corrections locally when Gemini API is unavailable
    """
    import re
    
    corrections = []
    corrected = text
    
    # Grammar rules: (pattern, replacement, reason, is_regex)
    grammar_rules = [
        # Capitalization
        (r'\bi\b', 'I', 'Capitalization: pronoun "i" → "I"', True),
        
        # Subject-verb agreement
        (r'\b([Hh]e|[Ss]he|[Ii]t)\s+are\b', r'\1 is', 'Subject-verb agreement: "are" → "is"', True),
        (r'\b([Ii]|[Yy]ou|[Ww]e|[Tt]hey|people)\s+is\b', r'\1 are', 'Subject-verb agreement: "is" → "are"', True),
        (r'\b([Hh]e|[Ss]he|[Ii]t)\s+have\b', r'\1 has', 'Subject-verb agreement: "have" → "has"', True),
        (r'\b([Ii]|[Yy]ou|[Ww]e|[Tt]hey)\s+has\b', r'\1 have', 'Subject-verb agreement: "has" → "have"', True),
        
        # Common contractions and typos
        (r"\byour\s+(going|coming|doing|making|taking)\b", r"you're \1", 'Contraction: "your" → "you\'re"', True),
        (r"\bits\s+([a-z])", r"it's \1", 'Contraction: "its" → "it\'s"', True),
        (r"\btheir\s+(going|coming|doing)\b", r"they're \1", 'Contraction: "their" → "they\'re"', True),
        (r"\bthere\s+(is|are)\b", r"there \1", 'Phrase: "there is/are" is correct', True),
        
        # Common spelling mistakes
        (r"\brecieve\b", 'receive', 'Spelling: "recieve" → "receive"', True),
        (r"\boccured\b", 'occurred', 'Spelling: "occured" → "occurred"', True),
        (r"\bseperate\b", 'separate', 'Spelling: "seperate" → "separate"', True),
        (r"\bneccessary\b", 'necessary', 'Spelling: "neccessary" → "necessary"', True),
        (r"\bdefinately\b", 'definitely', 'Spelling: "definately" → "definitely"', True),
        (r"\baccross\b", 'across', 'Spelling: "accross" → "across"', True),
        (r"\bwether\b", 'whether', 'Spelling: "wether" → "whether"', True),
        
        # Common phrase errors
        (r"\bwould\s+of\b", 'would have', 'Grammar: "would of" → "would have"', True),
        (r"\bcould\s+of\b", 'could have', 'Grammar: "could of" → "could have"', True),
        (r"\bshould\s+of\b", 'should have', 'Grammar: "should of" → "should have"', True),
        (r"\blot\s+of\b", 'lot of', 'Grammar: correct usage of "lot of"', True),
        
        # Double spaces
        (r"  +", ' ', 'Spacing: remove extra spaces', True),
    ]
    
    # Apply each rule
    for pattern, replacement, reason, is_regex in grammar_rules:
        try:
            if is_regex:
                # Find matches first to record them
                matches = list(re.finditer(pattern, corrected, flags=re.IGNORECASE))
                for match in matches:
                    original = match.group(0)
                    fixed = re.sub(pattern, replacement, original, flags=re.IGNORECASE)
                    if original != fixed and show_explanations:
                        # Avoid duplicate improvements
                        exists = any(c['original'].lower() == original.lower() for c in corrections)
                        if not exists:
                            corrections.append({
                                'original': original,
                                'fixed': fixed,
                                'reason': reason
                            })
                
                # Apply substitution to entire text
                corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
            else:
                # Simple string replacement
                if pattern in corrected:
                    if show_explanations:
                        corrections.append({
                            'original': pattern,
                            'fixed': replacement,
                            'reason': reason
                        })
                    corrected = corrected.replace(pattern, replacement)
        except Exception as e:
            print(f"[DEBUG] Grammar rule error for pattern {pattern}: {e}")
            continue
    
    return json.dumps({
        'correctedText': corrected.strip(),
        'improvements': corrections[:10]  # Limit to 10 improvements to avoid clutter
    })

def enhance_text(text, tone='original', show_explanations=True):
    """
    Enhance text using Gemini API with specified tone
    """
    try:
        tone_instruction = WRITING_TONES.get(tone, WRITING_TONES['original'])

        prompt = f"""You are an expert grammar correction and writing enhancement assistant.

Task: Review and improve the following text.
Tone: {tone_instruction}

Original Text:
{text}

Please provide:
1. The corrected and enhanced version of the text
2. {"A list of specific improvements made (in JSON format with 'original', 'fixed', and 'reason' fields)" if show_explanations else ""}

Format your response as JSON with these fields:
- correctedText: The improved text
- improvements: [{{"original": "...", "fixed": "...", "reason": "..."}}] (only if explanations are requested)

Respond ONLY with valid JSON, no additional text."""

        if HAS_GEMINI_SDK and GEMINI_API_KEY and GEMINI_API_KEY != 'your-api-key-here':
            try:
                # Use gemini-2.0-flash (latest model) or fall back to gemini-1.5-flash
                try:
                    model = genai.GenerativeModel('gemini-2.0-flash')
                except:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                
                response = model.generate_content(prompt)
                result_text = response.text.strip()
                print(f"[DEBUG] Gemini response received: {result_text[:100]}...")
            except Exception as e:
                print(f"[DEBUG] Gemini API error: {e}")
                # Use local grammar correction with simple rules
                result_text = apply_local_grammar_correction(text, tone, show_explanations)
        else:
            print(f"[DEBUG] Gemini SDK not available or API key not set")
            # Local fallback using simple grammar rules
            result_text = apply_local_grammar_correction(text, tone, show_explanations)
        
        # Clean up JSON response if it came from Gemini
        if isinstance(result_text, str):
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.startswith('```'):
                result_text = result_text[3:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            
            result = json.loads(result_text.strip())
        else:
            result = result_text
        
        return {
            'correctedText': result.get('correctedText', text),
            'improvements': result.get('improvements', []) if show_explanations else []
        }
    
    except Exception as e:
        print(f"Error in enhance_text: {e}")
        return {
            'correctedText': text,
            'improvements': [],
            'error': str(e)
        }

@app.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')

@app.route('/api/enhance', methods=['POST'])
def api_enhance():
    """API endpoint for text enhancement"""
    try:
        data = request.json
        text = data.get('text', '')
        tone = data.get('tone', 'original')
        show_explanations = data.get('showExplanations', True)
        
        if not text or not text.strip():
            return jsonify({'error': 'Text is required'}), 400
        
        result = enhance_text(text, tone, show_explanations)
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 500
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'api_configured': bool(GEMINI_API_KEY and GEMINI_API_KEY != 'your-api-key-here')
    })

if __name__ == '__main__':
    # Check if API key is configured
    if GEMINI_API_KEY == 'your-api-key-here':
        print("\n⚠️  WARNING: GEMINI_API_KEY not configured!")
        print("Set it using: export GEMINI_API_KEY='your-actual-api-key'\n")
    
    print("🚀 SkyWrite AI Backend starting...")
    print("📝 Access the app at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
