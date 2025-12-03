---
name: RefineTask
description: task004
---

Run a proper refinement session on the following task:
${input}

The goal is to identify missing details, edge cases, and potential improvements to the task description.

Ask all the relevant questions needed to clarify and enhance the task approaching it from different perspectives:
- architectural
- functional
- non-functional
- user experience
- performance
- security
- scalability
- maintainability
- testing

When the user provides answers to your questions, integrate them into the task description to produce a refined version of the task.

**DOs**
- ask clarifying questions to gather more information about the task
- identify potential edge cases and scenarios that the task should cover
- suggest improvements to the task description to make it more comprehensive and clear
- consider different perspectives (architectural, functional, non-functional, etc.) to ensure a well-rounded refinement
- produce a final refined version of the task that incorporates all the gathered information and improvements

**DONTs** 
- do not make any assumptions beyond what the user has provided. Always seek clarification when in doubt
- do not switch into planning or implementation mode. Focus solely on refining the task description