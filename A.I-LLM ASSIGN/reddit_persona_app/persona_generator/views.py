# persona_generator/views.py

import os
import re
import json
import praw
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Persona, PersonaCharacteristic

# Initialize Reddit API (PRAW)
# Ensure REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT are set in settings.py
reddit = praw.Reddit(
    client_id=settings.REDDIT_CLIENT_ID,
    client_secret=settings.REDDIT_CLIENT_SECRET,
    user_agent=settings.REDDIT_USER_AGENT
)

# Gemini API Configuration
GEMINI_API_KEY = settings.GEMINI_API_KEY
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def index(request):
    """
    Renders the homepage with the persona generation form and a list of past personas.
    """
    personas = Persona.objects.all().order_by('-generated_at')
    return render(request, 'persona_generator/index.html', {'personas': personas})

def persona_detail(request, pk):
    """
    Renders the detail page for a specific generated persona.
    """
    persona = get_object_or_404(Persona, pk=pk)
    # Parse citations from JSON string back to Python list/dict
    for char in persona.characteristics.all():
        try:
            char.parsed_citations = json.loads(char.citations)
        except json.JSONDecodeError:
            char.parsed_citations = [] # Handle malformed JSON
    return render(request, 'persona_generator/persona_detail.html', {'persona': persona})

@csrf_exempt # For simplicity in development, remove in production and use proper CSRF handling
def generate_persona(request):
    """
    Handles the persona generation request.
    Scrapes Reddit, calls LLM, and saves persona to DB.
    """
    if request.method == 'POST':
        reddit_url = request.POST.get('reddit_url')
        if not reddit_url:
            return JsonResponse({'status': 'error', 'message': 'Reddit URL is required.'}, status=400)

        # Extract username from URL
        match = re.search(r'reddit\.com/user/([^/]+)', reddit_url)
        if not match:
            return JsonResponse({'status': 'error', 'message': 'Invalid Reddit user URL.'}, status=400)
        username = match.group(1)

        # Check if persona already exists
        if Persona.objects.filter(reddit_username=username).exists():
            return JsonResponse({'status': 'error', 'message': f'Persona for {username} already exists. Please view existing or try a different user.'}, status=409)

        try:
            # Step 1: Scrape Reddit posts and comments using PRAW
            user_content = []
            redditor = reddit.redditor(username)

            # Fetch recent posts
            for submission in redditor.submissions.new(limit=20): # Limit to 20 recent posts
                user_content.append({
                    'type': 'post',
                    'url': f"https://www.reddit.com{submission.permalink}",
                    'text': submission.title + " " + submission.selftext,
                    'id': submission.id
                })

            # Fetch recent comments
            for comment in redditor.comments.new(limit=20): # Limit to 20 recent comments
                user_content.append({
                    'type': 'comment',
                    'url': f"https://www.reddit.com{comment.permalink}",
                    'text': comment.body,
                    'id': comment.id
                })

            if not user_content:
                return JsonResponse({'status': 'error', 'message': f'No recent public posts or comments found for u/{username}.'}, status=404)

            # Prepare content for LLM
            llm_input_content = ""
            content_map = {} # To easily retrieve original content for citations
            for i, item in enumerate(user_content):
                llm_input_content += f"--- Content ID: {item['id']} ({item['type']}) ---\n{item['text']}\n\n"
                content_map[item['id']] = item

            # Step 2: Call LLM (Gemini API) to build User Persona
            # We instruct the LLM to output JSON for easy parsing of characteristics and citations
            llm_prompt = f"""
            Analyze the following Reddit user's posts and comments to create a detailed user persona.
            For each characteristic in the persona, provide a citation (Content ID from the provided text) that supports it.

            Output the persona in JSON format with the following structure:
            {{
                "persona_summary": "Overall summary of the user persona.",
                "characteristics": [
                    {{
                        "trait": "Characteristic 1",
                        "description": "Description of characteristic 1.",
                        "supporting_content_ids": ["Content ID 1", "Content ID 2"]
                    }},
                    {{
                        "trait": "Characteristic 2",
                        "description": "Description of characteristic 2.",
                        "supporting_content_ids": ["Content ID 3"]
                    }}
                ]
            }}

            Reddit User Content for u/{username}:
            {llm_input_content}
            """

            headers = {
                'Content-Type': 'application/json'
            }
            payload = {
                "contents": [
                    {
                        "parts": [{"text": llm_prompt}]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }

            response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", headers=headers, json=payload)
            response.raise_for_status() # Raise an exception for HTTP errors
            llm_result = response.json()

            # Extract text from LLM response
            if llm_result and llm_result.get('candidates') and llm_result['candidates'][0].get('content') and llm_result['candidates'][0]['content'].get('parts'):
                llm_response_text = llm_result['candidates'][0]['content']['parts'][0]['text']
                persona_data = json.loads(llm_response_text) # Parse the JSON output from LLM
            else:
                raise ValueError("LLM response format unexpected.")

            # Step 3: Save Persona to Database
            new_persona = Persona.objects.create(
                reddit_username=username,
                persona_text=persona_data.get('persona_summary', 'No summary provided.')
            )

            for char_data in persona_data.get('characteristics', []):
                citations_list = []
                for content_id in char_data.get('supporting_content_ids', []):
                    original_item = content_map.get(content_id)
                    if original_item:
                        citations_list.append({
                            'url': original_item['url'],
                            'type': original_item['type'],
                            'snippet': original_item['text'][:150] + '...' if len(original_item['text']) > 150 else original_item['text']
                        })
                PersonaCharacteristic.objects.create(
                    persona=new_persona,
                    characteristic=f"{char_data.get('trait', '')}: {char_data.get('description', '')}",
                    citations=json.dumps(citations_list) # Store citations as JSON string
                )

            return JsonResponse({'status': 'success', 'persona_id': new_persona.pk, 'username': username})

        except praw.exceptions.PRAWException as e:
            return JsonResponse({'status': 'error', 'message': f'Reddit API Error: {e}. Please check username or API credentials.'}, status=500)
        except requests.exceptions.RequestException as e:
            return JsonResponse({'status': 'error', 'message': f'LLM API Connection Error: {e}.'}, status=500)
        except json.JSONDecodeError as e:
            return JsonResponse({'status': 'error', 'message': f'LLM response parsing error: {e}. LLM might not have returned valid JSON.'}, status=500)
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {e}'}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)