# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Copyright (C) 2020-2023 by TgCatUB@Github.
# This file is part of: https://github.com/TgCatUB/catuserbot
# and is released under the "GNU v3.0 License Agreement".
# Please see: https://github.com/TgCatUB/catuserbot/blob/master/LICENSE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import os
from openai import OpenAI
from telethon import events

from userbot import catub
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.utils import reply_id
from ..sql_helper.globals import addgvar, delgvar, gvarstatus

plugin_category = "tools"

# Updated Models and Sizes
MODELS = ["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo-0125"] 
DALLE_SIZES = ["1024x1024", "1792x1024", "1024x1792"]  # DALL-E 3 supported sizes

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ChatContext:
    """Handles conversation context for GPT"""
    @staticmethod
    def get_context(chat_id):
        # Implement your context storage logic here
        return []

    @staticmethod 
    def add_to_context(chat_id, role, content):
        # Implement context append logic
        pass

    @staticmethod
    def clear_context(chat_id):
        # Implement context clearing
        return "Context cleared"

async def generate_gpt_response(text, chat_id, model=None):
    """Generate response using modern ChatCompletion API"""
    try:
        messages = [{"role": "user", "content": text}]
        
        if system_msg := gvarstatus("SYSTEM_MESSAGE"):
            messages.insert(0, {"role": "system", "content": system_msg})
            
        response = client.chat.completions.create(
            model=model or gvarstatus("CHAT_MODEL") or "gpt-3.5-turbo-0125",
            messages=messages,
            max_tokens=1000
        )
        return response.choices[0].message.content
        
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

async def generate_dalle_image(prompt, size="1024x1024", n=1):
    """Generate images using DALL-E 3"""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard",
            n=n
        )
        return [img.url for img in response.data]
    except Exception as e:
        return [f"⚠️ DALL-E Error: {str(e)}"]

@catub.cat_cmd(
    pattern="gpt(?:\s|$)([\s\S]*)",
    command=("gpt", plugin_category),
    info={
        "header": "Generate GPT response (supports GPT-4-turbo)",
        "usage": [
            "{tr}gpt <prompt>",
            "{tr}gpt -m <model> (change model)",
            "{tr}gpt -s <system message>",
            "{tr}gpt -dc (clear context)"
        ],
        "models": MODELS
    }
)
async def handle_gpt(event):
    text = event.pattern_match.group(1)
    reply = await event.get_reply_message()
    chat_id = event.chat_id

    # Handle model change
    if "-m" in text:
        model = text.replace("-m", "").strip()
        if model in MODELS:
            addgvar("CHAT_MODEL", model)
            return await edit_delete(event, f"Model set to: {model}")
        return await edit_delete(event, f"Available models: {', '.join(MODELS)}")

    # Handle system message
    elif "-s" in text:
        msg = text.replace("-s", "").strip()
        addgvar("SYSTEM_MESSAGE", msg)
        ChatContext.clear_context(chat_id)
        return await edit_delete(event, f"System message set:\n`{msg}`")

    # Handle context clearing
    elif "-dc" in text:
        result = ChatContext.clear_context(chat_id)
        return await edit_delete(event, result)

    # Get prompt from reply if no text
    if not text and reply:
        text = reply.text
    if not text:
        return await edit_delete(event, "Please provide a prompt")

    catevent = await edit_or_reply(event, "🧠 Thinking...")
    response = await generate_gpt_response(text, chat_id)
    await catevent.edit(response)

@catub.cat_cmd(
    pattern="dalle(?:\s|$)([\s\S]*)",
    command=("dalle", plugin_category),
    info={
        "header": "Generate DALL-E 3 images",
        "usage": [
            "{tr}dalle <prompt>",
            "{tr}dalle -s <size>",
            "{tr}dalle -n <1-5>"
        ],
        "sizes": DALLE_SIZES
    }
)
async def handle_dalle(event):
    text = event.pattern_match.group(1)
    
    # Handle size change
    if "-s" in text:
        size = text.replace("-s", "").strip()
        if size in DALLE_SIZES:
            addgvar("DALLE_SIZE", size)
            return await edit_delete(event, f"Size set to: {size}")
        return await edit_delete(event, f"Available sizes: {', '.join(DALLE_SIZES)}")

    # Handle count change
    elif "-n" in text:
        try:
            n = min(5, max(1, int(text.replace("-n", "").strip())))
            addgvar("DALLE_LIMIT", n)
            return await edit_delete(event, f"Image count set to: {n}")
        except ValueError:
            return await edit_delete(event, "Please enter a number 1-5")

    # Generate images
    if not text:
        return await edit_delete(event, "Please provide a prompt")

    catevent = await edit_or_reply(event, "🎨 Painting your idea...")
    size = gvarstatus("DALLE_SIZE") or "1024x1024"
    n = min(5, max(1, int(gvarstatus("DALLE_LIMIT") or 1)))
    
    image_urls = await generate_dalle_image(text, size, n)
    
    if image_urls and not image_urls[0].startswith("⚠️"):
        await event.client.send_file(
            event.chat_id,
            image_urls,
            caption=f"Prompt: {text}",
            reply_to=await reply_id(event)
        )
        await catevent.delete()
    else:
        await catevent.edit(image_urls[0] if image_urls else "Failed to generate images")
