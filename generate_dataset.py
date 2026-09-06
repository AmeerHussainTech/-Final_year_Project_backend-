import os
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai

# Load env variables
load_dotenv()

# Configure Gemini
# The user's actual workspace env contains the API key.
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY or GEMINI_API_KEY == 'your-gemini-api-key-here':
    print("[ERROR] GEMINI_API_KEY not found or default placeholder used in .env file.", flush=True)
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

def generate_synthetic_data():
    """
    Generate diverse presentation slide transcripts and evaluations using Gemini.
    Generates 100 samples across 5 contexts and different quality levels.
    """
    print("[START] Starting expert multi-context synthetic dataset generation (rate-limit safe)...", flush=True)
    
    model = genai.GenerativeModel('gemini-3.6-flash')
    
    dataset = []
    
    qualities = ["excellent", "good", "average", "poor"]
    contexts = [
        "Academic Thesis Defense",
        "Sales Pitch",
        "Corporate Business Proposal",
        "Technical Architecture Review",
        "Educational Lecture"
    ]
    
    batch_size = 4  # 4 samples per API request
    total_needed = 40
    batches = total_needed // batch_size
    
    for b in range(batches):
        context = contexts[b % len(contexts)]
        target_quality = qualities[b % len(qualities)]
        
        print(f"[BATCH] Generating batch {b+1}/{batches} (Context: {context}, Target Quality: {target_quality})...", flush=True)
        
        prompt = f"""
        Generate exactly {batch_size} realistic presentation transcripts/slide texts in the context of: '{context}'.
        Each transcript must target a different level of quality: targeting a '{target_quality}' presentation, but make sure we get a wide variety of quality levels across the samples.
        
        For each sample, output the text (usually 3-5 slides with headers and bullet points) and a detailed evaluation matching this JSON structure:
        {{
          "samples": [
            {{
              "text": "<Complete transcript of slides, with slide headers and content>",
              "context": "<One of the five contexts mentioned above>",
              "scores": {{
                "Structure": <integer 10-100 based on slide logic, intro, and agenda>,
                "Clarity": <integer 10-100 based on sentence simplicity>,
                "Persuasion": <integer 10-100 based on argumentation>,
                "Content_Quality": <integer 10-100 based on depth>,
                "Call_to_Action": <integer 10-100 based on concluding statements>,
                "Grammar_and_Syntax": <integer 10-100 based on typos and grammar errors>,
                "Accuracy": <integer 10-100 based on correctness>,
                "Tone_Appropriateness": <integer 10-100 based on professional tone>,
                "Audience_Alignment": <integer 10-100 based on suitability>,
                "Purpose_Fulfillment": <integer 10-100 based on clear outcomes>,
                "overall_score": <integer 10-100 based on the average of all score metrics>
              }},
              "seven_cs": {{
                "Clear": <1 for Passed, 0 for Needs Improvement>,
                "Concise": <1 for Passed, 0 for Needs Improvement>,
                "Correct": <1 for Passed, 0 for Needs Improvement>,
                "Complete": <1 for Passed, 0 for Needs Improvement>,
                "Courteous": <1 for Passed, 0 for Needs Improvement>,
                "Concrete": <1 for Passed, 0 for Needs Improvement>,
                "Consistent": <1 for Passed, 0 for Needs Improvement>
              }}
            }}
          ]
        }}
        
        Return ONLY a single valid JSON object. Do not wrap in markdown backticks. Make the slide texts very realistic: some with lots of filler words (um, like, basically), some with poor formatting, some with excellent citations.
        """
        
        retries = 5
        while retries > 0:
            try:
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                res_json = json.loads(response.text)
                samples = res_json.get("samples", [])
                
                if len(samples) > 0:
                    dataset.extend(samples)
                    print(f"   [SUCCESS] Batch {b+1} complete. Total samples: {len(dataset)}", flush=True)
                    break
                else:
                    retries -= 1
                    time.sleep(5)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
                    print(f"   [WARN] Rate limit (429) hit. Waiting 65s for reset...", flush=True)
                    time.sleep(65)
                else:
                    print(f"   [WARN] Error during generation: {err_str}. Retrying...", flush=True)
                    retries -= 1
                    time.sleep(5)
        
        # Sleep 8 seconds between requests to guarantee staying under the RPM rate limit
        time.sleep(8)

    os.makedirs('instance', exist_ok=True)
    with open('instance/synthetic_dataset.json', 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2)
        
    print(f"[DONE] Successfully generated {len(dataset)} samples and saved to instance/synthetic_dataset.json", flush=True)

if __name__ == "__main__":
    generate_synthetic_data()
