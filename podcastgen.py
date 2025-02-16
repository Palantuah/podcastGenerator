import boto3
import openai
import requests
import os
import time
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

# Set your API keys from environment variables
eleven_labs_api_key = os.getenv("ELEVEN_LABS_API")
open_ai_key = os.getenv("API_OPENAI_KEY")
client = openai.OpenAI(open_ai_key)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

s3 = boto3.client("s3")

def update_supabase(newsletter_id, podcast_url):
    """Updates the Supabase database with the podcast URL."""
    url = f"{SUPABASE_URL}/rest/v1/newsletters?id=eq.{newsletter_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    data = json.dumps({"podcast_url": podcast_url})
    
    response = requests.patch(url, headers=headers, data=data)
    
    if response.status_code in [200, 204]:
        print("Supabase updated successfully!")
    else:
        print(f"Error updating Supabase: {response.text}")

def lambda_handler(event, context):
    try:
        # Parse event data (e.g., params)
        newsletter_id = event['newsletter_id']
        target_duration = event['target_duration']
        voice_id = event['voice_id']
        newsletter_text = event['newsletter_text']
        
        # Call your existing generate_monologue function here
        podcast_url = generate_monologue(newsletter_id, newsletter_text, target_duration, voice_id)

        # Return the podcast URL
        return {
            'statusCode': 200,
            'body': json.dumps({'podcast_url': podcast_url})
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_available_voices():
    """Get available voices from ElevenLabs API"""
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {
        "Accept": "application/json",
        "xi-api-key": eleven_labs_api_key
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        voices = response.json()["voices"]
        return [(voice["voice_id"], voice["name"]) for voice in voices]
    else:
        print(f"Error fetching voices: {response.status_code}")
        return []

def save_to_s3(file_path, s3_key):
    """Uploads podcast file to AWS S3 and returns its URL."""
    with open(file_path, "rb") as file:
        s3.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=file)
    
    return f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

def generate_monologue(newsletter_id, newsletter_text, target_duration_minutes, voice):
    """
    Generates a monologue podcast script from the provided newsletter text.
    The monologue is tailored to fit approximately target_duration_minutes (assuming ~150 words/minute).
    It then converts the script to speech using Eleven Labs TTS and saves both audio and transcript.
    """
    target_word_count = target_duration_minutes * 150  # Approximation

    # Create the prompt for GPT-4
    prompt = (
        f"Your name is Axon. Using the newsletter content below, generate an informative monologue podcast script."
        f"The final script should be written in natural spoken language suitable for text-to-speech conversion and "
        f"should fit within approximately {target_duration_minutes} minutes (around {target_word_count} words). "
        f"Make sure to include smooth transitions between topics, and cover all key points from the newsletter.\n\n"
        f"Newsletter Content:\n{newsletter_text}"
    )

    # Generate the monologue script using GPT-4
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "YOUR SCRIPT WRITING INSTRUCTIONS HERE"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    monologue_text = response.choices[0].message.content

    # Save the transcript to a file in /tmp
    transcript_dir = "/tmp/Podcast_textfile"
    os.makedirs(transcript_dir, exist_ok=True)
    transcript_path = os.path.join(transcript_dir, "Podcast_Transcript.txt")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(monologue_text)

    # Request TTS conversion using Eleven Labs
    tts_response = requests.post("YOUR_ELEVEN_LABS_URL", json={})
    audio_path = "/tmp/Final_Audio/podcast.mp3"
    with open(audio_path, "wb") as f:
        f.write(tts_response.content)

    # Upload to S3
    s3_key = f"podcasts/newsletter_{newsletter_id}.mp3"
    podcast_url = save_to_s3(audio_path, s3_key)

    # Update Supabase with podcast URL
    update_supabase(newsletter_id, podcast_url)

    return podcast_url


# # Example usage:
# if __name__ == "__main__":
#     # Load your comprehensive newsletter content from a file
#     with open("newsletter.txt", "r", encoding="utf-8") as f:
#         newsletter_text = f.read()

#     target_duration = 10  # e.g., 10 minutes podcast
#     voice_id = "pqHfZKP75CvOlQylNhV4"  # Bill - American, trustworthy voice
    
#     transcript, audio_file = generate_monologue(newsletter_text, target_duration, voice_id)
#     print("Podcast generation complete!")
#     print(f"Transcript saved at: {os.path.abspath('Podcast_textfile/Podcast_Transcript.txt')}")
#     print(f"Audio saved at: {os.path.abspath(audio_file)}")
