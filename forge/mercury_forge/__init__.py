"""Mercury Forge: prompt-driven application forge, build templates and the desktop bridge server.

Builds on ``mercury-runtime``, which in turn builds on the ``mercury`` flywheel.
"""

from mercury_forge.templates import (
    APP_TEMPLATES,
    AppTemplate,
    BuiltAppArtifact,
    build_app_from_template,
    generate_or_load_spec_manifest,
    get_build_template,
    list_build_templates,
    verify_code_against_spec,
)

__all__ = [
    "APP_TEMPLATES",
    "AppTemplate",
    "BuiltAppArtifact",
    "build_app_from_template",
    "generate_or_load_spec_manifest",
    "get_build_template",
    "list_build_templates",
    "verify_code_against_spec",
]

__version__ = "0.4.0"
