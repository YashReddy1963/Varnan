#!/usr/bin/env python3
"""
Simple test script to verify the transliteration API is working correctly.
"""

import requests
import json
import os

def test_api():
    """Test the transliteration API endpoint."""
    
    # Create a simple test image (you can replace this with an actual image path)
    test_image_path = "/home/yashreddy/Documents/dev/varnan/test_image.jpg"
    
    # Check if test image exists
    if not os.path.exists(test_image_path):
        print("❌ Test image not found. Please create a test image at:", test_image_path)
        print("   You can use any image with text for testing.")
        return False
    
    try:
        # Test the API endpoint
        url = "http://localhost:8000/api/transliterate-image/"
        
        with open(test_image_path, 'rb') as f:
            files = {'image': ('test_image.jpg', f, 'image/jpeg')}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Test Successful!")
            print("📝 Original Text:", data.get('original_text', 'N/A'))
            print("🌍 Detected Language:", data.get('detected_language', 'N/A'))
            print("🔄 Transliterations:")
            
            for script, text in data.get('transliterations', {}).items():
                print(f"   {script}: {text}")
            
            return True
        else:
            print(f"❌ API Test Failed! Status Code: {response.status_code}")
            print("Response:", response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the Django server is running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Varnan Transliteration API...")
    print("=" * 50)
    
    # Check if Django server is running
    try:
        response = requests.get("http://localhost:8000/admin/")
        print("✅ Django server is running")
    except:
        print("❌ Django server is not running. Please start it with:")
        print("   cd varnan-backend && source venv/bin/activate && python manage.py runserver")
        exit(1)
    
    print()
    test_api()
