# 🚀 Gemini API Setup Guide - Phase Two Document Analyzer

## Overview
Phase Two has been updated to use **Google Gemini 1.5 Flash API** for real AI-powered document analysis instead of dummy responses.

## Step 1: Get Your Gemini API Key

1. Visit **https://makersuite.google.com/app/apikey**
2. Sign in with your Google account (or create one)
3. Click **"Create API Key"**
4. Copy the generated API key

## Step 2: Configure Your .env File

1. Open the `.env` file in the root directory (`d:\FYP FInal\.env`)
2. Replace `your_gemini_api_key_here` with your actual API key:
   ```
   GEMINI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
   ```
3. Save the file

## Step 3: Restart the Flask Server

The backend will automatically pick up the new configuration:

```bash
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

python main.py
```

## 📋 What's New in Phase Two

### Features
✅ **Real AI Analysis** - Uses Google Gemini 3.6 Flash model (`gemini-3.6-flash` with `gemini-2.5-flash-lite` fallback)  
✅ **Secure File Handling** - Temporary files with automatic cleanup  
✅ **Privacy Protection** - Files deleted from Gemini servers after processing  
✅ **Structured JSON Output** - Consistent, frontend-ready responses  
✅ **12-Category Evaluation**:
  - Structure (0-100)
  - Clarity (0-100)
  - Persuasion (0-100)
  - Content Quality (0-100)
  - Call to Action (0-100)
  - Grammar and Syntax (0-100)
  - Accuracy (0-100)
  - Overall score (0-100)
  - tone (0-100)
  - Audience (0-100)
  - Purpose (0-100)
✅ **7 Cs Analysis**:
  - Clear
  - Concise
  - Correct
  - Complete
  - Courteous
  - Concrete
  - Consistent

✅ **Additional Outputs**:
  - Strengths (top 5)
  - Recommendations (top 5 actionable improvements)
  - Detailed comprehensive feedback

### Supported File Formats
- 📄 PDF
- 📊 PPTX (PowerPoint)
- 📝 DOCX (Word)
- 📃 TXT (Text)
- 🖼️ PNG, JPG, JPEG, GIF, WEBP (Images)

## 🔐 Security Features

### Temporary File Handling
```python
# Uses Python's tempfile module for:
- Secure isolated file storage
- Memory-efficient processing
- Automatic cleanup after use
```

### File Deletion
```python
# After processing:
1. Delete file from Gemini servers (privacy protection)
2. Delete local temporary file (memory cleanup)
3. Graceful error handling if deletion fails
```

### JSON Response Format
```python
# Forced JSON output ensures:
- Structured data format
- Prevents LLM from returning markdown
- Guarantees schema consistency
- Better error handling
```

## 🧪 Test the Integration

You can test the new endpoint with a sample file:

```bash
curl -X POST http://localhost:5000/api/analyze-document \
  -F "file=@sample.pdf"
```

Or use Python:
```python
import requests

with open('sample.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:5000/api/analyze-document',
        files=files
    )
    print(response.json())
```

## 📊 Expected Response Format

```json
{
  "status": "success",
  "document_name": "presentation.pdf",
  "overall_score": 87,
  "category_scores": {
    "Structure": 88,
    "Clarity": 85,
    "Persuasion": 82,
    "Content_Quality": 90,
    "Call_to_Action": 84,
    "Grammar_and_Syntax": 89,
    "Accuracy": 91,
    "Tone_Appropriateness": 78,
    "Audience_Alignment": 83,
    "Purpose_Fulfillment": 86
  },
  "seven_cs_evaluation": {
    "Clear": {
      "status": "Passed",
      "feedback": "Well-organized with clear headers and progressive logical flow."
    },
    "Concise": {
      "status": "Needs Improvement",
      "feedback": "Could reduce redundant background sections on slide 3."
    },
    "Correct": {
      "status": "Passed",
      "feedback": "All facts, data points, and terminology are verified and correct."
    },
    "Complete": {
      "status": "Passed",
      "feedback": "Covers all essential topics and mandatory analytical parameters."
    },
    "Courteous": {
      "status": "Passed",
      "feedback": "Maintains an exceptionally professional, objective, and respectful tone."
    },
    "Concrete": {
      "status": "Needs Improvement",
      "feedback": "Needs more visual graphs or quantitative metrics to ground claims."
    },
    "Consistent": {
      "status": "Passed",
      "feedback": "Uniform typographic layout, structural design, and tone throughout."
    }
  },
  "strengths": [
    "Strong visual organization across segments",
    "Compelling narrative flow and contextual alignment",
    "Well-researched subject matter expertise",
    "Clear semantic structures",
    "Professional font hierarchy"
  ],
  "recommendations": [
    "Add an executive summary slide at the beginning",
    "Include more native data visualization items",
    "Strengthen call-to-action closing section",
    "Condense introductory text blocks into scannable lists",
    "Align contrasting accent colors to increase readability"
  ],
  "detailed_feedback": "Your document demonstrates excellent technical precision and highly structured logical execution. Minor visual optimizations and concise textual refactoring will elevate its delivery to corporate presentation benchmarks.",
  "analysis_timestamp": "2026-06-20T10:02:02.123456"
}
```


## ⚠️ Error Handling

### Missing API Key
```json
{
  "error": "500 Internal Server Error",
  "message": "GEMINI_API_KEY not found in environment variables"
}
```

### Unsupported File Format
```json
{
  "error": "Unsupported file format",
  "message": "Supported formats: .pdf, .pptx, .docx, .txt, .png, .jpg, .jpeg, .gif, .webp"
}
```

### API Timeout
```json
{
  "error": "Document analysis failed",
  "message": "An error occurred while analyzing your document.",
  "details": "API timeout or rate limit exceeded"
}
```

## 🎓 Technical Details for Your FYP Defense

### Temporary File Handling (tempfile module)
**Why it's necessary:**
- Gemini API cannot process `request.files` objects directly
- Flask's FileStorage objects are in-memory representations
- Solution: Write to disk temporarily, upload to API, then cleanup

**Benefits:**
- Memory efficiency (not loading entire file into RAM)
- Secure isolated storage
- Automatic cleanup with context managers
- Works with large files (100+ MB)

### JSON MIME Type Configuration
**Why it's necessary:**
- LLMs naturally generate text/markdown format
- Without `response_mime_type="application/json"`, model might return markdown
- JSON MIME type forces structured JSON output

**Configuration:**
```python
generation_config={
    "response_mime_type": "application/json",
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40
}
```

**Benefits:**
- Guarantees valid JSON response
- Prevents parsing errors on frontend
- Ensures schema consistency
- Simplifies error handling

### File Deletion Strategy
**Why both deletions matter:**
1. **Gemini Server Deletion** - Data privacy compliance, reduces API storage footprint
2. **Local Temp File Deletion** - System memory cleanup, prevents accumulation
3. **Graceful Error Handling** - Doesn't crash if deletion fails, logs warnings

## 📞 Troubleshooting

### "ModuleNotFoundError: No module named 'google'"
- Solution: Ensure virtual environment is activated
- Run: `pip install google-generativeai python-dotenv`

### "GEMINI_API_KEY not found"
- Solution: Check if `.env` file exists in root directory
- Verify API key is correctly set in `.env`
- Restart Flask server after updating `.env`

### "Invalid JSON response from AI model"
- Solution: API might be rate-limited or temporarily down
- Wait a moment and try again
- Check API key validity at https://makersuite.google.com/app/apikey

### File upload fails with large files
- Solution: Check Flask max file size configuration
- Update `main.py` with: `app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024`  # 100MB

## 🚀 Next Steps

1. ✅ Add your GEMINI_API_KEY to `.env`
2. ✅ Restart Flask server
3. ✅ Test with sample documents
4. ✅ Integrate frontend file upload component
5. ✅ Monitor API usage at https://makersuite.google.com/app/billing

---

**Last Updated:** May 24, 2026  
**Version:** Phase Two v2.0 - Gemini Integration
