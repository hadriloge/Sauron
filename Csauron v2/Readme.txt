You will need to create json files according to what you're trying to achieve:
You might also need to create the processed and screenshots folder. 

-----------------------------------------------
config.json
{
    "target_window": "Chrome.exe",
    "capture_interval": 0.5,
    "template_dir": ".venv/templates",
    "confidence_threshold": 0.6
}

-----------------------------------------------
templates_metadata.json
{
    "zombie1.jpg": {
        "category": "danger",
        "value": -5
    },
    "zombie2.jpg": {
        "category": "danger",
        "value": -5
    }
}

-----------------------------------------------
pixel_checks.json

{
    "pixel_checks": [
        {
            "name": "Thirst",
            "position": [
                1087,
                687
            ],
            "checks": [
                {
                    "range": [
                        [
                            170,
                            170,
                            170
                        ],
                        [
                            255,
                            255,
                            255
                        ]
                    ],
                    "state": "White"
                },
                {
                    "range": [
                        [
                            0,
                            180,
                            180
                        ],
                        [
                            100,
                            255,
                            255
                        ]
                    ],
                    "state": "Yellow"
                },
                {
                    "range": [
                        [
                            0,
                            0,
                            150
                        ],
                        [
                            100,
                            100,
                            255
                        ]
                    ],
                    "state": "Red"
                }
            ]
        },
        {
            "name": "Hunger",
            "position": [
                1118,
                683
            ],
            "checks": [
                {
                    "range": [
                        [
                            170,
                            170,
                            170
                        ],
                        [
                            255,
                            255,
                            255
                        ]
                    ],
                    "state": "White"
                },
                {
                    "range": [
                        [
                            0,
                            180,
                            180
                        ],
                        [
                            100,
                            255,
                            255
                        ]
                    ],
                    "state": "Yellow"
                },
                {
                    "range": [
                        [
                            0,
                            0,
                            150
                        ],
                        [
                            100,
                            100,
                            255
                        ]
                    ],
                    "state": "Red"
                }
            ]
        },
        {
            "name": "Blood",
            "position": [
                1185,
                697
            ],
            "checks": [
                {
                    "range": [
                        [
                            170,
                            170,
                            170
                        ],
                        [
                            255,
                            255,
                            255
                        ]
                    ],
                    "state": "White"
                },
                {
                    "range": [
                        [
                            0,
                            180,
                            180
                        ],
                        [
                            100,
                            255,
                            255
                        ]
                    ],
                    "state": "Yellow"
                },
                {
                    "range": [
                        [
                            0,
                            0,
                            150
                        ],
                        [
                            100,
                            100,
                            255
                        ]
                    ],
                    "state": "Red"
                }
            ]
        },
        {
            "name": "Health",
            "position": [
                1202,
                687
            ],
            "checks": [
                {
                    "range": [
                        [
                            170,
                            170,
                            170
                        ],
                        [
                            255,
                            255,
                            255
                        ]
                    ],
                    "state": "White"
                },
                {
                    "range": [
                        [
                            0,
                            180,
                            180
                        ],
                        [
                            100,
                            255,
                            255
                        ]
                    ],
                    "state": "Yellow"
                },
                {
                    "range": [
                        [
                            0,
                            0,
                            150
                        ],
                        [
                            100,
                            100,
                            255
                        ]
                    ],
                    "state": "Red"
                }
            ]
        }
    ]
}
