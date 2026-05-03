# Restricted Actions

Restricted actions are local operations that can change local access paths, initialize stored data, or alter maintenance state.

They are separated from normal Store and Retrieve flows.

## Guard Model

Restricted actions are evaluated by a shared local policy layer. Depending on the action, the policy can require:

- a valid Web mutation token;
- an unlocked UI session when face lock is enabled;
- a fresh restricted confirmation window;
- a typed action phrase;
- a deployment capability mode that permits the action.

The guard model is local-only. It does not rely on external approval devices or cloud services.

## CLI Behavior

CLI commands must use neutral wording and must not describe internal storage layout, trial order, or restricted recovery side effects.

No high-risk command should provide a single-step `--force` shortcut. Dangerous local actions should remain deliberate, typed, and auditable.

## WebUI Behavior

Normal WebUI navigation does not link to restricted routes. Hidden routes are UX concealment only and are not a security boundary by themselves.

Server-side policy checks remain required even when a route is not visible in navigation.

## Review Checks

Reviewers should test:

- direct restricted-route access without confirmation;
- wrong typed phrase;
- expired restricted confirmation;
- deployment capability mode that disables the action;
- Field Mode before and after restricted confirmation.
