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
client = openai.OpenAI(api_key=os.getenv("API_OPENAI_KEY"))

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


def generate_monologue(newsletter_text, target_duration_minutes, voice):
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
            {"role": "system", "content": "YOU ARE AN INFORMATIVE PODCAST SCRIPT WRITER. WRITE IN PURE SPOKEN FORM WITHOUT ANY FORMATTING MARKS OR SECTION HEADERS.\n\nSCRIPT FORMAT:\nWrite in pure spoken text without any brackets, section markers, or audio cues. Never use [Introduction], [Segment 1], or similar markers. Never include stage directions or audio instructions. Create natural verbal transitions between topics without explicitly marking sections. Write exactly as it should be spoken.\n\nINFORMATION STRUCTURE:\nPresent key insights first. Layer supporting evidence systematically. Connect related concepts before introducing new ones. Build logical progressions of ideas. Create natural conceptual bridges.\n\nLANGUAGE AND FLOW:\nUse clear, direct statements. State relationships between concepts explicitly. Vary sentence length for natural rhythm. Prioritize active voice. Explain technical terms in context. Transform data points into clear insights.\n\nTOPIC PROGRESSION:\nBegin with foundational concepts. Layer in supporting details methodically. Draw connections between related elements. Highlight significant patterns. Emphasize cause-and-effect relationships. Build complexity gradually.\n\nENGAGEMENT APPROACH:\nMaintain flow through logical connections. Highlight key implications of data. Connect abstract concepts to concrete outcomes. Use precise language and specific examples. Create natural pause points between major concepts.\n\nAVOID THESE ELEMENTS:\nArtificial enthusiasm or forced personality. Unnecessary anecdotes or asides. Over-explanation of basic concepts. Repetition without new context. Casual conversation fillers. News-style delivery. Corporate jargon. Any form of formatting marks or section headers.\n\nREQUIRED IN EACH SECTION:\nClear thesis statement. Supporting evidence and context. Specific data points with meaning. Logical bridges between concepts. Clear implications of information.\n\nREMEMBER: Your goal is pure information transfer through clear, logical progression. Write exactly as the words should be spoken, with no formatting or markers. Focus on knowledge delivery through natural language flow rather than entertainment or personality. Maintain engagement through structure and clarity, not artificial personality elements."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        presence_penalty=0.0,
    )
    monologue_text = response.choices[0].message.content

    # Save the transcript to a file
    transcript_dir = "Podcast_textfile"
    os.makedirs(transcript_dir, exist_ok=True)
    transcript_path = os.path.join(transcript_dir, "Podcast_Transcript.txt")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(monologue_text)

    # Prepare request to Eleven Labs TTS
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": eleven_labs_api_key,
    }
    data = {
        "text": monologue_text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
    }

    # Request TTS conversion
    tts_response = requests.post(url, json=data, headers=headers)
    if tts_response.status_code != 200:
        print(f"Error with ElevenLabs API: Status {tts_response.status_code}")
        print(f"Response: {tts_response.text}")
        # In case of an error, wait and try with alternative voice settings
        time.sleep(30)
        data["model_id"] = "eleven_multilingual_v2"
        data["voice_settings"] = {"stability": 0.7, "similarity_boost": 0.75}
        tts_response = requests.post(url, json=data, headers=headers)
        if tts_response.status_code != 200:
            print(f"Second attempt failed: Status {tts_response.status_code}")
            print(f"Response: {tts_response.text}")
            raise Exception("Failed to generate audio with ElevenLabs API")

    # Check response size before saving
    content_length = len(tts_response.content)
    print(f"Received audio size: {content_length} bytes")
    if content_length < 1000:  # Audio files should be much larger
        print(f"Warning: Audio file seems too small. Response content: {tts_response.text}")
        raise Exception("Generated audio file is suspiciously small")

    # Save the audio file
    audio_dir = "Final_Audio"
    os.makedirs(audio_dir, exist_ok=True)
    audio_path = os.path.join(audio_dir, "podcast.mp3")
    with open(audio_path, "wb") as f:
        for chunk in tts_response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    return monologue_text, audio_path

# Example usage:
if __name__ == "__main__":
    # Load your comprehensive newsletter content from a file
    with open("newsletter.txt", "r", encoding="utf-8") as f:
        newsletter_text = f.read()

    target_duration = 10  # e.g., 10 minutes podcast
    voice_id = "pqHfZKP75CvOlQylNhV4"  # Bill - American, trustworthy voice
    
    transcript, audio_file = generate_monologue(newsletter_text, target_duration, voice_id)
    print("Podcast generation complete!")
    print(f"Transcript saved at: {os.path.abspath('Podcast_textfile/Podcast_Transcript.txt')}")
    print(f"Audio saved at: {os.path.abspath(audio_file)}")
