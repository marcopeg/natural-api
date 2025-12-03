---
route: /test/body-defaults
method: POST
body:
  name:
    type: string
    default: Anonymous
    description: User name
  active:
    type: boolean
    default: true
    description: Active status
---

Name: ${body.name}
Active: ${body.active}
