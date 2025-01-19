from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext as _
from googletrans import Translator
from .models import Blog
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
import pydub
from pydub.utils import mediainfo
from pydub import AudioSegment
import whisper
import os
import cv2
import numpy as np
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
import random
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
import speech_recognition as sr
import tempfile
import subprocess
import moviepy

translator = Translator()

# Define supported languages
SUPPORTED_LANGUAGES = {
    'hi': 'Hindi',
    'bn': 'Bengali',
    'te': 'Telugu',
    'ta': 'Tamil',
    'mr': 'Marathi',
    'gu': 'Gujarati',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'pa': 'Punjabi',
    'or': 'Odia'
}

def upload_page(request):
    if request.method == 'POST':
        text_file = request.FILES.get('textFile')
        video_file = request.FILES.get('videoFile')
        uploaded_files = {}
        
        if text_file:
            try:
                fs = FileSystemStorage(location='uploads/')
                
                # Ensure uploads directory exists
                os.makedirs('uploads/', exist_ok=True)
                
                filename = fs.save(text_file.name, text_file)
                uploaded_files['text'] = filename
                
                # Verify file was saved
                file_path = fs.path(filename)
                if not os.path.exists(file_path):
                    return HttpResponse(f"Error: File failed to save at {file_path}")
                    
                # Verify file is readable
                with open(file_path, 'r', encoding='utf-8') as file:
                    text_content = file.read()
                    if not text_content:
                        return HttpResponse("Warning: Saved file is empty")
                
                print(f"File uploaded successfully: {file_path}")  # Debug print
                print(f"Content length: {len(text_content)}")      # Debug print
                
                return redirect('preview_text', filename=filename)
                
            except Exception as e:
                return HttpResponse(f"Upload error: {str(e)}")
            
        if video_file:
            fs = FileSystemStorage(location='uploads/')
            filename = fs.save(video_file.name, video_file)
            uploaded_files['video'] = filename
            
        request.session['uploaded_files'] = uploaded_files
        return redirect('process_files')
        
    return render(request, 'blogs/upload_page.html', {'error': None})

def preview_text(request, filename):
    try:
        fs = FileSystemStorage(location='uploads/')
        file_path = fs.path(filename)
        
        print(f"Attempting to read file: {file_path}")  # Debug print
        
        if not os.path.exists(file_path):
            return HttpResponse(f"Error: File {filename} not found at {file_path}")
        
        if request.method == 'POST':
            # Save the edited content
            edited_content = request.POST.get('content', '')
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(edited_content)
                
            # Store filename in session and redirect to process page
            uploaded_files = {'text': filename}
            request.session['uploaded_files'] = uploaded_files
            return redirect('process_files')
        
        # Read the content for preview
        with open(file_path, 'r', encoding='utf-8') as file:
            text_content = file.read()
            
        print(f"Content length: {len(text_content)}")  # Debug print
        
        if not text_content:
            return HttpResponse("Warning: File is empty")
            
        context = {
            'filename': filename,
            'content': text_content,
        }
        print(f"Context content length: {len(context['content'])}")  # Debug print
        return render(request, 'blogs/preview_text.html', context)
        
    except Exception as e:
        return HttpResponse(f"Error reading file: {str(e)}")

def process_files(request):
    uploaded_files = request.session.get('uploaded_files', {})
    
    if request.method == 'POST':
        action = request.POST.get('action')
        language = request.POST.get('language')
        
        if action == 'translate' and language:
            return redirect('translation_result', lang_code=language)
        elif action == 'transcribe':
            return redirect('transcription_result')
    
    context = {
        'supported_languages': SUPPORTED_LANGUAGES,
        'has_text_file': 'text' in uploaded_files,
        'has_video_file': 'video' in uploaded_files,
    }
    return render(request, 'blogs/process_files.html', context)

def translation_result(request, lang_code):
    uploaded_files = request.session.get('uploaded_files', {})
    results = {}
    
    try:
        # Handle text file translation
        if 'text' in uploaded_files:
            fs = FileSystemStorage(location='uploads/')
            file_path = fs.path(uploaded_files['text'])
            
            with open(file_path, 'r', encoding='utf-8') as file:
                text_content = file.read()
                
            translated_text = translator.translate(text_content, dest=lang_code).text
            results['text_translation'] = translated_text
            
            # Save translated text to a new file
            translated_filename = f"translated_{uploaded_files['text']}"
            with open(fs.path(translated_filename), 'w', encoding='utf-8') as f:
                f.write(translated_text)
            results['translated_file'] = translated_filename
            
        context = {
            'results': results,
            'target_language': SUPPORTED_LANGUAGES.get(lang_code),
            'source_language': 'English'
        }
        return render(request, 'blogs/translation_result.html', context)
        
    except Exception as e:
        context = {
            'error': f"Translation error: {str(e)}",
            'target_language': SUPPORTED_LANGUAGES.get(lang_code)
        }
        return render(request, 'blogs/translation_result.html', context)
    

def extract_audio_from_video(video_path, audio_path):
    try:
        # Load the video file
        video = moviepy.VideoFileClip(video_path)
        
        # Extract the audio from the video
        audio = video.audio
        
        # Write the audio to a file (WAV format)
        audio.write_audiofile(audio_path)
        print(f"Audio extracted and saved as {audio_path}")
    except Exception as e:
        print(f"Error extracting audio: {e}")
        raise

def transcribe_audio(audio_file_path):
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_file_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)  # Uses Google Speech API
        return text
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None


            
def transcription_result(request):
    uploaded_files = request.session.get('uploaded_files', {})
    results = {}
    
    try:
        if 'video' in uploaded_files:
            fs = FileSystemStorage(location='uploads/')
            video_path = fs.path(uploaded_files['video'])
            
            # Create a temporary WAV file for audio
            temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_audio_path = temp_audio.name
            temp_audio.close()

            # Extract audio using moviepy
            extract_audio_from_video(video_path, temp_audio_path)

            # Transcribe the audio using Whisper
            transcribed_text = transcribe_audio(temp_audio_path)
            
            if transcribed_text:
                results['full_transcript'] = transcribed_text
            else:
                results['error'] = "Could not transcribe the audio."
            
            # Clean up the temporary audio file
            os.unlink(temp_audio_path)

        context = {
            'results': results
        }
        return render(request, 'blogs/transcription_result.html', context)
        
    except Exception as e:
        context = {
            'error': f"Transcription error: {str(e)}"
        }
        return render(request, 'blogs/transcription_result.html', context)
    
def blog_list(request):
    blogs = Blog.objects.all()
    return render(request, 'blogs/blog_list.html', {'blogs': blogs})

def blog_detail(request, blog_id, lang_code='en'):
    blog = get_object_or_404(Blog, id=blog_id)
    translated_title = blog.title
    translated_content = blog.content
    
    if lang_code != 'en':
        try:
            translated_title = translator.translate(blog.title, dest=lang_code).text
            translated_content = translator.translate(blog.content, dest=lang_code).text
        except Exception as e:
            translated_content = f"Error: {e}"
            
    context = {
        'blog': blog,
        'translated_title': translated_title,
        'translated_content': translated_content,
        'lang_code': lang_code,

    }
    return render(request, 'blogs/blog_detail.html', context)












































































































