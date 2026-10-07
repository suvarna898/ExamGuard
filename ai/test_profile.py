# LOW RISK PROFILE


LOW_RISK_PROFILE = {
    "integrity_score": 98,
    "risk_level": "Low",
    "event_penalty": 2,
    "face_presence_ratio": 98,
    "computed_at": "2026-09-29T15:00:00",

    "browser_events": [],

    "face_events": [
        {
            "started_at": "2026-09-29T14:30:00",
            "ended_at": "2026-09-29T14:30:36",
            "duration_seconds": 36
        }
    ]
}

# Integrity Score       = 98
# Risk Level            = Low
# Event Penalty         = 2
# Face Presence         = 98%
# Browser Events        = None
# Face absence          = 36 seconds


# Medium Risk Test Profile:

MEDIUM_RISK_PROFILE = {
    "integrity_score": 70,
    "risk_level": "Medium",
    "event_penalty": 25,
    "face_presence_ratio": 75,
    "computed_at": "2026-09-29T15:00:00",

    "browser_events": [
        {
            "event_type": "tab_switch",
            "event_time": "2026-09-29T14:10:00",
            "details": "Tab switched"
        },
        {
            "event_type": "tab_switch",
            "event_time": "2026-09-29T14:20:00",
            "details": "Tab switched"
        },
        {
            "event_type": "tab_switch",
            "event_time": "2026-09-29T14:35:00",
            "details": "Tab switched"
        },
        {
            "event_type": "focus_lost",
            "event_time": "2026-09-29T14:12:00",
            "details": "Browser focus lost"
        },
        {
            "event_type": "focus_lost",
            "event_time": "2026-09-29T14:25:00",
            "details": "Browser focus lost"
        },
        {
            "event_type": "right_click",
            "event_time": "2026-09-29T14:40:00",
            "details": "Right click detected"
        }
    ],

    "face_events": [
        {
            "started_at": "2026-09-29T14:15:00",
            "ended_at": "2026-09-29T14:18:00",
            "duration_seconds": 180
        },
        {
            "started_at": "2026-09-29T14:30:00",
            "ended_at": "2026-09-29T14:34:30",
            "duration_seconds": 270
        }
    ]
}


# Integrity Score       = 70
# Risk Level            = Medium
# Event Penalty         = 25
# Face Presence         = 75%

# Tab switches          = 3
# Focus losses          = 2
# Right clicks          = 1


# High Risk Test Profile

HIGH_RISK_PROFILE = {
    "integrity_score": 40,
    "risk_level": "High",
    "event_penalty": 40,
    "face_presence_ratio": 45,
    "computed_at": "2026-09-29T15:00:00",

    "browser_events": [
        {
            "event_type": "tab_switch",
            "event_time": "2026-09-29T14:05:00",
            "details": "Tab switched"
        },
        {
            "event_type": "tab_switch",
            "event_time": "2026-09-29T14:10:00",
            "details": "Tab switched"
        },
        {
            "event_type": "tab_switch",
            "event_time": "2026-09-29T14:15:00",
            "details": "Tab switched"
        },
        {
            "event_type": "tab_switch",
            "event_time": "2026-09-29T14:20:00",
            "details": "Tab switched"
        },
        {
            "event_type": "tab_switch",
            "event_time": "2026-09-29T14:25:00",
            "details": "Tab switched"
        },
        {
            "event_type": "focus_lost",
            "event_time": "2026-09-29T14:07:00",
            "details": "Browser focus lost"
        },
        {
            "event_type": "focus_lost",
            "event_time": "2026-09-29T14:12:00",
            "details": "Browser focus lost"
        },
        {
            "event_type": "focus_lost",
            "event_time": "2026-09-29T14:18:00",
            "details": "Browser focus lost"
        },
        {
            "event_type": "copy_attempt",
            "event_time": "2026-09-29T14:30:00",
            "details": "Copy attempt detected"
        },
        {
            "event_type": "paste_attempt",
            "event_time": "2026-09-29T14:32:00",
            "details": "Paste attempt detected"
        },
        {
            "event_type": "right_click",
            "event_time": "2026-09-29T14:35:00",
            "details": "Right click detected"
        },
        {
            "event_type": "right_click",
            "event_time": "2026-09-29T14:36:00",
            "details": "Right click detected"
        }
    ],

    "face_events": [
        {
            "started_at": "2026-09-29T14:05:00",
            "ended_at": "2026-09-29T14:15:00",
            "duration_seconds": 600
        },
        {
            "started_at": "2026-09-29T14:20:00",
            "ended_at": "2026-09-29T14:37:30",
            "duration_seconds": 1050
        }
    ]
}



# Integrity Score       = 40
# Risk Level            = High
# Event Penalty         = 40
# Face Presence         = 45%

# Tab switches          = 5
# Focus losses          = 3
# Copy attempts         = 1
# Paste attempts        = 1
# Right clicks          = 2