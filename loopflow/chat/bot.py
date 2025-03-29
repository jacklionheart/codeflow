"""
Bot module for loopflow.

This module is intended to be used by the loopflow-server process,
which registers mate-configured LLMs with Discord. It uses a Flask app
to receive notifications from Discord bots. In a full implementation,
this would include logic for sending messages to Discord channels and
maintaining chat history.
"""

import logging
from flask import Flask, request, jsonify
import os

app = Flask(__name__)
logger = logging.getLogger("loopflow.bot")

# In a real implementation, these would be loaded from configuration.
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "your-discord-bot-token")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "your-discord-channel-id")

# Global registry for mate objects.
mates = {}

@app.route("/discord/webhook", methods=["POST"])
def discord_webhook():
    data = request.json
    logger.info("Received Discord webhook: %s", data)
    # Here you would determine which mate this message is for,
    # forward the message to the corresponding LLM instance,
    # and possibly update conversation history.
    response = {"status": "received"}
    return jsonify(response)

def register_mates():
    # Load mate configurations from the mates directory.
    # For example, using the same logic as load_all_teammates in templates.
    logger.info("Registering mates from configuration...")
    # Here you would call:
    # from loopflow.templates import load_all_teammates
    # global mates
    # mates = load_all_teammates()
    # For now, we simulate:
    mates["merlin"] = "Mate object for merlin"
    mates["maya"] = "Mate object for maya"
    logger.info("Registered mates: %s", list(mates.keys()))

def run_discord_bot():
    register_mates()
    logger.info("Starting Discord bot server on port 5000")
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    run_discord_bot()
