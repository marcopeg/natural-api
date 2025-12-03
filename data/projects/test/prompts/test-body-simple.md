---
route: /test/body-simple
method: POST
body:
  message:
    type: string
    required: true
    description: A simple message
---

Received message: ${body.message}
