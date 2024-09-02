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
intents.members = True

client = discord.Client(intents=intents)
app = Quart(__name__)


def check_auth(auth_header):
    if not auth_header:
        return False
    try:
        auth_type, credentials = auth_header.split(" ")
        if auth_type.lower() == "basic":
            decoded_credentials = base64.b64decode(credentials).decode("utf-8")
            username, password = decoded_credentials.split(":")
            return username == os.getenv(
                'auth_login') and password == os.getenv('auth_pass')
    except Exception as e:
        print(f"[ERROR] Invalid authentication format: {e}")
    return False


@app.route('/webhook', methods=['POST'])
async def webhook():
    if not check_auth(request.headers.get('Authorization')):
        return Response("Unauthorized", status=401)

    data = await request.get_json()
    user_id = data.get('user_id')
    message_content = data.get('message', 'hello')
    guild_id = data.get('guild_id')

    if user_id and guild_id:
        asyncio.create_task(send_dm(user_id, message_content, guild_id))
        return '', 200
    else:
        return jsonify({"error":
                        "both user_id and guild_id are required"}), 400


async def send_dm(user_id, content, guild_id):
    try:
        guild = client.get_guild(guild_id)
        if not guild:
            guild = await client.fetch_guild(guild_id)
            if not guild:
                print(f"Guild {guild_id} not found after fetching")
                return

        # Try to get the member from cache
        member = guild.get_member(user_id)
        if not member:
            # Fetch the member if not in cache
            try:
                member = await guild.fetch_member(user_id)
                print(f"Member {user_id} fetched from API")
            except discord.NotFound:
                print(
                    f"Member {user_id} not found in guild {guild_id} after fetching"
                )
                return

        optin_role = discord.utils.get(guild.roles, name="Cool guy")
        if optin_role in member.roles:
            await member.send(content)
            print(f"Message sent to {member.display_name} ({user_id})")
        else:
            print(
                f"User {member.display_name} ({user_id}) does not have the {optin_role} role"
            )
    except discord.Forbidden:
        print(f"Couldn't send a DM to user {user_id} - Forbidden")
    except discord.HTTPException as e:
        print(f"Failed to send a DM to {user_id}: {e}")
    except Exception as e:
        print(f"Unexpected error when sending DM to {user_id}: {e}")


@app.route('/fetch_member_ids', methods=['GET'])
async def fetch_member_ids_endpoint():
    if not check_auth(request.headers.get('Authorization')):
        return Response("Unauthorized", status=401)

    try:
        member_ids = await fetch_member_ids()
        return jsonify({"member_ids": member_ids}), 200
    except Exception as e:
        print(f"Error fetching member IDs: {e}")
        return jsonify({"error": str(e)}), 500


async def fetch_member_ids():
    guild_id = 1260188923569770536  # DISCORD SERVER ID
    guild = client.get_guild(guild_id)
    if guild:
        return [member.id for member in guild.members]
    else:
        raise Exception('Guild not found')


@app.route('/')
async def home():
    return "App is running"


@client.event
async def on_ready():
    print(f'App logged in as {client.user}')


async def start_server():
    config = Config()
    config.bind = [f"0.0.0.0:{int(os.environ.get('PORT', 8000))}"]
    await hypercorn.asyncio.serve(app, config)


async def main():
    discord_token = os.getenv('discord_token')
    if not discord_token:
        raise ValueError("No Discord token found.")

    await asyncio.gather(start_server(), client.start(discord_token))


if __name__ == '__main__':
    asyncio.run(main())
