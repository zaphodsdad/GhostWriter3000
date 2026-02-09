# CYOABot + Prose Pipeline: Community-Driven Serialized Fiction

## The Idea

A sequel to "The Empire of the Cat" (UnDead Animals Book 1) written by AI, steered by community votes, with reader sentiment from Discord subtly influencing the narrative. The author (John) provides a starting point and the system runs autonomously from there.

Readers vote on **what** happens. Discord discussion influences **how** it's written.

## Architecture Overview

### Components

| Component | Role | Status |
|-----------|------|--------|
| **johnaburks.com** | Primary reader interface — read scenes, view choices, cast votes | Exists (needs voting UI) |
| **CYOABot** | Orchestrator — runs the generation loop, collects votes, posts results | Exists as Discord bot (needs this workflow) |
| **prose-pipeline** | Writing engine — generates prose using characters, world, memory, style | Running, 66 MCP tools |
| **Persona MCP** | Sentiment layer — monitors Discord, extracts reader interests/sentiment | Not built yet (Phase 3) |
| **Discord** | Community discussion — readers theorize, argue, hype | Exists |

### Data Flow

```
Website vote (WHAT happens) ──→ CYOABot ──→ prose-pipeline ──→ New scene
Discord discussion (HOW) ──→ Persona MCP ──→ soft context ──↗
```

## The Loop

Each cycle produces one scene (~2-5k words). The loop runs continuously (or on a schedule — daily, every few days, whatever cadence works for reader engagement).

### Step 1: Generate Scene
- CYOABot calls prose-pipeline MCP tools
- prose-pipeline assembles context: characters, world, memory, style guide, previous scenes
- If Persona MCP is active: reader sentiment is included as additional context
- Generation engine: context + outline → prose → critique → revise → accept
- Scene is marked as canon, memory is updated

### Step 2: Generate Choices
- After the scene is written, CYOABot asks the AI (via prose-pipeline or directly):
  - "Given the current story state, propose two meaningfully different directions"
- Each choice is 1-2 paragraphs describing what would happen next
- Choices should be narratively viable, dramatically different, and both interesting
- Bad choices: "go left" vs "go right"
- Good choices: "Bonan leads a frontal assault on the cat stronghold" vs "Meme infiltrates alone using her knowledge of the city's underbelly"

### Step 3: Present to Readers
- New scene + both choices posted to johnaburks.com
- Scene + choices also posted to Discord
- Voting opens on the website (primary ballot)
- Discord discussion happens naturally

### Step 4: Collect Input
- Website tallies votes over the voting period
- (Phase 3) Persona MCP monitors Discord discussion:
  - Reader sentiment: "everyone loves Meme", "people are worried about Rubi"
  - Theories: "someone thinks Kitkat has a boss"
  - Requests: "more world-building about the sleeping men"
  - This becomes soft context — flavor, not direction

### Step 5: Build Next Scene Outline
- Winning vote becomes the scene's outline/premise
- Losing vote is discarded (not canon)
- Persona MCP sentiment feeds into `additional_notes` or `tone` on the scene
- CYOABot creates the new scene in prose-pipeline via MCP
- Go to Step 1

## Key Design Decisions

### Linear, Not Branching
The community writes ONE story. Every vote is canon. The losing option disappears. There's no branching tree to manage. This means:
- prose-pipeline's existing linear structure (acts → chapters → scenes) works perfectly
- Series memory accumulates linearly
- Continuity checking works without modification
- The sequel is just Book 2 in the "undead-animals" series

### Scenes, Not Chapters
Each generation cycle produces a scene (~2-5k words), not a chapter. Reasons:
- Faster cadence between votes = more engagement
- Easier for the AI to generate well
- Better context assembly (smaller chunks)
- Scenes group into chapters after the fact

### Cheap AI is Fine
The whole architecture is designed so the LLM doesn't need to be brilliant — it needs to be well-informed. With full series context (characters, world, memory, style guide, recent scenes), even DeepSeek or similar models can produce good output. The critique-revision loop catches quality issues. The expensive part is context, not intelligence.

### Vote Determines Direction, Discussion Influences Flavor
The binary vote is the hard steering input. Discord sentiment is soft context — it influences emphasis, character focus, tone, and pacing, but never overrides the vote. This means:
- Phase 1-2 work without Persona MCP at all (just votes)
- Phase 3 adds the sentiment layer as an enhancement
- Readers feel heard beyond the binary choice

## What Prose-Pipeline Provides (Already Built)

- **Series system**: Book 2 inherits characters, world, memory from Book 1
- **Character persistence**: Bonan, Rubi, Meme, etc. with full descriptions and arcs
- **World context**: Locations, factions, magic systems, politics
- **Series memory**: Plot events, character state changes, world facts — with decay and staleness
- **Style learning**: Learns John's voice from edits to match his prose style
- **Generation engine**: Context assembly → generation → critique → revision → acceptance
- **Continuity checking**: LLM-based contradiction detection across the series
- **Causal chains**: Plot coherence tracking
- **66 MCP tools**: Full programmatic access to everything above

## What Needs to Be Built

### Phase 1: Prepare the Source Material (prose-pipeline)
- [ ] Split Book 1 chapters at `***` scene breaks into proper scene records
- [ ] Re-run extraction on smaller scenes for cleaner character/world/memory data
- [ ] Verify series context is complete and accurate

### Phase 2: CYOABot Orchestration Loop
- [ ] CYOABot connects to prose-pipeline via MCP
- [ ] Create Book 2 project in "undead-animals" series
- [ ] Implement the generate → choices → vote → generate loop
- [ ] Build voting UI on johnaburks.com (simple: show scene, two choices, vote button, countdown)
- [ ] Post scenes + choices to Discord
- [ ] Accept starting premise from John, then run autonomously

### Phase 3: Persona MCP Sentiment Layer
- [ ] Persona MCP monitors Discord channels
- [ ] Periodically extracts reader sentiment via LLM summarization
- [ ] Sentiment fed as soft context into prose-pipeline generation
- [ ] Reader interest tracking (which characters, plot threads get the most discussion)

### Phase 4: Polish
- [ ] Scene → chapter grouping (auto or manual)
- [ ] Reading archive on johnaburks.com (read the full story so far)
- [ ] Vote history / stats page
- [ ] Email notifications for new scenes
- [ ] Engagement metrics

## The Portfolio Angle

This is genuinely novel:
- AI-generated serialized fiction
- Community-steered via voting
- Sentiment-aware generation from Discord discussion
- Multi-model architecture (cheap generation + smart critique)
- Built on a full writing pipeline with memory, continuity, and style learning

It's not a tutorial project. It's a product. And it showcases the entire stack: prose-pipeline, Persona MCP, CYOABot, johnaburks.com — all working together.

## Source Material

- **Book 1**: "The Empire of the Cat" by John Burks (UnDead Animals series)
- **Series**: "undead-animals" in prose-pipeline
- **Existing data**: 13 chapters, characters, world elements, series memory (all extracted)
- **Starting point for Book 2**: TBD by John — a premise/scene that kicks off the sequel
