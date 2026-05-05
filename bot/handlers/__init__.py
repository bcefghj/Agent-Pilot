"""bot.handlers – Handler subpackage for event routing.

Re-exports key handler functions so other code can import from bot.handlers directly.
"""

from bot.handlers._common import (  # noqa: F401
    cancel_focus_expiry,
    check_and_send_achievements,
    extract_text,
    resolve_name,
    schedule_focus_expiry,
    set_scheduler,
    wm_append,
)
from bot.handlers.card_actions import on_card_action  # noqa: F401
from bot.handlers.mentor import (  # noqa: F401
    MENTOR_COMMANDS,
    handle_mentor_command,
    handle_onboarding_in_progress,
)
from bot.handlers.pilot import (  # noqa: F401
    PILOT_COMMANDS,
    handle_group_pilot,
    handle_pilot_command,
    pilot_help_text,
)
from bot.handlers.shield import (  # noqa: F401
    handle_focusing_p2p,
    handle_group_message,
)
