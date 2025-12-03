---
route: /test/body-config-error/{name}
method: POST
body:
  name:
    type: string
    description: This duplicates the route parameter
---

This prompt has a configuration error - duplicate field name.
