---
route: /test/body-enum
method: POST
body:
  color:
    type: string
    enum: [red, green, blue]
    required: true
    description: Color choice
---

Selected color: ${body.color}
