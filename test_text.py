from google import genai

client = genai.Client()

response = client.models.generate_content(
    model="gemma-4-26b-a4b-it",
    contents="Write a two-line spooky poem about a haunted computer lab.",
)

print(response.text)