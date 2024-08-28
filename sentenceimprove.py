#!/usr/bin/env python3
import os
import shlex
import subprocess
from openai import OpenAI
import sys
from loguru import logger
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib

client = OpenAI()

SYSTEM = """You are tasked with analyzing and reconstructing a given text. Your goal is to improve its clarity and structure while preserving the core message and tone. Follow these instructions to reconstruct the text:

1. Use the same language as the original text.
2. Improve any unclear or awkwardly structured sentences.
3. Maintain the essential message and intent of the original text.
4. Refine the overall sentence structure and syntax for better readability.
5. Keep the same tone and style, as if the same person wrote it.
6. Preserve any unique formatting (e.g., all lowercase, all uppercase, punctuation, etc) from the original text.
7. If words in a different language than the main one appear, translate them to match the main language of the text, as long as it's obvious it's a request from the user.
8. Ignore minor typos or spelling errors (keeping them in the output) unless they significantly impact clarity.
9. If there are technical terms or proper nouns, ensure they are spelled correctly (e.g.: a function name will be put inside backticks in the output).
10. Don't change punctuation differently than the input message. Keep capital letters the same way as the input.

Remember:
- The goal is to make the text clearer and more coherent while sounding like it came from the same author.
- If the original text uses informal language or slang, maintain that style in your reconstruction.

Here are some examples of input and output:

<example>
<input>We get the pseudocode of old attack/dodge methods on ghidra and do a fuzzy similarity search something like that of that versus the pseucode of the new ver.\n\nSo if the score is high it means the method didnt change much, which means its like to be t he righjt one</input>
<output>We get the pseudocode of the old attack and dodge methods using Ghidra and calculate the code similarity against methods of the new version.\n\nIf the similarity score is high, it means that their code is pretty similar, suggesting that it's the same method</output>
</example>

<example>
<input>"you can also do a traceMethodsByArgType or traceClassesByPattern and dodge like 7 times in a raid, then copy the entire trace and look for a method that was called only 7 times"</input>
<output>"you can also use `traceMethodsByArgType` or `traceClassesByPattern`, then dodge 7 consecutive times in a raid. afterwards look for the method that was called exactly seven times within that trace"</output>
</example>

<example>
<input>eu estou sempre muito ocupado, então já pedi à minha assistente para entrar em contato contig amanha. Se achar mewlhor, também podes falar com ela primeiro. O nome dela é Thaylana"</input>
<output>eu estou sempre bastante ocupado, então já falei à minha assistente, Thaylana, para que amanhã entre em contato contigo. Se preferir podes falar com ela antes também</output>
</example>

Now, reconstruct the given text based on these instructions. Provide your reconstructed text inside <output> tags, without any additional commentary or explanations. Generate 3 different versions of the reconstructed text, each enclosed in separate <output> tags."""

def send_request(sentence):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "<input>" + sentence + "</input>"},
        ],
        temperature=1,
        frequency_penalty=0.5,
        presence_penalty=0.5,
        max_tokens=2000,
        n=2  # Request 5 different completions
    )

    # Extract the content from the responses
    contents = [choice.message.content for choice in response.choices]

    # Find the content within <output> tags for each response
    outputs = []
    for content in contents:
        start_tag = "<output>"
        end_tag = "</output>"
        start_index = content.find(start_tag) + len(start_tag)
        end_index = content.find(end_tag)

        if start_index >= len(start_tag) and end_index > -1:
            outputs.append(content[start_index:end_index].strip())
        else:
            outputs.append(content.replace("<output>", "").replace("</output>", "").strip())

    return outputs


class ContextMenuWindow(Gtk.ApplicationWindow):
    def __init__(self, app, options):
        super().__init__(application=app, title="Select an option")
        self.set_default_size(300, -1)
        self.options = options
        self.selected_option = None

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_child(box)

        for i, option in enumerate(self.options, start=1):
            button = Gtk.Button(label=f"Option {i}")
            button.connect("clicked", self.on_option_clicked, option)
            box.append(button)

        self.set_resizable(False)
        self.set_decorated(False)

    def on_option_clicked(self, button, option):
        self.selected_option = option
        self.close()

class ContextMenuApp(Gtk.Application):
    def __init__(self, options):
        super().__init__(application_id="com.example.ContextMenu")
        self.options = options
        self.selected_option = None

    def do_activate(self):
        # Create a hidden window to serve as a parent
        self.window = Gtk.ApplicationWindow(application=self, title="Hidden Window")
        self.window.set_default_size(1, 1)
        self.window.set_opacity(0)  # Make the window invisible

        self.window.present()

        # Create the popover menu
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        popover.set_child(box)

        for i, option in enumerate(self.options, start=1):
            button = Gtk.Button(label=f"Option {i}")
            button.connect("clicked", self.on_option_clicked, option)
            box.append(button)

        # Get the current mouse position
        display = Gdk.Display.get_default()
        seat = display.get_default_seat()
        pointer = seat.get_pointer()
        _, x, y = pointer.get_position()

        # Position and show the popover
        popover.set_pointing_to(Gdk.Rectangle(x, y, 1, 1))
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.set_autohide(True)
        popover.popup()

        # Add a timeout to quit the application if no selection is made
        GLib.timeout_add_seconds(60, self.on_timeout)

    def on_option_clicked(self, button, option):
        self.selected_option = option
        self.quit()

    def on_timeout(self):
        self.quit()
        return False

def show_context_menu(options):
    app = ContextMenuApp(options)
    app.run()
    return app.selected_option

clipboard = subprocess.run(shlex.split("xclip -o -selection clipboard"), capture_output=True).stdout.decode("utf-8")
if not clipboard:
    sys.exit(1)

subprocess.run(shlex.split("xclip -i -selection clipboard"), input="".encode("utf-8"))

improved_sentences = send_request(clipboard)

if improved_sentences:
    selected_sentence = show_context_menu(improved_sentences)
    if selected_sentence:
        improved_sentence = selected_sentence
    else:
        improved_sentence = clipboard  # revert if no selection made
else:
    improved_sentence = clipboard  # revert if no improvements generated

subprocess.run(shlex.split("xclip -i -selection clipboard"), input=improved_sentence.encode('utf-8'))
