"""Models for Ollama interaction and conversation management."""

import json
import re
import requests
from typing import List, Dict
import time


ACTION_BLOCK_RE = re.compile(r'<<<ACTION>>>.*?<<<END>>>', re.DOTALL)
ACTION_TYPE_RE = re.compile(r"TYPE:\s*([a-z_]+)", re.IGNORECASE)
ACTION_VERBS = (
    "create", "make", "build", "generate", "write", "edit", "update", "change",
    "fix", "refactor", "rename", "move", "copy", "delete", "remove", "read",
    "show", "list", "find", "search", "scan", "open", "install", "run",
    "scaffold", "set up", "setup", "add"
)
NON_ACTION_PREFIXES = (
    "how", "what", "why", "when", "where", "who", "explain", "describe",
    "teach", "help me understand", "can you explain", "what is", "how do i"
)
VERB_TO_ACTION_TYPES = {
    "edit": {"edit_file", "read_file"},
    "update": {"edit_file", "read_file"},
    "change": {"edit_file", "read_file"},
    "fix": {"edit_file", "read_file"},
    "read": {"read_file"},
    "show": {"read_file", "list_dir", "tree", "stats"},
    "list": {"list_dir", "find_files", "tree"},
    "find": {"find_files", "read_file", "list_dir"},
    "search": {"find_files", "read_file", "list_dir"},
    "scan": {"find_files", "tree", "stats"},
    "open": {"read_file", "list_dir"},
    "run": {"bash"},
}


def contains_action_blocks(text: str) -> bool:
    """Return True when the response contains at least one valid action block."""
    return bool(text and ACTION_BLOCK_RE.search(text))


def extract_action_types(text: str) -> set:
    """Return normalized action types found inside action blocks."""
    if not text:
        return set()
    return {match.lower() for match in ACTION_TYPE_RE.findall(text)}


def should_require_actions(user_input: str) -> bool:
    """Heuristic: actionable prompts should return executable action blocks."""
    if not user_input:
        return False

    normalized = " ".join(user_input.strip().lower().split())
    if not normalized:
        return False

    if normalized.endswith("?") or any(normalized.startswith(prefix) for prefix in NON_ACTION_PREFIXES):
        return False

    return any(normalized.startswith(verb) for verb in ACTION_VERBS)


def expected_action_types(user_input: str) -> set:
    """Return action types that should appear for strongly directed verbs."""
    if not user_input:
        return set()

    normalized = " ".join(user_input.strip().lower().split())
    if not normalized:
        return set()

    for verb, action_types in VERB_TO_ACTION_TYPES.items():
        if normalized.startswith(verb):
            return action_types
    return set()


def _build_prompt(messages):
    """Build a plain prompt from message history for Ollama generate()."""
    prompt = ""
    for msg in messages:
        role = msg['role']
        content = msg['content']
        if role == 'user':
            prompt += f"\nUser: {content}\n"
        elif role == 'assistant':
            prompt += f"\nAssistant: {content}\n"
    prompt += "\nAssistant:"
    return prompt


def _make_payload(prompt, system_prompt, model, stream, temperature, num_predict, num_ctx):
    return {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": stream,
        "options": {
            "num_ctx": num_ctx,
            "temperature": temperature,
            "num_predict": num_predict,
            "stop": ["\nUser:"],
        }
    }


def ask_model(messages, system_prompt, model, ollama_url, stream=True, timeout=300,
              temperature=0.1, num_predict=4096, num_ctx=8192, require_actions=False):
    """Send conversation to Ollama and return response with improved error handling."""
    prompt = _build_prompt(messages)
    stream = stream and not require_actions
    payload = _make_payload(prompt, system_prompt, model, stream, temperature, num_predict, num_ctx)

    expected_types = expected_action_types(messages[-1]["content"] if messages else "")

    def response_is_valid(text: str) -> bool:
        if not require_actions:
            return True
        if not contains_action_blocks(text):
            return False
        if not expected_types:
            return True
        return bool(extract_action_types(text) & expected_types)

    try:
        if stream:
            resp = requests.post(ollama_url, json=payload, stream=True, timeout=timeout)
            resp.raise_for_status()
            full_response = ""
            last_output = time.time()
            
            try:
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        # hide raw action blocks while streaming, show them after
                        if "<<<ACTION>>>" not in full_response and "<<<ACTION>>>" not in token:
                            print(token, end="", flush=True)
                        full_response += token
                        last_output = time.time()
                        if chunk.get("done"):
                            break
                print()  # newline after streaming
                return full_response
            except requests.exceptions.ChunkedEncodingError:
                if full_response:
                    print()
                    return full_response + "\n\n[Note: Response was truncated]"
                return "ERROR: Failed to receive complete response from Ollama"
        else:
            resp = requests.post(ollama_url, json=payload, timeout=timeout)
            resp.raise_for_status()
            response = resp.json().get("response", "").strip()

            if require_actions and not response_is_valid(response):
                expected_note = ""
                if expected_types:
                    expected_note = (
                        " Include at least one action of type: "
                        + ", ".join(sorted(expected_types))
                        + "."
                    )
                retry_prompt = (
                    prompt
                    + "\n[System reminder: Your previous answer was invalid because it did not include any "
                      "valid action blocks for the user's request. Re-answer using one or more valid action blocks "
                      "first. Do not give a tutorial or numbered steps unless the user explicitly asked for an explanation."
                      + expected_note
                      + "]\n"
                    + "Assistant:"
                )
                retry_payload = _make_payload(
                    retry_prompt, system_prompt, model, False, temperature, num_predict, num_ctx
                )
                retry_resp = requests.post(ollama_url, json=retry_payload, timeout=timeout)
                retry_resp.raise_for_status()
                retry_text = retry_resp.json().get("response", "").strip()
                if response_is_valid(retry_text):
                    response = retry_text

            return response

    except requests.exceptions.Timeout:
        return f"ERROR: Request timed out after {timeout}s. The model may be too slow or Ollama is overloaded."
    except requests.exceptions.ConnectionError:
        return "ERROR: Cannot connect to Ollama. Make sure:\n  1. Ollama is running (ollama serve)\n  2. The URL is correct"
    except requests.exceptions.HTTPError as e:
        if "404" in str(e):
            return f"ERROR: Model not found. Run: ollama pull {model}"
        return f"ERROR: HTTP error {e.response.status_code}"
    except json.JSONDecodeError:
        return "ERROR: Invalid response from Ollama (not JSON)"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


class ConversationContext:
    """Manages conversation state and history with improved tracking."""
    
    def __init__(self, max_turns=10):
        self.messages: List[Dict[str, str]] = []
        self.max_turns = max_turns
        self.action_results: List[str] = []
        self.turn_count = 0

    def add_user(self, content: str):
        """Add a user message to the conversation."""
        if not content or not content.strip():
            return False
        self.messages.append({"role": "user", "content": content.strip()})
        self.turn_count += 1
        self._trim()
        return True

    def add_assistant(self, content: str):
        """Add an assistant message to the conversation."""
        if not content:
            return False
        self.messages.append({"role": "assistant", "content": content})
        return True

    def add_action_result(self, action_type: str, result: str):
        """Log an action result for context."""
        if result:
            truncated = result[:200] if len(result) > 200 else result
            self.action_results.append(f"[{action_type}]: {truncated}")

    def get_messages_with_results(self) -> List[Dict[str, str]]:
        """Inject recent action results into context."""
        msgs = self.messages.copy()
        if self.action_results and msgs:
            results_text = "\n".join(self.action_results[-5:])  # last 5 results
            if msgs[-1]['role'] == 'user':
                # Add to last user message
                msgs[-1]["content"] += f"\n\n[System: Recent action results]\n{results_text}"
        return msgs

    def clear(self):
        """Clear conversation history."""
        self.messages = []
        self.action_results = []
        self.turn_count = 0

    def _trim(self):
        """Keep context small for local models."""
        if len(self.messages) > self.max_turns * 2:
            # keep system summary + last N turns
            self.messages = self.messages[-(self.max_turns * 2):]
