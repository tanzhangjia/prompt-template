"""
Prompt Template — Renderer

Replaces {{variable}} placeholders with actual values from the workflow.

That's it. No role system. No mode system. No rules engine. No template hooks.
Just variable substitution, like the LLM node's prompt editor does.
"""
import re

# Matches {{anything_inside}}
_VAR_RE = re.compile(r"\{\{([^}]+)\}\}")


def render_template(template: str, variables: dict, fallback: str = "") -> str:
    """Replace {{var_name}} with variable values.

    Args:
        template: String containing {{variable}} placeholders.
        variables: Dict of {name: value} to substitute.
        fallback: Text to use when a variable is not found (default: "").

    Returns:
        Rendered string with all placeholders replaced.
    """
    if not template:
        return ""

    def _replacer(match):
        var_name = match.group(1).strip()
        return str(variables.get(var_name, fallback))

    return _VAR_RE.sub(_replacer, template).strip()


def collect_variables(params: dict) -> dict:
    """Collect all available variables from the input.

    Everything in params (including nested) gets flattened by Dify's tool framework.
    We specifically handle:
    - Top-level scalar params (Dify injects them as-is)
    - extra_vars dict (user-provided key-value pairs)

    Dify's tool framework flattens workflow variable references like
    {{nodes.search.output}} into the parameters dict as string values.
    So we just pass them through directly.
    """
    variables = {}

    # Collect all params except special ones
    skip_keys = {"system_template", "user_template", "extra_vars", "fallback", "system_only"}

    for key, value in params.items():
        if key in skip_keys:
            continue

        # Dify passes {{nodes.xxx.yyy}} references as their resolved string values
        # If a key looks like "nodes.xxx.yyy", also alias by short name
        if isinstance(key, str) and value is not None:
            variables[key] = str(value)

    # Merge extra_vars last (they take priority)
    extra = params.get("extra_vars", {})
    if isinstance(extra, dict):
        for k, v in extra.items():
            variables[k] = str(v) if v is not None else ""

    return variables


def run(params: dict) -> list[dict]:
    """Main entry point for Dify tool framework.

    Returns list of dicts in Dify tool output format.
    """
    fallback = params.get("fallback", "")
    system_only = params.get("system_only", False)

    variables = collect_variables(params)

    results = []

    if system_only:
        # Single-output mode: just return rendered system_template as "prompt"
        rendered = render_template(
            params.get("system_template", ""), variables, fallback
        )
        results.append({"type": "text", "text": rendered})
        return results

    # Dual-output mode
    system_rendered = render_template(
        params.get("system_template", ""), variables, fallback
    )
    user_rendered = render_template(
        params.get("user_template", ""), variables, fallback
    )

    if system_rendered:
        results.append({"type": "text", "text": system_rendered, "name": "system_prompt"})
    else:
        results.append({"type": "text", "text": "", "name": "system_prompt"})

    if user_rendered:
        results.append({"type": "text", "text": user_rendered, "name": "user_prompt"})
    else:
        results.append({"type": "text", "text": "", "name": "user_prompt"})

    return results
