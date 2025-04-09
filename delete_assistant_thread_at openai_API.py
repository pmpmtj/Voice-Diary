


from openai import OpenAI
client = OpenAI()

response = client.beta.threads.delete("thread_...")
print(response)