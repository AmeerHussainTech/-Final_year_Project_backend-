import requests
import json
import io
import sys

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://localhost:5000"

def run_tests():
    print("==================================================")
    print("    PRESENOVA FULL END-TO-END AUTOMATED TEST      ")
    print("==================================================")
    
    session = requests.Session()
    
    # 1. Root Health Check
    print("\n[TEST 1] Root Health Check GET /")
    res = session.get(f"{BASE_URL}/")
    assert res.status_code == 200, f"Failed: {res.text}"
    print(f"  Result: {res.json()}")

    # 2. API Health Check
    print("\n[TEST 2] API Health Check GET /api/health")
    res = session.get(f"{BASE_URL}/api/health")
    assert res.status_code == 200, f"Failed: {res.text}"
    print(f"  Result: {res.json()}")

    # 3. Auth Signup
    print("\n[TEST 3] Auth Signup POST /api/auth/signup")
    import random
    test_email = f"test_user_{random.randint(1000, 9999)}@example.com"
    signup_data = {
        "name": "Test Runner",
        "email": test_email,
        "password": "Password123!"
    }
    res = session.post(f"{BASE_URL}/api/auth/signup", json=signup_data)
    print(f"  Signup Status: {res.status_code}")
    assert res.status_code in (200, 201), f"Signup failed: {res.text}"
    signup_resp = res.json()
    token = signup_resp.get("access_token")
    assert token, "No access token returned!"
    print(f"  User created: {signup_resp.get('user', {}).get('email')}")

    # Set Auth header for subsequent requests
    session.headers.update({"Authorization": f"Bearer {token}"})

    # 4. Auth Me
    print("\n[TEST 4] Auth Me GET /api/auth/me")
    res = session.get(f"{BASE_URL}/api/auth/me")
    assert res.status_code == 200, f"Failed: {res.text}"
    print(f"  User profile retrieved: {res.json().get('user', {}).get('name')}")

    # 5. Document Analyzer
    print("\n[TEST 5] Document Analyzer POST /api/analyze-document")
    doc_content = (
        "Slide 1: Artificial Intelligence in Healthcare\n"
        "AI algorithms enable faster medical imaging diagnosis and personalized treatment plans.\n\n"
        "Slide 2: Methodology\n"
        "We used deep convolutional neural networks trained on 10,000 anonymized X-ray scans.\n\n"
        "Slide 3: Results\n"
        "The model achieved 94.2% sensitivity and reduced diagnosis latency by 35%.\n"
    )
    files = {
        "file": ("sample_presentation.txt", io.BytesIO(doc_content.encode("utf-8")), "text/plain")
    }
    res = session.post(f"{BASE_URL}/api/analyze-document", files=files)
    print(f"  Status: {res.status_code}")
    assert res.status_code == 200, f"Document analysis failed: {res.text}"
    doc_report = res.json()
    print(f"  Overall Score: {doc_report.get('overall_score')}")
    print(f"  Grammar Score: {doc_report.get('grammar_score')}")
    print(f"  Grammar Issues Count: {doc_report.get('grammar_issues_count')}")

    # 6. Speech Analyzer
    print("\n[TEST 6] Speech Analyzer POST /api/analyze-speech")
    speech_payload = {
        "text": "Hello everyone, um basically today I am going to talk about our research project. We worked very hard and actually got good results.",
        "duration_seconds": 25
    }
    res = session.post(f"{BASE_URL}/api/analyze-speech", json=speech_payload)
    print(f"  Status: {res.status_code}")
    assert res.status_code == 200, f"Speech analysis failed: {res.text}"
    speech_report = res.json()
    print(f"  Speech Speed WPM: {speech_report.get('speech_speed_wpm')}")
    print(f"  Filler Words Count: {speech_report.get('filler_words_count')}")
    print(f"  Grammar Score: {speech_report.get('grammar_score')}")

    # 7. AI Practice Coach Chat
    print("\n[TEST 7] AI Coach Chat POST /api/practice-chat")
    chat_payload = {
        "message": "How can I reduce filler words like um and basically during my speech?",
        "history": [],
        "contextReport": {
            "phase": "practice",
            "v1Analysis": doc_report
        }
    }
    res = session.post(f"{BASE_URL}/api/practice-chat", json=chat_payload)
    print(f"  Status: {res.status_code}")
    assert res.status_code == 200, f"Chat failed: {res.text}"
    chat_resp = res.json()
    print(f"  AI Coach Response Snippet: {chat_resp.get('ai_response', '')[:100]}...")

    # 8. User History
    print("\n[TEST 8] User History GET /api/auth/history")
    res = session.get(f"{BASE_URL}/api/auth/history")
    print(f"  Status: {res.status_code}")
    assert res.status_code == 200, f"History failed: {res.text}"
    reports = res.json().get("reports", [])
    print(f"  History records found: {len(reports)}")

    print("\n==================================================")
    print("   ALL API ENDPOINTS TESTED SUCCESSFULLY! [OK]    ")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
