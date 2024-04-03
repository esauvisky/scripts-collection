#!/usr/bin/env python3
import os
import shlex
import subprocess
import sys
# from pygments.lexers import guess_lexer, get_lexer_by_name, get_all_lexers
# from pygments.util import ClassNotFound

# Define a list of allowed languages (using the common names used by Pygments)
# allowed_lexers = {
#     "python", "java", "javascript", "c", "cpp", "csharp", "ruby", "go", "php", "perl", "bash", "sql", "html", "css",
#     "json", "xml", "yaml", "markdown", "diff", "shell", "makefile", "dockerfile"}

import re

def detect_language(clipboard):
    patterns = {
        r"#!/bin/bash": "bash",
        r"#include <[^>]+>": "cpp",
        r"import java\.[\w\.]+": "java",
        r"def [\w]+\(": "python",
        r"function [\w]+\(": "javascript",
        r"var [\w]+ = ": "javascript",
        r"let [\w]+ = ": "javascript",
        r"const [\w]+ = ": "javascript",
        r"#!/usr/bin/env python": "python",
        r"for [\w]+ in": "python",
        r"from [\w\.]+ import": "python",
        r"print\(": "python",
        r"import [\w\.]+": "python",
        r"class [\w]+ ?\{": "java",
        r"public static void main": "java",
        r"{\s*[\w]+\s*:": "json",
        r"<script": "html",
        r"<html": "html",
        r"<\?php": "php",
        # Add more patterns here
    }

    for pattern, language in patterns.items():
        if re.search(pattern, clipboard):
            return language

    # Check for unique language-specific features
    if re.search(r"class [\w]+ ?\{", clipboard) and "public static void main" in clipboard:
        return "java"
    # Add other nuanced checks

    return ""  # Default if no specific language is detected


# Function to remove extra indentation
def remove_extra_indentation(text):
    lines = text.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    min_indentation = min((len(line) - len(line.lstrip()) for line in non_empty_lines), default=0)
    trimmed_lines = [line[min_indentation:] for line in lines]
    return '\n'.join(trimmed_lines)


clipboard = subprocess.run(shlex.split("xclip -o -selection clipboard"), capture_output=True).stdout.decode("utf-8")
if not clipboard:
    sys.exit(1)

# Detect language with Pygments and remove extra indentation
language = detect_language(clipboard)
clipboard = remove_extra_indentation(clipboard).strip()

final_sentence = f'''
```{language}
{clipboard}
```
'''

subprocess.run(shlex.split("xclip -i -selection clipboard"), input=final_sentence.encode('utf-8'))
