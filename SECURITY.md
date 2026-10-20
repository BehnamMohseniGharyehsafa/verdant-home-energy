# Security and data scope

Smart is an anonymous, publicly deployable **simulation**. It does not store household records, send physical-device commands, or require external API credentials. Scenario settings live in browser memory and reset on refresh.

Do not add actual smart-home credentials to source code or browser stores. A physical-device integration requires server-side secrets, authentication, authorization, validated commands and a separate review before public exposure. Keep `.env` and credentials out of version control.

For a security issue, use the repository's private GitHub security-reporting option when available. Do not post passwords, API tokens, personal home data or exploit details in a public issue. If private reporting is unavailable, contact the repository owner through an appropriate private channel.
