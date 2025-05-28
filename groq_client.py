import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def encode_image(image_path):
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    # Get file extension to determine MIME type
    file_ext = os.path.splitext(image_path)[1].lower()
    if file_ext in ['.jpg', '.jpeg']:
        mime_type = 'image/jpeg'
    elif file_ext == '.png':
        mime_type = 'image/png'
    elif file_ext == '.gif':
        mime_type = 'image/gif'
    elif file_ext == '.webp':
        mime_type = 'image/webp'
    else:
        mime_type = 'image/jpeg'  # default fallback
    
    return f"data:{mime_type};base64,{data}"

def get_groq_response(messages, image_path=None, model="meta-llama/llama-4-scout-17b-16e-instruct"):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Create a copy of messages to avoid modifying the original
    processed_messages = []
    
    # Process all messages except the last one normally (for conversation history)
    for msg in messages[:-1]:
        if isinstance(msg.get('content'), str):
            processed_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    # Handle the last message (current user message)
    if messages:
        last_message = messages[-1]
        if image_path and os.path.exists(image_path):
            # For vision models, structure the content as an array
            image_data_url = encode_image(image_path)
            processed_messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": last_message['content']
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        }
                    }
                ]
            })
        else:
            # Text-only message
            processed_messages.append({
                "role": last_message["role"],
                "content": last_message["content"]
            })
    
    payload = {
        "model": model,
        "messages": processed_messages,
        "max_completion_tokens": 1024,
        "temperature": 0.7,
        "top_p": 1,
        "stream": False
    }
    
    try:
        print(f"Using model: {model}")
        print(f"Sending {len(processed_messages)} messages to API")
        
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        
        # Debug: Print response details if there's an error
        if response.status_code != 200:
            print(f"Error Status Code: {response.status_code}")
            print(f"Error Response: {response.text}")
            
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response content: {response.text}")
        
        # Check if it's a model decommissioned error and suggest alternatives
        if "model_decommissioned" in response.text or "decommissioned" in response.text:
            return "Error: The vision model has been updated. Please check the latest Groq documentation for supported models."
        
        return f"Error: Unable to get response from Groq API. Status: {response.status_code}"
    except Exception as e:
        print(f"General error: {e}")
        return f"Error: {str(e)}"