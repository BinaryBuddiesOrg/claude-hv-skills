# forge

Maintainer tooling. End users do not install this; maintainers can:

```
/plugin install forge --marketplace BinaryBuddiesOrg/claude-hv-skills
```

```
agents/newadder.md          the self-improvement agent (research → gaps → vet → implement → gates → commit)
skills/newadder/            invocation: "hey newadder, work on video skills" or /forge:newadder video "anime styles"
  references/sources.md     per-domain research playbook
skills/new-skill/           (planned) scaffold a skill that passes lint on first try
```

Load from source while developing: `claude --plugin-dir ./plugins` from the repo root.

Status: **draft** — agent and playbook drafted; not yet run.
