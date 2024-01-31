#!/usr/bin/env python3
import os
import shlex
import subprocess
from openai import OpenAI

client = OpenAI()
import sys
from loguru import logger

SYSTEM = """Please comprehensively analyze the following text and reconstruct it entirely. You are granted the liberty to rewrite, supplement, or eliminate any part as you see fit, provided you adhere to these guidelines listed in order of priority:

- Preserve the core message and inherent purpose of the text.
- Prioritize refining the overall sentence structure and syntax over enhancements in word form or vocabulary.
- Refrain from using overly verbose or uncommon words. Maintain a similar degree of expressiveness and prolixity.

You must obligatory **always** respect the rules below:
- Employ the same language that's presented in the text.
- Do not reply with anything else but the reconstructed text.

Approach this task methodically and strive to produce the best possible result. The text will be displayed in its entirety as the prompt below, unless it is accompanied by instructions, case in which then the text will be either quoted or distinctly separated below the instructions.

## Example
User: Hi. I live in Brazil, I want to purchase a SUV S1, but will I get taxed on customs and pay duties fees? Because it says that the shipping is $200 with taxes included.
Assistant: Hello. I live in Brazil and want to buy the SUV S1. Will I need to pay customs taxes or duties? It says the $200 shipping fee includes taxes. Does that cover everything?
"""
PROMPT = """
## Actual Text
User: <SENTENCE>
Assistant: """

def send_request(sentence):
    # for ammount, temp, model, single_or_multiple in [(3, 0.6, "gpt-3.5-turbo", "single"), (2, 1.1, "gpt-3.5-turbo", "multiple")]: #(1, 0.95, "gpt-4", "multiple")]:
    response = client.chat.completions.create(model="gpt-4",
    top_p=1,
    temperature=1,
    stop=None,
    max_tokens=2000,
    messages=[
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": PROMPT.replace("<SENTENCE>", sentence)},])

    # Fix some common issues
    for choice in response.choices:
        content = choice.message.content

    return content


clipboard = subprocess.run(shlex.split("xclip -o -selection clipboard"), capture_output=True).stdout.decode("utf-8")
if not clipboard:
    sys.exit(1)

subprocess.run(shlex.split("xclip -i -selection clipboard"), input="".encode("utf-8"))

improved_sentence = send_request(clipboard)

if not improved_sentence:
    improved_sentence = clipboard # reverts

subprocess.run(shlex.split("xclip -i -selection clipboard"), input=improved_sentence.encode('utf-8'))
