# coding=utf-8

# https://api.slack.com/legacy/custom-integrations/outgoing-webhooks
WEBHOOK_DATA = {
    "token": "test-token",

    "user_id": "U2147483697",
    "user_name": "Steve",
    "team_id": "T0001",
    "team_domain": "example",
    "channel_id": "C2147483705",
    "channel_name": "test",

    "timestamp": "1504640775.000005",
    "thread_ts": "1504640714.003543",

    "trigger_word": "googlebot:",
    "text": "googlebot: What is the air-speed velocity of an unladen swallow?"
}

# https://api.slack.com/interactivity/slash-commands
COMMAND_DATA = {
    "token": "gIkuvaNzQIHg97ATvDxqgjtO",

    "user_id": "U2147483697",
    "user_name": "Steve",
    "team_id": "T0001",
    "team_domain": "example",
    "enterprise_id": "E0001",
    "enterprise_name": "Globular%20Construct%20Inc",
    "channel_id": "C2147483705",
    "channel_name": "test",

    "command": "/weather",
    "text": "94070",

    "api_app_id": "ABC123",
    "trigger_id": "1234.5678.abc123",
    "response_url": "https://hooks.slack.com/commands/1234/5678"
}

# https://api.slack.com/reference/interaction-payloads/block-actions
BLOCK_ACTION_DATA = {
    "token": "9s8d9as89d8as9d8as989",

    "team": {
        "id": "T9TK3CUKW",
        "domain": "example"
    },
    "user": {
        "id": "UA8RXUSPL",
        "username": "jtorrance",
        "team_id": "T9TK3CUKW"
    },
    "channel": {
        "id": "CBR2V3XEX",
        "name": "review-updates"
    },

    "message": {
        "bot_id": "BAH5CA16Z",
        "type": "message",
        "text": "This content can't be displayed.",
        "user": "UAJ2RU415",
        "ts": "1548261231.000200",
    },
    "container": {
        "type": "message_attachment",
        "message_ts": "1548261231.000200",
        "attachment_id": 1,
        "channel_id": "CBR2V3XEX",
        "is_ephemeral": False,
        "is_app_unfurl": False
    },

    "type": "block_actions",
    "actions": [
        {
            "action_id": "WaXA",
            "block_id": "=qXel",
            "text": {
                "type": "plain_text",
                "text": "View",
                "emoji": True
            },
            "value": "click_me_123",
            "type": "button",
            "action_ts": "1548426417.840180"
        }
    ],

    "api_app_id": "ABC123",
    "trigger_id": "1234.5678.abc123",
    "response_url": "https://hooks.slack.com/actions/ABAB/CDCD/EFEF"
}
