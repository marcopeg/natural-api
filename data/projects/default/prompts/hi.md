---
model: gpt-5.1-codex-mini
method: POST
route: /hi/{name}
body:
  age:
    type: number
    required: true
---

Generate a random greeting for ${route.name} of age ${body.age}.