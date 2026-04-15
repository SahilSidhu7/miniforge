"""Models for Ollama interaction and conversation management."""

import json
import requests


def ask_model(messages, system_prompt, model, ollama_url, stream=True):
    """Send conversation to Ollama and return response."""
    # Build a single prompt from message history
    prompt = ""
    for msg in messages:
        role = msg['role']
        content = msg['content']
        if role == 'user':
            prompt += f"\nUser: {content}\n"
        elif role == 'assistant':
            prompt += f"\nAssistant: {content}\n"
    prompt += "\nAssistant:"

    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": stream,
        "options": {
            "num_ctx": 8192,
            "temperature": 0.1,
            "num_predict": 4096,
            "stop": ["\nUser:"],
        }
    }

    try:
        if stream:
            resp = requests.post(ollama_url, json=payload, stream=True, timeout=300)
            resp.raise_for_status()
            full_response = ""
            for line in resp.iter_lines():
                if line:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    # hide raw action blocks while streaming, show them after
                    if "<<<ACTION>>>" not in full_response and "<<<ACTION>>>" not in token:
                        print(token, end="", flush=True)
                    full_response += token
                    if chunk.get("done"):
                        break
            print()  # newline after streaming
            return full_response
        else:
            resp = requests.post(ollama_url, json=payload, timeout=300)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()

    except requests.exceptions.Timeout:
        return "ERROR: Request timed out. The model may be too slow for this task."
    except requests.exceptions.ConnectionError:
        return "ERROR: Cannot connect to Ollama. Is it running?"
    except Exception as e:
        return f"ERROR: {e}"


class ConversationContext:
    """Manages conversation state and history."""
    
    def __init__(self, max_turns=10):
        self.messages = []
        self.max_turns = max_turns
        self.action_results = []

    def add_user(self, content):
        """Add a user message to the conversation."""
        self.messages.append({"role": "user", "content": content})
        self._trim()

    def add_assistant(self, content):
        """Add an assistant message to the conversation."""
        self.messages.append({"role": "assistant", "content": content})

    def add_action_result(self, action_type, result):
        """Log an action result for context."""
        self.action_results.append(f"[{action_type}]: {result[:200]}")

    def get_messages_with_results(self):
        """Inject recent action results into context."""
        msgs = self.messages.copy()
        if self.action_results and msgs:
            results_text = "\n".join(self.action_results[-5:])  # last 5 results
            msgs[-1]["content"] += f"\n\n[System: Recent action results]\n{results_text}"
        return msgs

    def _trim(self):
        """Keep context small for local models."""
        if len(self.messages) > self.max_turns * 2:
            # keep system summary + last N turns
            self.messages = self.messages[-(self.max_turns * 2):]
