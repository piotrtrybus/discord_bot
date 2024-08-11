import discord
from quart import Quart, request, jsonify, Response
import asyncio
import os
from dotenv import load_dotenv
import hypercorn.asyncio
from hypercorn.config import Config
import base64

load_dotenv()

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True  # Ensure you have the intent to fetch members

client = discord.Client(intents=intents)

# Initialize Quart app
app = Quart(__name__)

def check_auth(auth_header):
    if not auth_header:
        return False

    try:
        auth_type, credentials = auth_header.split(" ")
        if auth_type.lower() != "basic":
            return False

        decoded_credentials = base64.b64decode(credentials).decode("utf-8")
        username, password = decoded_credentials.split(":")

        # Replace 'your_username' and 'your_password' with actual credentials
        return username == "p_trybus" and password == "auth123"
    except Exception as e:
        print(f"[ERROR] Invalid authentication format: {e}")
        return False

@app.route('/webhook', methods=['POST'])
async def webhook():
    auth_header = request.headers.get('Authorization')
    if not check_auth(auth_header):
        return Response("Unauthorized", status=401)

    data = await request.get_json()
    user_id = data.get('user_id')
    message_content = data.get('message', 'Hello World')  # Default to 'Hello World' if no message is provided
    if user_id:
        # Schedule the send_dm coroutine in the event loop
        asyncio.create_task(send_dm(user_id, message_content))
    return '', 200

async def send_dm(user_id, content):
    try:
        user = await client.fetch_user(user_id)
        if user:
            await user.send(content)
            print(f"Message sent to {user.display_name} ({user_id})")
    except discord.Forbidden:
        print(f"Couldn't send a DM to {user.display_name} ({user_id}) - Forbidden")
    except discord.HTTPException as e:
        print(f"Failed to send a DM to {user_id}: {e}")
    except Exception as e:
        print(f"Unexpected error when sending DM to {user_id}: {e}")


@app.route('/fetch_member_ids', methods=['GET'])
async def fetch_member_ids_endpoint():
    auth_header = request.headers.get('Authorization')
    if not check_auth(auth_header):
        return Response("Unauthorized", status=401)

    try:
        member_ids = await fetch_member_ids()
        return jsonify({"member_ids": member_ids}), 200
    except Exception as e:
        print(f"Error fetching member IDs: {e}")
        return jsonify({"error": str(e)}), 500

async def fetch_member_ids():
    YOUR_GUILD_ID = 1260188923569770536  # Replace with your actual Guild ID
    guild = client.get_guild(YOUR_GUILD_ID)
    if guild:
        member_ids = [member.id for member in guild.members]
        print(f'Member IDs: {member_ids}')
        return member_ids
    else:
        print('Guild not found')
        raise Exception('Guild not found')

@app.route('/')
async def home():
    return "App is running"

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

async def start_server():
    config = Config()
    port = int(os.environ.get("PORT", 8000))
    config.bind = [f"0.0.0.0:{port}"]
    config.certfile = None  # 'piotr_bot/cert.pem'
    config.keyfile = None  # 'piotr_bot/key_nopass.pem'

    await hypercorn.asyncio.serve(app, config)

async def main():
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    if not DISCORD_TOKEN:
        raise ValueError("No Discord token found in environment variables.")

    # Start the server and bot concurrently
    server_task = asyncio.create_task(start_server())
    bot_task = asyncio.create_task(client.start(DISCORD_TOKEN))

    await asyncio.gather(server_task, bot_task)

if __name__ == '__main__':
    asyncio.run(main())
