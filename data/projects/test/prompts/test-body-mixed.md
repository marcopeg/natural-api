---
route: /test/body-mixed/{username}
method: POST
body:
  task:
    type: string
    required: true
    description: Task to perform
  priority:
    type: number
    min: 1
    max: 5
    default: 3
    description: Task priority
---

User ${route.username} wants to: ${body.task}
Priority: ${body.priority}
