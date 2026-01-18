"""
Story Structure Templates

Pre-defined narrative frameworks that can be applied to projects
to scaffold an outline with acts, chapters, and scenes.
"""

STORY_TEMPLATES = {
    "heros-journey": {
        "name": "Hero's Journey",
        "description": "Joseph Campbell's 12-stage monomyth structure. Classic adventure arc.",
        "acts": [
            {
                "title": "Act I - Departure",
                "description": "The hero leaves the ordinary world",
                "chapters": [
                    {
                        "title": "The Ordinary World",
                        "scenes": [
                            {
                                "title": "Ordinary World",
                                "outline": "Establish the hero's normal life before the adventure. Show their world, relationships, and any flaws or desires that will drive the story.",
                                "beats": [
                                    {"text": "Introduce the protagonist in their everyday environment"},
                                    {"text": "Show what they want vs. what they need"},
                                    {"text": "Hint at the larger world or conflict to come"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Call to Adventure",
                        "scenes": [
                            {
                                "title": "The Call",
                                "outline": "Something disrupts the hero's ordinary world. An invitation, threat, or opportunity presents itself that will change everything.",
                                "beats": [
                                    {"text": "The inciting incident occurs"},
                                    {"text": "The hero learns of the challenge or opportunity"},
                                    {"text": "Stakes are established"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Refusal of the Call",
                        "scenes": [
                            {
                                "title": "Hesitation",
                                "outline": "The hero resists the call. Fear, doubt, or obligation holds them back. This shows they're human and the stakes are real.",
                                "beats": [
                                    {"text": "Hero expresses doubt or fear"},
                                    {"text": "Reasons for staying are shown"},
                                    {"text": "The cost of refusing becomes clear"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Meeting the Mentor",
                        "scenes": [
                            {
                                "title": "The Mentor",
                                "outline": "A guide appears who provides wisdom, training, or a crucial gift. The mentor helps the hero commit to the journey.",
                                "beats": [
                                    {"text": "Mentor is introduced or revealed"},
                                    {"text": "Wisdom or tools are given"},
                                    {"text": "Hero gains confidence to proceed"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Crossing the Threshold",
                        "scenes": [
                            {
                                "title": "Into the Unknown",
                                "outline": "The hero commits to the adventure and leaves the ordinary world behind. There's no going back now.",
                                "beats": [
                                    {"text": "Hero makes the decision to go"},
                                    {"text": "They cross into the special world"},
                                    {"text": "First challenges of the new world appear"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Act II - Initiation",
                "description": "The hero faces tests and transforms",
                "chapters": [
                    {
                        "title": "Tests, Allies, Enemies",
                        "scenes": [
                            {
                                "title": "The New World",
                                "outline": "The hero navigates the special world. They learn the rules, make allies, identify enemies, and face a series of tests.",
                                "beats": [
                                    {"text": "Hero encounters the rules of the new world"},
                                    {"text": "Allies are gained"},
                                    {"text": "Enemies are revealed"},
                                    {"text": "Skills are tested and developed"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Approach to the Inmost Cave",
                        "scenes": [
                            {
                                "title": "Preparing for the Ordeal",
                                "outline": "The hero approaches the central challenge. Tension builds as they prepare for the greatest test yet.",
                                "beats": [
                                    {"text": "The central challenge is identified"},
                                    {"text": "Preparations are made"},
                                    {"text": "Doubts resurface"},
                                    {"text": "The team/hero commits to the approach"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "The Ordeal",
                        "scenes": [
                            {
                                "title": "Death and Rebirth",
                                "outline": "The hero faces their greatest fear or challenge. They may experience a metaphorical or literal death, then emerge transformed.",
                                "beats": [
                                    {"text": "Hero confronts the central challenge"},
                                    {"text": "All seems lost - the 'death' moment"},
                                    {"text": "Hero finds inner strength or revelation"},
                                    {"text": "Victory through transformation"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Reward",
                        "scenes": [
                            {
                                "title": "Seizing the Sword",
                                "outline": "Having survived the ordeal, the hero claims their reward. This could be a physical object, knowledge, or reconciliation.",
                                "beats": [
                                    {"text": "The prize is claimed"},
                                    {"text": "Hero reflects on what they've learned"},
                                    {"text": "Brief moment of celebration or peace"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Act III - Return",
                "description": "The hero returns home, transformed",
                "chapters": [
                    {
                        "title": "The Road Back",
                        "scenes": [
                            {
                                "title": "Chase or Pursuit",
                                "outline": "The hero begins the journey home but faces pursuit or complications. The adventure isn't over yet.",
                                "beats": [
                                    {"text": "Decision to return"},
                                    {"text": "Pursuit or new complication arises"},
                                    {"text": "Stakes are raised again"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Resurrection",
                        "scenes": [
                            {
                                "title": "The Final Test",
                                "outline": "The hero faces a final, most dangerous challenge. They must use everything they've learned. A climactic battle or confrontation.",
                                "beats": [
                                    {"text": "The final confrontation begins"},
                                    {"text": "Hero applies all lessons learned"},
                                    {"text": "Ultimate victory (or meaningful defeat)"},
                                    {"text": "Hero is fully transformed"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Return with the Elixir",
                        "scenes": [
                            {
                                "title": "Home Again",
                                "outline": "The hero returns to the ordinary world, but changed. They bring back something that benefits their community - wisdom, treasure, or healing.",
                                "beats": [
                                    {"text": "Return to the ordinary world"},
                                    {"text": "Show how hero has changed"},
                                    {"text": "The 'elixir' benefits others"},
                                    {"text": "New equilibrium established"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    },

    "three-act": {
        "name": "Three-Act Structure",
        "description": "Classic beginning-middle-end framework. Simple and flexible.",
        "acts": [
            {
                "title": "Act I - Setup",
                "description": "Introduce characters, world, and the central conflict (roughly 25%)",
                "chapters": [
                    {
                        "title": "Opening",
                        "scenes": [
                            {
                                "title": "Hook",
                                "outline": "Open with something compelling. Establish tone, introduce protagonist, hint at what's to come.",
                                "beats": [
                                    {"text": "Attention-grabbing opening"},
                                    {"text": "Introduce protagonist"},
                                    {"text": "Establish the world and tone"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Establishing the World",
                        "scenes": [
                            {
                                "title": "Status Quo",
                                "outline": "Show the protagonist's normal life. Establish what they want, what they fear, their relationships and flaws.",
                                "beats": [
                                    {"text": "Protagonist's daily life"},
                                    {"text": "Key relationships introduced"},
                                    {"text": "Desires and flaws hinted"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "The Inciting Incident",
                        "scenes": [
                            {
                                "title": "Disruption",
                                "outline": "Something happens that disrupts the status quo and sets the main conflict in motion. The protagonist's life will never be the same.",
                                "beats": [
                                    {"text": "The inciting event occurs"},
                                    {"text": "Protagonist reacts"},
                                    {"text": "Stakes become clear"}
                                ]
                            },
                            {
                                "title": "First Act Turn",
                                "outline": "The protagonist makes a choice or is forced into action. They commit to dealing with the central problem. End of Act I.",
                                "beats": [
                                    {"text": "Protagonist faces a decision"},
                                    {"text": "They commit to action"},
                                    {"text": "No turning back"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Act II - Confrontation",
                "description": "Rising action, complications, midpoint shift (roughly 50%)",
                "chapters": [
                    {
                        "title": "Rising Action",
                        "scenes": [
                            {
                                "title": "First Attempts",
                                "outline": "The protagonist begins pursuing their goal. Early successes or failures teach them about the challenge ahead.",
                                "beats": [
                                    {"text": "Protagonist takes action"},
                                    {"text": "Obstacles appear"},
                                    {"text": "Learning and adaptation"}
                                ]
                            },
                            {
                                "title": "Complications",
                                "outline": "Things get harder. New obstacles, betrayals, or revelations complicate the protagonist's path.",
                                "beats": [
                                    {"text": "New complications arise"},
                                    {"text": "Stakes increase"},
                                    {"text": "Pressure mounts"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Midpoint",
                        "scenes": [
                            {
                                "title": "The Shift",
                                "outline": "A major revelation or event changes everything. The protagonist's understanding of the situation fundamentally shifts. Often a false victory or false defeat.",
                                "beats": [
                                    {"text": "Major revelation or event"},
                                    {"text": "Everything changes"},
                                    {"text": "New understanding emerges"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Escalation",
                        "scenes": [
                            {
                                "title": "Raising Stakes",
                                "outline": "Post-midpoint, the antagonist responds to the protagonist's progress. The conflict intensifies.",
                                "beats": [
                                    {"text": "Antagonist pushes back"},
                                    {"text": "Conflict intensifies"},
                                    {"text": "Time pressure increases"}
                                ]
                            },
                            {
                                "title": "All Is Lost",
                                "outline": "The protagonist hits rock bottom. Their plan fails, allies desert them, or a devastating loss occurs. The darkest moment before the dawn.",
                                "beats": [
                                    {"text": "Major setback or loss"},
                                    {"text": "Hope seems gone"},
                                    {"text": "Protagonist at lowest point"}
                                ]
                            },
                            {
                                "title": "Second Act Turn",
                                "outline": "From the ashes, the protagonist finds new resolve. A revelation, reunion, or moment of clarity propels them toward the climax.",
                                "beats": [
                                    {"text": "Moment of reflection or revelation"},
                                    {"text": "New resolve emerges"},
                                    {"text": "Protagonist prepares for final push"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Act III - Resolution",
                "description": "Climax and resolution (roughly 25%)",
                "chapters": [
                    {
                        "title": "Climax",
                        "scenes": [
                            {
                                "title": "Final Confrontation",
                                "outline": "The protagonist faces the antagonist or central problem directly. Everything they've learned is put to the test. Maximum tension.",
                                "beats": [
                                    {"text": "Final confrontation begins"},
                                    {"text": "All skills and growth applied"},
                                    {"text": "Outcome hangs in balance"},
                                    {"text": "Decisive moment"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Falling Action",
                        "scenes": [
                            {
                                "title": "Aftermath",
                                "outline": "The immediate aftermath of the climax. Wounds are tended, victories acknowledged, losses mourned.",
                                "beats": [
                                    {"text": "Immediate aftermath"},
                                    {"text": "Characters react to outcome"},
                                    {"text": "Loose ends addressed"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Resolution",
                        "scenes": [
                            {
                                "title": "New Normal",
                                "outline": "Show the new status quo. How has the protagonist changed? What does their world look like now? End with resonance.",
                                "beats": [
                                    {"text": "New equilibrium established"},
                                    {"text": "Character growth demonstrated"},
                                    {"text": "Thematic resonance"},
                                    {"text": "Final image"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    },

    "save-the-cat": {
        "name": "Save the Cat",
        "description": "Blake Snyder's 15-beat structure. Popular in screenwriting, works great for novels.",
        "acts": [
            {
                "title": "Act I - Thesis",
                "description": "The 'before' snapshot of the protagonist's world",
                "chapters": [
                    {
                        "title": "Opening Image",
                        "scenes": [
                            {
                                "title": "Opening Image",
                                "outline": "A visual or scene that captures the protagonist's world before the story changes them. This will mirror the final image.",
                                "beats": [
                                    {"text": "Establish tone and mood"},
                                    {"text": "Show protagonist's current state"},
                                    {"text": "Visual representation of 'before'"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Theme Stated",
                        "scenes": [
                            {
                                "title": "Theme Stated",
                                "outline": "Someone (not the protagonist) states the theme of the story, usually in dialogue. The protagonist doesn't understand it yet.",
                                "beats": [
                                    {"text": "Theme expressed (often by minor character)"},
                                    {"text": "Protagonist doesn't yet understand"},
                                    {"text": "Seeds planted for later"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Setup",
                        "scenes": [
                            {
                                "title": "The Setup",
                                "outline": "Establish the protagonist's world, their flaws, the things that need fixing. Show what's missing in their life.",
                                "beats": [
                                    {"text": "Protagonist's world established"},
                                    {"text": "Flaws and needs shown"},
                                    {"text": "Supporting characters introduced"},
                                    {"text": "What's missing becomes clear"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Catalyst",
                        "scenes": [
                            {
                                "title": "Catalyst",
                                "outline": "The inciting incident. Something happens that will change everything. Life as the protagonist knows it is over.",
                                "beats": [
                                    {"text": "Life-changing event occurs"},
                                    {"text": "The old world is disrupted"},
                                    {"text": "No going back to before"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Debate",
                        "scenes": [
                            {
                                "title": "Debate",
                                "outline": "The protagonist debates what to do. Should they go? Can they do it? This is the last chance for fear before committing.",
                                "beats": [
                                    {"text": "Protagonist weighs options"},
                                    {"text": "Fear and doubt expressed"},
                                    {"text": "The question: What should I do?"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Act II - Antithesis",
                "description": "The upside-down version of the protagonist's world",
                "chapters": [
                    {
                        "title": "Break into Two",
                        "scenes": [
                            {
                                "title": "Break into Two",
                                "outline": "The protagonist makes a choice and enters Act II. They leave the thesis world and enter the antithesis. This must be a decision, not an accident.",
                                "beats": [
                                    {"text": "Protagonist makes active choice"},
                                    {"text": "Leaves the old world behind"},
                                    {"text": "Enters the upside-down world"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "B Story",
                        "scenes": [
                            {
                                "title": "B Story",
                                "outline": "Introduce the B Story, usually a love story or friendship. This relationship will carry the theme and help the protagonist learn.",
                                "beats": [
                                    {"text": "B Story character introduced or deepened"},
                                    {"text": "This relationship = thematic helper"},
                                    {"text": "Different perspective on the problem"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Fun and Games",
                        "scenes": [
                            {
                                "title": "Promise of the Premise",
                                "outline": "The 'fun and games' section. This is what the audience came for - the promise of the premise delivered. Fish out of water moments, training montages, exploring the new world.",
                                "beats": [
                                    {"text": "Deliver on the premise"},
                                    {"text": "Fun set pieces and scenes"},
                                    {"text": "Protagonist explores new world"},
                                    {"text": "Early wins or entertaining failures"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Midpoint",
                        "scenes": [
                            {
                                "title": "Midpoint",
                                "outline": "A false victory or false defeat. Stakes are raised. The clock starts ticking. The fun and games are over - things get serious.",
                                "beats": [
                                    {"text": "False victory or false defeat"},
                                    {"text": "Stakes raised to public/life-death"},
                                    {"text": "The clock starts ticking"},
                                    {"text": "No more games"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Bad Guys Close In",
                        "scenes": [
                            {
                                "title": "Bad Guys Close In",
                                "outline": "External pressure (bad guys) and internal pressure (team dissent, doubt) both increase. Things start falling apart.",
                                "beats": [
                                    {"text": "External forces tighten"},
                                    {"text": "Internal conflict grows"},
                                    {"text": "Things fall apart"},
                                    {"text": "Protagonist's flaws bite back"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "All Is Lost",
                        "scenes": [
                            {
                                "title": "All Is Lost",
                                "outline": "The lowest point. A death (literal or metaphorical) occurs. The old way is dead. The whiff of death hangs over everything.",
                                "beats": [
                                    {"text": "Rock bottom moment"},
                                    {"text": "Death (literal or metaphorical)"},
                                    {"text": "The old way is truly dead"},
                                    {"text": "All hope seems lost"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Dark Night of the Soul",
                        "scenes": [
                            {
                                "title": "Dark Night of the Soul",
                                "outline": "The protagonist wallows in hopelessness. They mourn what's lost. This is the darkness before the dawn - necessary for the transformation.",
                                "beats": [
                                    {"text": "Protagonist processes the loss"},
                                    {"text": "Wallowing in defeat"},
                                    {"text": "Mourning the old way"},
                                    {"text": "Seeds of revelation planted"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Act III - Synthesis",
                "description": "The protagonist combines old and new to create something better",
                "chapters": [
                    {
                        "title": "Break into Three",
                        "scenes": [
                            {
                                "title": "Break into Three",
                                "outline": "The solution! Thanks to the B Story character or a new insight, the protagonist figures out what to do. A and B stories cross.",
                                "beats": [
                                    {"text": "Eureka moment"},
                                    {"text": "A and B stories merge"},
                                    {"text": "Protagonist knows what to do"},
                                    {"text": "New resolve emerges"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Finale",
                        "scenes": [
                            {
                                "title": "Gathering the Team",
                                "outline": "The protagonist gathers allies, makes a plan, and executes it. They storm the castle.",
                                "beats": [
                                    {"text": "Team assembled"},
                                    {"text": "Plan formed"},
                                    {"text": "Execution begins"}
                                ]
                            },
                            {
                                "title": "High Tower Surprise",
                                "outline": "The plan hits a snag. There's a twist or complication. The protagonist must dig deeper.",
                                "beats": [
                                    {"text": "Unexpected complication"},
                                    {"text": "Plan goes sideways"},
                                    {"text": "Must improvise"}
                                ]
                            },
                            {
                                "title": "Dig Deep Down",
                                "outline": "The protagonist must use their newly learned lesson to win. The theme pays off. Character growth saves the day.",
                                "beats": [
                                    {"text": "Theme applied"},
                                    {"text": "Character growth demonstrated"},
                                    {"text": "Inner change enables outer victory"}
                                ]
                            },
                            {
                                "title": "Victory",
                                "outline": "The protagonist wins (or loses meaningfully). The external problem is resolved. Bad guys are defeated.",
                                "beats": [
                                    {"text": "Final confrontation"},
                                    {"text": "Victory achieved"},
                                    {"text": "External problem resolved"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Final Image",
                        "scenes": [
                            {
                                "title": "Final Image",
                                "outline": "The opposite of the opening image. Show how the protagonist and their world have changed. Prove the transformation.",
                                "beats": [
                                    {"text": "Mirror the opening image"},
                                    {"text": "Show the change"},
                                    {"text": "Prove the transformation"},
                                    {"text": "End with resonance"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    },

    "seven-point": {
        "name": "Seven-Point Structure",
        "description": "Dan Wells' streamlined structure. Great for plotters who want flexibility.",
        "acts": [
            {
                "title": "Beginning",
                "description": "Setup and first turn",
                "chapters": [
                    {
                        "title": "Hook",
                        "scenes": [
                            {
                                "title": "Hook",
                                "outline": "The opposite of the resolution. Show the protagonist in their 'before' state - the state that will be transformed by story's end.",
                                "beats": [
                                    {"text": "Protagonist in opposite state of resolution"},
                                    {"text": "Establish what needs to change"},
                                    {"text": "Hook the reader's interest"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Plot Turn 1",
                        "scenes": [
                            {
                                "title": "Plot Turn 1",
                                "outline": "The call to adventure. Something introduces the conflict and starts the protagonist's journey toward change.",
                                "beats": [
                                    {"text": "Conflict introduced"},
                                    {"text": "Journey begins"},
                                    {"text": "New world or situation entered"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Middle",
                "description": "Rising action through midpoint",
                "chapters": [
                    {
                        "title": "Pinch 1",
                        "scenes": [
                            {
                                "title": "Pinch 1",
                                "outline": "Apply pressure. Something goes wrong that forces the protagonist to act. The villain or problem shows its teeth.",
                                "beats": [
                                    {"text": "Pressure applied"},
                                    {"text": "Antagonist force shown"},
                                    {"text": "Protagonist forced to respond"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Midpoint",
                        "scenes": [
                            {
                                "title": "Midpoint",
                                "outline": "The protagonist moves from reaction to action. They stop running and start fighting. A major shift in approach.",
                                "beats": [
                                    {"text": "Shift from reactive to proactive"},
                                    {"text": "Protagonist commits fully"},
                                    {"text": "Major revelation or decision"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Pinch 2",
                        "scenes": [
                            {
                                "title": "Pinch 2",
                                "outline": "The antagonist strikes back hard. Apply maximum pressure. Remove the protagonist's safety nets. The jaws of defeat.",
                                "beats": [
                                    {"text": "Antagonist's counter-attack"},
                                    {"text": "Safety nets removed"},
                                    {"text": "Maximum pressure applied"},
                                    {"text": "All seems lost"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "End",
                "description": "Final turn and resolution",
                "chapters": [
                    {
                        "title": "Plot Turn 2",
                        "scenes": [
                            {
                                "title": "Plot Turn 2",
                                "outline": "The protagonist gains the final piece - the power, knowledge, or ally needed to resolve the story. The last puzzle piece.",
                                "beats": [
                                    {"text": "Final piece obtained"},
                                    {"text": "Path to victory revealed"},
                                    {"text": "Protagonist ready for final confrontation"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Resolution",
                        "scenes": [
                            {
                                "title": "Resolution",
                                "outline": "The climax and ending. The protagonist uses what they've gained to resolve the conflict. Show the transformation complete.",
                                "beats": [
                                    {"text": "Final confrontation"},
                                    {"text": "Victory (or meaningful defeat)"},
                                    {"text": "Transformation complete"},
                                    {"text": "New equilibrium"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    },

    "kishotenketsu": {
        "name": "Kishōtenketsu",
        "description": "East Asian 4-act structure. No central conflict required - great for literary fiction.",
        "acts": [
            {
                "title": "Ki (Introduction)",
                "description": "Introduce the characters and setting",
                "chapters": [
                    {
                        "title": "Introduction",
                        "scenes": [
                            {
                                "title": "Ki - Introduction",
                                "outline": "Introduce the characters and their world. Establish the baseline. No conflict needed yet - just set the stage.",
                                "beats": [
                                    {"text": "Introduce characters"},
                                    {"text": "Establish setting"},
                                    {"text": "Show normal life"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Shō (Development)",
                "description": "Develop the elements introduced",
                "chapters": [
                    {
                        "title": "Development",
                        "scenes": [
                            {
                                "title": "Shō - Development",
                                "outline": "Develop the characters and situations. Deepen understanding. Build on what was introduced without yet introducing the twist.",
                                "beats": [
                                    {"text": "Deepen character understanding"},
                                    {"text": "Develop relationships"},
                                    {"text": "Build on established elements"},
                                    {"text": "Create anticipation"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Ten (Twist)",
                "description": "A surprising turn that recontextualizes everything",
                "chapters": [
                    {
                        "title": "The Twist",
                        "scenes": [
                            {
                                "title": "Ten - Twist",
                                "outline": "Introduce something unexpected that changes the reader's understanding. Not a conflict - a new perspective. Something that doesn't seem to fit but will make sense.",
                                "beats": [
                                    {"text": "Unexpected element introduced"},
                                    {"text": "Apparent non-sequitur"},
                                    {"text": "Reader's understanding shifts"},
                                    {"text": "New perspective emerges"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Ketsu (Conclusion)",
                "description": "Reconcile the twist with everything before",
                "chapters": [
                    {
                        "title": "Reconciliation",
                        "scenes": [
                            {
                                "title": "Ketsu - Conclusion",
                                "outline": "Bring everything together. Show how the twist connects to and recontextualizes the earlier sections. The reader sees the whole picture.",
                                "beats": [
                                    {"text": "Connect twist to earlier elements"},
                                    {"text": "New understanding crystallizes"},
                                    {"text": "Thematic resonance"},
                                    {"text": "Satisfying conclusion"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    },

    "five-act": {
        "name": "Five-Act Structure",
        "description": "Shakespearean structure. Classic for drama and tragedy.",
        "acts": [
            {
                "title": "Act I - Exposition",
                "description": "Setup the world, characters, and conflict",
                "chapters": [
                    {
                        "title": "Exposition",
                        "scenes": [
                            {
                                "title": "Exposition",
                                "outline": "Introduce the setting, main characters, and the situation. Establish the world before the conflict disrupts it.",
                                "beats": [
                                    {"text": "Establish setting and mood"},
                                    {"text": "Introduce main characters"},
                                    {"text": "Show status quo"}
                                ]
                            },
                            {
                                "title": "Inciting Incident",
                                "outline": "The event that sets the main conflict in motion. Something happens that will change everything.",
                                "beats": [
                                    {"text": "Inciting event occurs"},
                                    {"text": "Conflict established"},
                                    {"text": "Stakes revealed"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Act II - Rising Action",
                "description": "Complications and escalating conflict",
                "chapters": [
                    {
                        "title": "Rising Action",
                        "scenes": [
                            {
                                "title": "Complications",
                                "outline": "The conflict deepens. Obstacles multiply. Relationships are tested. The protagonist's path becomes harder.",
                                "beats": [
                                    {"text": "Conflict deepens"},
                                    {"text": "Obstacles multiply"},
                                    {"text": "Character relationships tested"}
                                ]
                            },
                            {
                                "title": "Building Tension",
                                "outline": "Tension continues to build. Subplots develop. The protagonist makes progress but faces increasing resistance.",
                                "beats": [
                                    {"text": "Tension increases"},
                                    {"text": "Subplots develop"},
                                    {"text": "Resistance grows"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Act III - Climax",
                "description": "The turning point - the highest point of tension",
                "chapters": [
                    {
                        "title": "Climax",
                        "scenes": [
                            {
                                "title": "The Turning Point",
                                "outline": "The moment of highest tension. A critical decision or event that determines everything. The point of no return.",
                                "beats": [
                                    {"text": "Maximum tension reached"},
                                    {"text": "Critical moment arrives"},
                                    {"text": "Irreversible action taken"},
                                    {"text": "Outcome determined"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Act IV - Falling Action",
                "description": "Consequences unfold from the climax",
                "chapters": [
                    {
                        "title": "Falling Action",
                        "scenes": [
                            {
                                "title": "Consequences",
                                "outline": "The aftermath of the climax plays out. Events spiral toward the inevitable conclusion. Characters deal with what's happened.",
                                "beats": [
                                    {"text": "Consequences of climax unfold"},
                                    {"text": "Characters react and adapt"},
                                    {"text": "Move toward resolution"}
                                ]
                            },
                            {
                                "title": "Final Suspense",
                                "outline": "A final moment of tension or uncertainty before the resolution. One last complication or doubt.",
                                "beats": [
                                    {"text": "Final complication or doubt"},
                                    {"text": "Last moment of suspense"},
                                    {"text": "Set up for resolution"}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "title": "Act V - Denouement",
                "description": "Resolution and new equilibrium",
                "chapters": [
                    {
                        "title": "Resolution",
                        "scenes": [
                            {
                                "title": "Denouement",
                                "outline": "The final resolution. All threads are tied up. The new normal is established. In tragedy, this is where the fall is complete.",
                                "beats": [
                                    {"text": "Conflicts resolved"},
                                    {"text": "Loose ends tied"},
                                    {"text": "New equilibrium shown"},
                                    {"text": "Final image/moment"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
}


def get_template(template_id: str) -> dict | None:
    """Get a template by ID."""
    return STORY_TEMPLATES.get(template_id)


def list_templates() -> list[dict]:
    """List all available templates with basic info."""
    return [
        {
            "id": template_id,
            "name": template["name"],
            "description": template["description"],
            "act_count": len(template["acts"]),
            "scene_count": sum(
                len(scene)
                for act in template["acts"]
                for chapter in act["chapters"]
                for scene in [chapter["scenes"]]
            )
        }
        for template_id, template in STORY_TEMPLATES.items()
    ]
