import requests
import sys
import traceback
import json

url = 'http://localhost:5000/api/presentation-rewriter/submit'
try:
    with open('test_sample.pptx', 'rb') as f:
        files = {'file': ('test_sample.pptx', f, 'application/vnd.openxmlformats-officedocument.presentationml.presentation')}
        data = {'mode': 'professional', 'tone': 'professional'}
        resp = requests.post(url, files=files, data=data, timeout=300)
        print('STATUS:', resp.status_code)
        try:
            print('RESPONSE:', json.dumps(resp.json(), indent=2)[:3000])
        except Exception:
            print('RESPONSE:', resp.text[:2000])
except Exception as e:
    traceback.print_exc()
    print('ERROR:', str(e))
