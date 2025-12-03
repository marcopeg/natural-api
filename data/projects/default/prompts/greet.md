---
route: /greet/{name}
method: GET
model: gpt-5.1-codex-mini
---

# Goal:
Generate a warm, personalized greeting for ${name}.
Make it friendly and creative.

# Process:

1. Elaborate the greeting based on provided information
2. Write the geeting to "greeting.txt" in the data folder
3. Read it back and output it to the user

# Output:

The final output should contain only the readout from the "greeting.txt" without any comment or additional information, regardless of previous instructions.