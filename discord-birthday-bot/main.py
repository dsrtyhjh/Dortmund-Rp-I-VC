# Discord Bot Invite-Link:
# https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands

import discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime, timedelta, time
import json
import os

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot läuft! 🎉"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID") or 123456789012345678)
CHANNEL_ID = int(os.getenv("CHANNEL_ID") or 123456789012345678)

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

BIRTHDAY_FILE = 'birthdays.json'
BIRTHDAY_ROLE_NAME = "Geburtstags Kind 🎉🎁"

def load_birthdays():
    if not os.path.exists(BIRTHDAY_FILE):
        return {}
    with open(BIRTHDAY_FILE, 'r') as f:
        return json.load(f)

def save_birthdays(data):
    with open(BIRTHDAY_FILE, 'w') as f:
        json.dump(data, f)

class BirthdayModal(discord.ui.Modal, title="Geburtstag eingeben"):
    geburtstag = discord.ui.TextInput(
        label="Wann hast du Geburtstag? (TT-MM-JJJJ)",
        placeholder="z. B. 11-06-2004",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            geburtsdatum = datetime.strptime(self.geburtstag.value, "%d-%m-%Y")
        except ValueError:
            await interaction.response.send_message("❌ Ungültiges Format. Bitte TT-MM-JJJJ verwenden.", ephemeral=True)
            return

        data = load_birthdays()
        data[str(interaction.user.id)] = self.geburtstag.value
        save_birthdays(data)

        await interaction.response.send_message(f"✅ Geburtsdatum **{self.geburtstag.value}** gespeichert!", ephemeral=True)

@tree.command(name="enter_birthday", description="Gib dein Geburtsdatum ein", guild=discord.Object(id=GUILD_ID))
async def enter_birthday_command(interaction: discord.Interaction):
    await interaction.response.send_modal(BirthdayModal())

@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f'✅ Bot online als {client.user}')
    check_birthdays.start()
    remove_birthday_roles.start()

@tasks.loop(hours=1)
async def check_birthdays():
    now = datetime.utcnow()
    today = now.strftime("%d-%m")
    year_now = now.year

    data = load_birthdays()
    guild = client.get_guild(GUILD_ID)
    channel = guild.get_channel(CHANNEL_ID)
    role = discord.utils.get(guild.roles, name=BIRTHDAY_ROLE_NAME)

    for user_id, geburtstag in data.items():
        try:
            geb = datetime.strptime(geburtstag, "%d-%m-%Y")
            if geb.strftime("%d-%m") == today:
                alter = year_now - geb.year
                member = guild.get_member(int(user_id))
                if member:
                    await channel.send(f"🎉 Herzlichen Glückwunsch zum **{alter}. Geburtstag**, {member.mention}! 🎂")
                    if role and role not in member.roles:
                        await member.add_roles(role)
        except Exception as e:
            print(f"Fehler bei {user_id}: {e}")

@tasks.loop(time=time(23, 59))
async def remove_birthday_roles():
    guild = client.get_guild(GUILD_ID)
    if guild:
        role = discord.utils.get(guild.roles, name=BIRTHDAY_ROLE_NAME)
        if role:
            for member in guild.members:
                if role in member.roles:
                    try:
                        await member.remove_roles(role)
                        print(f"🎈 Rolle entfernt von {member.display_name}")
                    except Exception as e:
                        print(f"Fehler beim Entfernen der Rolle bei {member.display_name}: {e}")
    else:
        print(f"Guild mit ID {GUILD_ID} nicht gefunden.")

@remove_birthday_roles.before_loop
async def before_remove_birthday_roles():
    await client.wait_until_ready()

keep_alive()

if not TOKEN:
    raise ValueError("TOKEN environment variable not set!")
client.run(TOKEN)
