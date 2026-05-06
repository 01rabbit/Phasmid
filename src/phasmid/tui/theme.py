from textual.theme import Theme

PHASMID_DARK = Theme(
    name="phasmid-dark",
    primary="#00d7af",
    secondary="#005f87",
    accent="#00afff",
    background="#0d0d0d",
    surface="#1a1a1a",
    panel="#141414",
    error="#ff5f5f",
    warning="#ffaf00",
    success="#87d700",
    dark=True,
)

PHASMID_LIGHT = Theme(
    name="phasmid-light",
    primary="#005f87",
    secondary="#00afff",
    accent="#0087af",
    background="#f0f0f0",
    surface="#ffffff",
    panel="#e0e0e0",
    error="#d70000",
    warning="#875f00",
    success="#005f00",
    dark=False,
)
