---
route: /test/body-errors
method: POST
body:
  field1:
    type: string
    required: true
    minLength: 5
    description: First field
  field2:
    type: number
    required: true
    min: 1
    max: 10
    description: Second field
---

Field1: ${body.field1}
Field2: ${body.field2}
