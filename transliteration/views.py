from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os
import tempfile
import easyocr
from PIL import Image, ImageEnhance, ImageFilter
from langdetect import detect
from aksharamukha.transliterate import process
import json
import cv2
import numpy as np
from .formatters import formatter

# Initialize EasyOCR reader globally (to prevent reloading on every request)
# Using Hindi + English for better Hindi text detection
reader = easyocr.Reader(['hi', 'en'], gpu=False)

# Create your views here.


def preprocess_image_for_ocr(image_path):
    """
    Preprocess image to improve OCR accuracy
    """
    try:
        # Read image with OpenCV
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Could not read image")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply different preprocessing techniques
        processed_images = []
        
        # 1. Original grayscale
        processed_images.append(gray)
        
        # 2. Gaussian blur + threshold
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        thresh1 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        processed_images.append(thresh1)
        
        # 3. Adaptive threshold
        adaptive_thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        processed_images.append(adaptive_thresh)
        
        # 4. Morphological operations
        kernel = np.ones((1, 1), np.uint8)
        morph = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel)
        processed_images.append(morph)
        
        # 5. Denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        processed_images.append(denoised)
        
        # 6. Contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        processed_images.append(enhanced)
        
        return processed_images
        
    except Exception as e:
        print(f"Image preprocessing failed: {e}")
        # Return PIL Image as fallback
        try:
            pil_image = Image.open(image_path).convert('L')
            # Convert PIL to numpy array for consistency
            numpy_image = np.array(pil_image)
            return [numpy_image]
        except Exception as e2:
            print(f"Fallback image loading also failed: {e2}")
            return None

@api_view(['POST'])
def transliterate_image(request):
    """
    API endpoint to process uploaded image, extract text using EasyOCR,
    detect language, and transliterate to multiple Indian scripts.
    """
    try:
        # Check if image file is provided
        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image_file = request.FILES['image']
        
        # Validate file type
        if not image_file.content_type.startswith('image/'):
            return Response(
                {'error': 'Invalid file type. Please upload an image.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            # Write uploaded file to temporary location
            for chunk in image_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        try:
            # Extract text using EasyOCR
            # Load image for EasyOCR processing
            image = Image.open(temp_file_path)
            image_np = np.array(image)
            
            # Use EasyOCR to extract text
            results = reader.readtext(image_np)
            
            # Extract text from results and combine
            extracted_text = " ".join([text for (_, text, _) in results])
            
            # Clean up the text (remove extra whitespace, newlines)
            extracted_text = ' '.join(extracted_text.split())
            
            # If no text extracted, return error
            if not extracted_text:
                return Response(
                    {'error': 'No text could be extracted from the image. Please ensure the image contains clear, readable text.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Detect language
            try:
                detected_language = detect(extracted_text)
            except:
                detected_language = 'unknown'
            
            # Language code to script mapping for Aksharamukha
            language_to_script = {
                'hi': 'Devanagari',    # Hindi
                'mr': 'Devanagari',    # Marathi (uses Devanagari script)
                'ta': 'Tamil',         # Tamil
                'te': 'Telugu',        # Telugu
                'kn': 'Kannada',       # Kannada
                'ml': 'Malayalam',     # Malayalam
                'gu': 'Gujarati',      # Gujarati
                'bn': 'Bengali',       # Bengali
                'pa': 'Gurmukhi',      # Punjabi
                'or': 'Oriya',         # Odia
                'as': 'Bengali',       # Assamese (using Bengali script)
                'en': 'ITRANS',        # English (use ITRANS for transliteration)
            }
            
            # Determine source script - for English text, use ITRANS as source
            if detected_language == 'en' or not detected_language or detected_language == 'unknown':
                source_script = 'ITRANS'
            else:
                source_script = language_to_script.get(detected_language, 'ITRANS')
            
            # Target scripts for transliteration
            target_scripts = {
                'Devanagari (Hindi)': 'Devanagari',
                'Devanagari (Marathi)': 'Devanagari',
                'Tamil': 'Tamil',
                'Telugu': 'Telugu',
                'Kannada': 'Kannada',
                'Malayalam': 'Malayalam',
                'Gujarati': 'Gujarati',
                'Bengali': 'Bengali',
                'Gurmukhi': 'Gurmukhi',
                'Oriya': 'Oriya',
                'Roman': 'ITRANS'
            }
            
            # Perform transliteration to all target scripts
            transliterations = {}
            for script_name, script_code in target_scripts.items():
                try:
                    # For English text, we need special handling
                    if detected_language == 'en' or not detected_language or detected_language == 'unknown':
                        # Convert English text directly to target script using Aksharamukha
                        if script_code == 'ITRANS':
                            # For ITRANS/Roman, keep the original text
                            transliterated_text = extracted_text
                        else:
                            # For Indian scripts, perform direct transliteration using Aksharamukha
                            transliterated_text = process('ITRANS', script_code, extracted_text)
                    else:
                        # For other languages, use standard transliteration
                        transliterated_text = process(source_script, script_code, extracted_text)
                    
                    # Apply formatting for better readability
                    formatted_text = formatter.clean_transliteration(
                        transliterated_text, 
                        script_code
                    )
                    transliterations[script_name] = formatted_text
                except Exception as e:
                    print(f"Transliteration failed for {script_name}: {e}")
                    # If transliteration fails, try a fallback approach
                    try:
                        # Try direct transliteration from ITRANS
                        transliterated_text = process('ITRANS', script_code, extracted_text)
                        formatted_text = formatter.clean_transliteration(
                            transliterated_text, 
                            script_code
                        )
                        transliterations[script_name] = formatted_text
                    except Exception as e2:
                        print(f"Fallback transliteration also failed for {script_name}: {e2}")
                        # If all else fails, use original text
                        transliterations[script_name] = extracted_text
            
            # Prepare response
            response_data = {
                'original_text': extracted_text,
                'detected_language': detected_language,
                'transliterations': transliterations
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
            return Response(
                {'error': f'An error occurred while processing the image: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['POST'])
def transliterate_single(request):
    """
    API endpoint for single target transliteration with source language correction.
    """
    try:
        # Check if image file is provided
        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get source and target languages
        source_language = request.POST.get('source_language', 'hi')
        target_language = request.POST.get('target_language', 'en')
        
        image_file = request.FILES['image']
        
        # Validate file type
        if not image_file.content_type.startswith('image/'):
            return Response(
                {'error': 'Invalid file type. Please upload an image.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            # Write uploaded file to temporary location
            for chunk in image_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        try:
            # Extract text using EasyOCR
            # Load image for EasyOCR processing
            image = Image.open(temp_file_path)
            image_np = np.array(image)
            
            # Use EasyOCR to extract text
            results = reader.readtext(image_np)
            
            # Extract text from results and combine
            extracted_text = " ".join([text for (_, text, _) in results])
            
            # Clean up the text (remove extra whitespace, newlines)
            extracted_text = ' '.join(extracted_text.split())
            
            # If no text extracted, return error
            if not extracted_text:
                return Response(
                    {'error': 'No text could be extracted from the image. Please ensure the image contains clear, readable text.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Detect the actual language of the extracted text
            try:
                detected_language = detect(extracted_text)
            except:
                detected_language = source_language  # Fallback to user selection
            
            
            # Language code to script mapping for Aksharamukha
            language_to_script = {
                'hi': 'Devanagari',    # Hindi
                'mr': 'Devanagari',    # Marathi (uses Devanagari script)
                'ta': 'Tamil',         # Tamil
                'te': 'Telugu',        # Telugu
                'kn': 'Kannada',       # Kannada
                'ml': 'Malayalam',     # Malayalam
                'gu': 'Gujarati',      # Gujarati
                'bn': 'Bengali',       # Bengali
                'pa': 'Gurmukhi',      # Punjabi
                'or': 'Oriya',         # Odia
                'as': 'Bengali',       # Assamese (using Bengali script)
                'en': 'ITRANS',        # English (use ITRANS for transliteration)
            }
            
            # Use detected language if it's more reliable, otherwise use user selection
            # For English detection, prioritize user selection if they specifically chose English
            if detected_language == 'en' or source_language == 'en':
                actual_source_language = 'en'
            else:
                actual_source_language = detected_language if detected_language != 'unknown' else source_language
            
            # Get source and target scripts
            source_script = language_to_script.get(actual_source_language, 'Devanagari')
            target_script = language_to_script.get(target_language, 'ITRANS')
            
            
            # Perform single transliteration
            try:
                # For English text, we need special handling
                if actual_source_language == 'en':
                    # Convert English text directly to target script using Aksharamukha
                    if target_script == 'ITRANS':
                        # For ITRANS/Roman, keep the original text
                        transliterated_text = extracted_text
                    else:
                        # For Indian scripts, perform direct transliteration using Aksharamukha
                        raw_transliterated = process('ITRANS', target_script, extracted_text)
                        # Apply formatting for better readability
                        transliterated_text = formatter.clean_transliteration(
                            raw_transliterated, 
                            target_script
                        )
                else:
                    # For other languages, use standard transliteration
                    raw_transliterated = process(source_script, target_script, extracted_text)
                    # Apply formatting for better readability
                    transliterated_text = formatter.clean_transliteration(
                        raw_transliterated, 
                        target_script
                    )
                
            except Exception as e:
                print(f"Single transliteration failed: {e}")
                # Try fallback approach
                try:
                    raw_transliterated = process('ITRANS', target_script, extracted_text)
                    transliterated_text = formatter.clean_transliteration(
                        raw_transliterated, 
                        target_script
                    )
                except Exception as e2:
                    print(f"Fallback single transliteration also failed: {e2}")
                    # If both attempts fail, it's likely due to garbled OCR output
                    # Return an error message instead of the garbled text
                    transliterated_text = f"[Transliteration failed: OCR output appears to be garbled. Original: {extracted_text[:50]}...]"
            
            # Also generate all transliterations for comparison
            target_scripts = {
                'Devanagari (Hindi)': 'Devanagari',
                'Devanagari (Marathi)': 'Devanagari',
                'Tamil': 'Tamil',
                'Telugu': 'Telugu',
                'Kannada': 'Kannada',
                'Malayalam': 'Malayalam',
                'Gujarati': 'Gujarati',
                'Bengali': 'Bengali',
                'Gurmukhi': 'Gurmukhi',
                'Oriya': 'Oriya',
                'Roman': 'ITRANS'
            }
            
            # Generate all transliterations
            all_transliterations = {}
            for script_name, script_code in target_scripts.items():
                try:
                    # For English text, we need special handling
                    if actual_source_language == 'en':
                        # Convert English text directly to target script using Aksharamukha
                        if script_code == 'ITRANS':
                            # For ITRANS/Roman, keep the original text
                            multi_transliterated_text = extracted_text
                        else:
                            # For Indian scripts, perform direct transliteration using Aksharamukha
                            multi_transliterated_text = process('ITRANS', script_code, extracted_text)
                    else:
                        # For other languages, use standard transliteration
                        multi_transliterated_text = process(source_script, script_code, extracted_text)
                    
                    # Apply formatting for better readability
                    formatted_text = formatter.clean_transliteration(
                        multi_transliterated_text, 
                        script_code
                    )
                    all_transliterations[script_name] = formatted_text
                except Exception as e:
                    print(f"Transliteration failed for {script_name}: {e}")
                    # If transliteration fails, try a fallback approach
                    try:
                        # Try direct transliteration from ITRANS
                        multi_transliterated_text = process('ITRANS', script_code, extracted_text)
                        formatted_text = formatter.clean_transliteration(
                            multi_transliterated_text, 
                            script_code
                        )
                        all_transliterations[script_name] = formatted_text
                    except Exception as e2:
                        print(f"Fallback transliteration also failed for {script_name}: {e2}")
                        # If all else fails, use original text
                        all_transliterations[script_name] = extracted_text
            
            # Prepare response
            response_data = {
                'original_text': extracted_text,
                'detected_language': actual_source_language,
                'target_language': target_language,
                'transliterated_text': transliterated_text,
                'all_transliterations': all_transliterations
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        return Response(
            {'error': f'An error occurred while processing the image: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
