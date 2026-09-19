# Logic prototype

Expose the smallest state model that answers the question. Keep domain logic separate from display handlers so the model can be inspected and useful pieces can carry forward. Choose a reducer, state machine, or plain functions based on the behavior being explored.

For a standalone walkthrough, prefer a self-contained HTML file when it fits. Show the question, readable state fields, and controls in the user's domain language. Update the visible state after each action and make reset available.

Support free exploration and repeatable scenarios for the happy path, a relevant edge case, and an illegal transition when the model has one. Start each guided scenario from a known state. Demonstrate invalid operations without silently corrupting the model.

Use the existing application's framework when understanding its integration is part of the question. Keep the demonstration shell disposable and the observations tied to the behavior under review.
