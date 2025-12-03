---
route: /test/body-validation
method: POST
body:
  age:
    type: number
    min: 0
    max: 120
    maxDecimals: 0
    description: User age
  email:
    type: string
    pattern: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$
    description: Email address
---

User age: ${body.age}
Email: ${body.email}
