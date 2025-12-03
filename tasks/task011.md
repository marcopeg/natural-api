# Code Refactoring & Optimization

Goal: restructure the dynamic route implementation so to be able to focus on the prompt generation.

## Expected Phases

The Dynamic Route should move through the following phases:

1. validation
    - reject white listed route patterns
    - validate the project exists
    - validate the route exists and it matches a prompt
    - validate the informations (params, body) matcht the prompt's expectation
    - prepare the user's data scoped to the project
2. prompt generation
    - apply variable substitution and build the prompt to pass to the AI agent
3. prompt execution - or dry run
    - select the appropriate provider
    - compose the command to delegate the task with the appropriate flags
    - either output a dry-run information, or execute the command
    - grab the output, and stream it to the log and to the terminal
4. output
    - grab the final output and send it to the user

## Code Refactoring

Research the current implementation and restrutrure it so to clearly reflect this waterfall phases into isolated modules to maximize maintainability and code evolution.

## Testing

I expect each phase to be testable in terms of unit tests to better capture the goals of each step.