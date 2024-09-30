#!/usr/bin/env python3
import textwrap
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

Now, reconstruct the text below based on these instructions. Provide the text inside <output> tags, without any additional commentary or explanations. Generate 3 different versions of the reconstructed text, each enclosed in separate <output> tags."""

import textwrap

EXAMPLE_PROMPTS = [
    # First example
    {"role": "user",
     "content": "<input>Do you still have the findings of the reversion of the communication protocol? I work with RE and would love to play around with that 😏</input>"},
    {"role": "assistant",
     "content": textwrap.dedent("""
        <output>Do you still have your findings from reverse engineering the communication protocol? I work in reverse engineering and would love to explore that 😏</output>
        <output>I work with reverse engineering and would love to experiment with it 😏. Do you still have the results from the communication protocol reversion?</output>
        <output>Do you still have the results from the reversion of the communication protocol? I work with RE and would be excited to explore that 😏</output>
        <output>Do you still have the results from reversing the communication protocol? I specialize in reverse engineering and would love to experiment with them. 😏</output>
        <output>Do you still have the results from the communication protocol reversal? I work in reverse engineering and would love to dig into it 😏</output>""".strip())},

    # Second example
    {"role": "user",
     "content": "<input>Can you share the recent sales reports? I'm preparing for tomorrow's meeting, and it would really help.</input>"},
    {"role": "assistant",
     "content": textwrap.dedent("""
        <output>Could you send me the updated sales reports? I need them for a meeting tomorrow and would appreciate it.</output>
        <output>I'm preparing for tomorrow's meeting. Could you share the sales reports when you get a chance?</output>
        <output>Are the recent sales reports available? I'd like to review them before the meeting.</output>
        <output>I could really use the sales data for tomorrow's meeting. Can you send it over?</output>
        <output>Any chance you can provide me with the sales reports? They'd be useful for tomorrow's discussion.</output>""".strip())},

    # Third example
    {"role": "user",
     "content": "<input>have you checked out the new UI? we need feedback on this asap. let me know when you get a chance</input>"},
    {"role": "assistant",
     "content": textwrap.dedent("""
        <output>Have you had a look at the new UI? we could really use your feedback soon. let me know when you're able to review it</output>
        <output>We need feedback on the new UI as soon as possible. please take a look and tell me what you think</output>
        <output>Could you check out the new UI? your input is needed urgently, so please let me know when you have time</output>
        <output>Have you reviewed the new UI design yet? we need feedback at your earliest convenience</output>
        <output>Let me know when you've had a chance to look at the UI changes. your feedback is important and we need it quickly</output>""".strip())},

    # Fourth example (multi-line input)
    {"role": "user",
     "content": "<input>hey! did you finish reviewing the documentation? we're hoping to finalize the project scope by the end of the week.\n\nif you can, try to send me your thoughts by thursday. thx!</input>"},
    {"role": "assistant",
     "content": textwrap.dedent("""
        <output>hi! just checking in—have you finished looking over the documentation? we want to finalize the project scope by week's end.</output>
        <output>did you get a chance to review the docs? if possible, please send over your feedback by thursday so we can move forward with the project.</output>
        <output>we need to finalize the project scope this week. can you send me your review of the documentation by thursday?</output>
        <output>if you've finished reviewing the documentation, could you share your thoughts by thursday? we're wrapping up the project scope soon. thx!!</output>
        <output>please let me know when you've finished reviewing the documents. we're hoping to have everything ready for final approval by week's end. thank you</output>""".strip())},

    # Fifth example (varying structure drastically)
    {"role": "user",
     "content": "<input>Are the Q3 results out yet? I've been waiting on them for ages and still no word. This is holding up our analysis!</input>"},
    {"role": "assistant",
     "content": textwrap.dedent("""
        <output>Do we have the Q3 numbers yet? I need them to move forward with the analysis, and they've been delayed for too long.</output>
        <output>Still waiting on the Q3 results here. They're overdue and holding back our analysis process.</output>
        <output>The Q3 report is holding up our work. When can we expect to receive it?</output>
        <output>We really need those Q3 results for our analysis. Have they been released yet?</output>
        <output>Has there been any update on the Q3 data? It's becoming a major blocker for our analysis!</output>""".strip())}
]



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
