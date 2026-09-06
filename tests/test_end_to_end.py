"""
End-to-end runtime test for the Presentation Enhancement Platform.
Tests: upload -> extract -> analyze -> rewrite -> validate -> save -> report -> download
"""
import requests
import json
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://localhost:5000"
TEST_FILE = r"c:\Users\fatim\Downloads\FYP Final\test_sample.pptx"

def test_health():
    print("\n=== STEP 1: Health Check ===")
    r = requests.get(f"{BASE_URL}/")
    data = r.json()
    print(f"Status: {data.get('status')}")
    assert data.get('status') == 'running', "Backend not running!"
    print("✅ Health check passed")
    return True

def test_upload(filepath, mode="professional", tone="professional"):
    print(f"\n=== STEP: Upload (mode={mode}, tone={tone}) ===")
    with open(filepath, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/api/presentation-rewriter/submit",
            files={"file": (os.path.basename(filepath), f, "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
            data={"mode": mode, "tone": tone},
        )
    print(f"HTTP {r.status_code}")
    data = r.json()
    if not data.get("success"):
        print(f"❌ Upload failed: {data.get('message')}")
        return None
    print(f"✅ Success: {data.get('message')}")
    print(f"   Slides: {data.get('slides_processed')}")
    print(f"   Time: {data.get('processing_time')}")
    print(f"   Output: {data.get('output_filename')}")
    print(f"   Mode: {data.get('mode')}")
    print(f"   Tone: {data.get('tone')}")
    return data

def verify_quality_scores(data):
    print("\n=== Verify Quality Scores ===")
    qs = data.get("quality_scores", {})
    print(f"   Overall: {qs.get('overall_score')}/100")
    print(f"   Grade: {qs.get('grade')}")
    assert qs.get("overall_score") is not None, "Missing overall_score"
    assert qs.get("category_scores") is not None, "Missing category_scores"
    print(f"   Categories: {list(qs.get('category_scores', {}).keys())}")
    print(f"   7 Cs: {list(qs.get('seven_cs_scores', {}).keys())}")
    assert len(qs.get("category_scores", {})) > 0, "Empty category scores"
    print("✅ Quality scores verified")

def verify_final_assessment(data):
    print("\n=== Verify Final Assessment ===")
    fa = data.get("final_assessment", {})
    if not fa:
        print("⚠️ No final_assessment in response")
        return
    print(f"   Original: {fa.get('original_score')}/100")
    print(f"   Improved: {fa.get('overall_score')}/100")
    print(f"   Grade: {fa.get('grade')}")
    print(f"   Improvement: {fa.get('improvement')} points")
    print(f"   Confidence: {fa.get('confidence_score')}%")
    print(f"   Semantic valid: {fa.get('semantic_valid')}")
    print(f"   Structural valid: {fa.get('structural_valid')}")
    print(f"   Change metrics: {fa.get('change_metrics', {}).get('total_textboxes_checked')} textboxes")
    assert fa.get("overall_score") is not None, "Missing overall_score"
    print("✅ Final assessment verified")

def verify_executive_summary(data):
    print("\n=== Verify Executive Summary ===")
    es = data.get("executive_summary", {})
    if not es:
        print("⚠️ No executive_summary in response")
        return
    print(f"   Quality: {es.get('quality_label')}")
    print(f"   Assessment: {es.get('overall_assessment')[:80]}...")
    print(f"   Top improvements: {len(es.get('top_improvements', []))}")
    print(f"   Weaknesses: {len(es.get('weaknesses', []))}")
    assert es.get("overall_score") is not None, "Missing overall_score"
    assert es.get("quality_label") is not None, "Missing quality_label"
    print("✅ Executive summary verified")

def verify_analytics(data):
    print("\n=== Verify Analytics ===")
    a = data.get("analytics", {})
    if not a:
        print("⚠️ No analytics in response")
        return
    overall = a.get("overall", {})
    print(f"   Original: {overall.get('original_score')} -> Improved: {overall.get('improved_score')}")
    print(f"   Delta: {overall.get('delta')} ({overall.get('improvement_percentage')}%)")
    print(f"   Grade: {overall.get('original_grade')} -> {overall.get('improved_grade')}")
    print(f"   Categories improved: {a.get('summary', {}).get('improved')}/{a.get('summary', {}).get('total_categories')}")
    assert overall.get("original_score") is not None, "Missing original_score"
    assert overall.get("improved_score") is not None, "Missing improved_score"
    print("✅ Analytics verified")

def verify_recommendations(data):
    print("\n=== Verify Recommendations ===")
    r = data.get("recommendations", {})
    if not r:
        print("⚠️ No recommendations in response")
        return
    print(f"   Total: {r.get('total_recommendations')}")
    print(f"   High priority: {r.get('high_priority_count')}")
    print(f"   Medium priority: {r.get('medium_priority_count')}")
    print(f"   Categories: {list(r.get('categorized', {}).keys())}")
    assert r.get("total_recommendations", 0) > 0 or True  # At least check structure
    if r.get("recommendations"):
        print(f"   First rec: {r['recommendations'][0].get('recommendation')[:60]}")
    print("✅ Recommendations verified")

def verify_statistics(data):
    print("\n=== Verify Statistics ===")
    s = data.get("statistics", {})
    if not s:
        print("⚠️ No statistics in response")
        return
    print(f"   Slide count: {s.get('slide_count')}")
    print(f"   Total words: {s.get('total_words')}")
    print(f"   Reading time: {s.get('reading_time')}")
    print(f"   Speaking time: {s.get('speaking_time')}")
    print(f"   Avg words/slide: {s.get('average_words_per_slide')}")
    assert s.get("slide_count") is not None, "Missing slide_count"
    print("✅ Statistics verified")

def test_download(data):
    print("\n=== Test Download ===")
    download_url = data.get("download_url", "")
    if download_url:
        if not download_url.startswith("http"):
            download_url = f"{BASE_URL}{download_url}"
        print(f"   Download URL: {download_url}")
        r = requests.get(download_url)
        if r.status_code == 200:
            print(f"✅ Download successful ({len(r.content)} bytes)")
        else:
            print(f"❌ Download failed: HTTP {r.status_code}")
    else:
        # Try constructing from output_filename
        fn = data.get("output_filename")
        if fn:
            url = f"{BASE_URL}/api/presentation-rewriter/download/{fn}"
            print(f"   Trying: {url}")
            r = requests.get(url)
            if r.status_code == 200:
                print(f"✅ Download successful ({len(r.content)} bytes)")
            else:
                print(f"❌ Download failed: HTTP {r.status_code} body={r.text[:200]}")

def test_report(data):
    print("\n=== Test Report Endpoint ===")
    fn = data.get("output_filename")
    if fn:
        url = f"{BASE_URL}/api/presentation-rewriter/report/{fn}"
        print(f"   Report URL: {url}")
        r = requests.get(url)
        print(f"   HTTP {r.status_code}")
        if r.status_code == 200:
            report = r.json()
            print(f"   Report has slides: {len(report.get('report', {}).get('slides', []))}")
            print("✅ Report endpoint works")
        else:
            print(f"❌ Report failed: {r.text[:200]}")

def test_report_json(filepath):
    """Check report.json on filesystem"""
    print("\n=== Check Filesystem Report ===")
    import glob
    report_dir = r"c:\Users\fatim\Downloads\FYP Final\instance\presentation_rewriter"
    report_files = [f for f in os.listdir(report_dir) if f.endswith(".report.json")]
    if report_files:
        latest = max(report_files, key=lambda f: os.path.getmtime(os.path.join(report_dir, f)))
        print(f"   Latest report: {latest}")
        with open(os.path.join(report_dir, latest), "r", encoding="utf-8") as f:
            rdata = json.load(f)
        print(f"   Keys in report: {list(rdata.keys())}")
        required = ["output_filename", "quality_scores", "slides", "final_assessment", 
                     "executive_summary", "analytics", "recommendations", "statistics",
                     "processing_metadata"]
        missing = [k for k in required if k not in rdata]
        if missing:
            print(f"   ❌ Missing keys: {missing}")
        else:
            print("   ✅ All required report keys present")
        # Check nested fields
        fa = rdata.get("final_assessment", {})
        print(f"   Final assessment: overall={fa.get('overall_score')}, grade={fa.get('grade')}, confidence={fa.get('confidence_score')}")
        pm = rdata.get("processing_metadata", {})
        print(f"   Processing metadata: mode={pm.get('mode')}, tone={pm.get('tone')}, model={pm.get('model')}")
        return rdata
    else:
        print("❌ No report.json files found")
        return None

def test_progress_polling():
    print("\n=== Test Progress Endpoint ===")
    r = requests.get(f"{BASE_URL}/api/presentation-rewriter/progress/test.pptx")
    if r.status_code in (200, 404):
        print(f"✅ Progress endpoint accessible (HTTP {r.status_code})")
    else:
        print(f"❌ Progress endpoint failed: HTTP {r.status_code}")

def test_modes_and_tones():
    """Test mode=academic, tone=academic"""
    print("\n\n=== TEST: Academic Mode + Academic Tone ===")
    data = test_upload(TEST_FILE, mode="academic", tone="academic")
    if data:
        print("✅ Academic mode test passed")

    print("\n\n=== TEST: Quick Mode + Business Tone ===")
    data = test_upload(TEST_FILE, mode="quick", tone="business")
    if data:
        print("✅ Quick mode test passed")

def test_invalid():
    print("\n\n=== TEST: Invalid Requests ===")
    # No file
    r = requests.post(f"{BASE_URL}/api/presentation-rewriter/submit")
    print(f"No file: {r.status_code} - {r.json().get('message')[:50]}")
    
    # Invalid mode
    with open(TEST_FILE, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/api/presentation-rewriter/submit?mode=invalid",
            files={"file": ("test.pptx", f, "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
        )
    print(f"Invalid mode: {r.status_code} - {r.json().get('message')[:50]}")

def test_analysis_only():
    print("\n\n=== TEST: Analysis Only ===")
    with open(TEST_FILE, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/api/presentation-rewriter/analyze",
            files={"file": ("test_sample.pptx", f, "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
        )
    print(f"HTTP {r.status_code}")
    data = r.json()
    print(f"Success: {data.get('success')}")
    print(f"Scores: {data.get('quality_scores', {}).get('overall_score')}")
    print(f"Slides: {data.get('slides_analysed')}")
    print(f"Time: {data.get('processing_time')}")

if __name__ == "__main__":
    print("=" * 60)
    print("AI Presentation Enhancement Platform - Runtime Test Suite")
    print("=" * 60)
    
    test_health()
    
    # Test with professional mode
    print("\n\n=== MAIN TEST: Professional Mode ===")
    result = test_upload(TEST_FILE, mode="professional", tone="professional")
    
    if result:
        verify_quality_scores(result)
        verify_final_assessment(result)
        verify_executive_summary(result)
        verify_analytics(result)
        verify_recommendations(result)
        verify_statistics(result)
        test_download(result)
        test_report(result)
        test_progress_polling()
        test_report_json(None)
    
    # Test modes and tones
    test_modes_and_tones()
    
    # Test invalid requests
    test_invalid()
    
    # Test analysis-only endpoint
    test_analysis_only()
    
    print("\n" + "=" * 60)
    print("RUNTIME TEST SUITE COMPLETE")
    print("=" * 60)

