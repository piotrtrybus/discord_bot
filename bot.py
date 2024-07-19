import discord
from quart import Quart, request, jsonify
import asyncio
import os

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True  # Ensure you have the intent to fetch members

client = discord.Client(intents=intents)

# Initialize Quart app
app = Quart(__name__)

@app.route('/webhook', methods=['POST'])
async def webhook():
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
            print(f"Message sent to {user.display_name}")
    except discord.Forbidden:
        print(f"Couldn't send a DM to {user.display_name}")
    except discord.HTTPException as e:
        print(f"Failed to send a DM: {e}")

@app.route('/fetch_member_ids', methods=['GET'])
async def fetch_member_ids_endpoint():
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
        # Optionally, write member IDs to a file
        with open('member_ids.txt', 'w') as file:
            for member_id in member_ids:
                file.write(f'{member_id}\n')
        return member_ids
    else:
        print('Guild not found')
        raise Exception('Guild not found')

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

async def main():
    # Start the Quart app in a separate task
    task1 = asyncio.create_task(app.run_task(host='0.0.0.0', port=5000))
    print("Quart server is running on http://0.0.0.0:5000")
    
    # Run the bot
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    if not DISCORD_TOKEN:
        raise ValueError("No Discord token found in environment variables.")
    
    task2 = asyncio.create_task(client.start(DISCORD_TOKEN))
    
    await task1
    await task2

if __name__ == '__main__':
    asyncio.run(main())
