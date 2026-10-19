"""Example tickets for the UI dropdown.

Each label starts with the category a good triage should pick, but the labels are only a
guide for the person trying the app: the API never sees them. Several tickets are
deliberately tricky (angry tone about a small problem, a vague message, mixed topics) so
people can see the triage judge impact rather than wording.
"""

EXAMPLE_TICKETS: dict[str, str] = {
    # Hardware
    "Hardware: conveyor motor overheating": (
        "Conveyor motor on line 3 is overheating and smells burnt. We shut the line down "
        "twenty minutes ago and production has stopped. This is the second time this month."
    ),
    "Hardware: hydraulic press losing pressure": (
        "Hydraulic press #2 keeps dropping pressure mid-cycle since Tuesday. We are running "
        "at half speed. It has not stopped yet but it is getting worse every day."
    ),
    "Hardware: charger sparking": (
        "The forklift battery charger in bay 4 gave off sparks when I plugged it in and the "
        "cable casing is melted. I have unplugged it and put a cone in front of it."
    ),
    "Hardware: sensor reading drifts": (
        "The temperature sensor on oven 2 reads about 8 degrees lower than our handheld "
        "thermometer. It has been drifting for two weeks. Batches are still passing checks."
    ),
    "Hardware: barcode scanner not reading": (
        "The handheld barcode scanner at the packing desk won't read labels any more. The "
        "light comes on but nothing beeps. We can type codes by hand for now."
    ),
    # Software
    "Software: dashboard crashes": (
        "Ever since the update on Friday the reporting dashboard crashes as soon as I log "
        "in. I can still use the mobile app, so it isn't urgent, but it's slowing me down."
    ),
    "Software: API returning errors for everyone": (
        "Since 9:10 this morning every call to your API returns a 500 error. Our customers "
        "cannot place orders and we are losing sales by the minute. Nothing changed on our side."
    ),
    "Software: password reset email never arrives": (
        "I requested a password reset three times and no email has arrived, not even in "
        "spam. I need to get in to approve invoices before the end of the week."
    ),
    "Software: export is missing rows": (
        "When I export the monthly report to Excel the last 40 or so rows are missing. The "
        "on-screen table shows all of them. I noticed because the totals do not match."
    ),
    "Software: dark mode text unreadable": (
        "In dark mode on my phone the grey text on the settings page is almost impossible "
        "to read. Not a big deal, just thought you would want to know."
    ),
    # Billing
    "Billing: charged twice": (
        "Hi, I've just checked my statement and I've been charged twice for my monthly "
        "subscription. Same amount, same day. Can you sort this out please?"
    ),
    "Billing: charged after cancelling": (
        "I cancelled my subscription on the 3rd and confirmed it by email, yet I was "
        "charged again today. I never agreed to this charge and want it reversed now."
    ),
    "Billing: price went up": (
        "My invoice this month is 20% higher than last month and I was not told about a "
        "price change. Can you explain why before I pay it?"
    ),
    "Billing: need a VAT invoice": (
        "Could you please re-issue last month's invoice with our company VAT number on it? "
        "Our accountant needs it for the quarter end, no rush."
    ),
    # Other, and tricky ones
    "Other: asking for training": (
        "Do you offer any training for new operators on the packaging line? We have three "
        "people starting next quarter and would like to know the options."
    ),
    "Other: feature suggestion": (
        "It would be really handy if the app could show last week's tickets next to this "
        "week's. Just an idea for the future, thanks for the great product."
    ),
    "Tricky: angry tone, tiny problem": (
        "THIS IS UNACCEPTABLE!!! The logo on my invoice PDF is slightly blurry. I have "
        "been a customer for years and expect better. Fix this immediately!!!"
    ),
    "Tricky: calm tone, serious problem": (
        "Hello, just a quick note. The emergency stop button on press 5 did not stop the "
        "machine when I pressed it today. Everything else seems fine. Thanks."
    ),
    "Tricky: vague message": ("It's not working again. Please help."),
    "Tricky: billing and hardware mixed": (
        "We were charged for a machine rental in March but the machine arrived broken and "
        "has been sitting unused. Can we get a refund and a replacement?"
    ),
}
