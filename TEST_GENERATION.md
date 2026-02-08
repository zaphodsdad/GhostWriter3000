# Test Prose Generation - Quick Guide

## 🎉 You're Ready to Generate!

Everything is set up. Here's how to test the AI prose generation.

## Step 1: Start the Server

```bash
cd /home/john/prose-pipeline

# Install dependencies (if not done yet)
pip3 install --user -r backend/requirements.txt

# Start the server
cd backend
python3 -m app.main
```

You should see:
```
Data directories initialized at /home/john/prose-pipeline/data
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Leave this terminal running!** Open a new terminal for testing.

## Step 2: Test the API (In New Terminal)

### Check Health
```bash
curl http://localhost:8000/api/health
```

Should return:
```json
{"status":"healthy","timestamp":"...","version":"1.0.0"}
```

### Start Generation
```bash
curl -X POST http://localhost:8000/api/generations/start \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "scene-001", "max_iterations": 3}'
```

You'll get back a `generation_id` like:
```json
{
  "generation_id": "abc-123-def...",
  "scene_id": "scene-001",
  "status": "initialized",
  ...
}
```

**Copy that generation_id!** You'll need it.

### Check Progress
```bash
# Replace YOUR_GENERATION_ID with the actual ID
curl http://localhost:8000/api/generations/YOUR_GENERATION_ID
```

The `status` field shows progress:
- `generating` - Creating initial prose
- `critiquing` - Analyzing the prose
- `awaiting_approval` - **Ready for your decision!**

### View the Results

Once status is `awaiting_approval`, the response includes:
- `current_prose` - The generated prose
- `current_critique` - AI's analysis

Example response (truncated):
```json
{
  "generation_id": "abc-123",
  "status": "awaiting_approval",
  "current_iteration": 1,
  "current_prose": "The desert sun beat down mercilessly on Elena's expedition...",
  "current_critique": "The opening effectively establishes the harsh environment...",
  "can_revise": true
}
```

### Approve & Revise (If You Want Changes)
```bash
curl -X POST http://localhost:8000/api/generations/YOUR_GENERATION_ID/approve
```

This triggers a revision based on the critique. Wait a bit, then check progress again.

### Accept as Final (When Happy)
```bash
curl -X POST http://localhost:8000/api/generations/YOUR_GENERATION_ID/accept
```

This:
1. Saves the prose as final
2. Auto-generates a scene summary
3. Marks status as `completed`

Check one more time to see the summary:
```bash
curl http://localhost:8000/api/generations/YOUR_GENERATION_ID
```

Look for `scene_summary` in the response!

## Step 3: View All Available Endpoints

Open in your browser:
```
http://localhost:8000/docs
```

This shows the interactive API documentation where you can:
- See all endpoints
- Try them out directly
- View request/response formats

## Complete Workflow Example

```bash
# 1. Start generation
RESPONSE=$(curl -s -X POST http://localhost:8000/api/generations/start \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "scene-001", "max_iterations": 3}')

# Extract generation ID (requires jq)
GEN_ID=$(echo $RESPONSE | jq -r '.generation_id')
echo "Generation ID: $GEN_ID"

# 2. Wait and check status (repeat until awaiting_approval)
while true; do
  STATUS=$(curl -s http://localhost:8000/api/generations/$GEN_ID | jq -r '.status')
  echo "Status: $STATUS"

  if [ "$STATUS" = "awaiting_approval" ]; then
    break
  fi

  sleep 5
done

# 3. View the prose and critique
curl -s http://localhost:8000/api/generations/$GEN_ID | jq '.current_prose, .current_critique'

# 4. Accept as final
curl -s -X POST http://localhost:8000/api/generations/$GEN_ID/accept

# 5. Wait for summary generation
sleep 10

# 6. View final result with summary
curl -s http://localhost:8000/api/generations/$GEN_ID | jq '.final_prose, .scene_summary'
```

## What Models Are Being Used?

Check your `.env` file:
```bash
cat /home/john/prose-pipeline/.env | grep MODEL
```

You should see:
```
GENERATION_MODEL=anthropic/claude-opus-4-20250514
CRITIQUE_MODEL=anthropic/claude-sonnet-4-20250514
```

These are OpenRouter model names. You can change them to:
- `openai/gpt-4-turbo` - Use GPT-4 instead
- `google/gemini-pro-1.5` - Use Google's model
- `anthropic/claude-sonnet-4-20250514` - Use Sonnet for everything (cheaper)

Full list: https://openrouter.ai/models

## Timing Expectations

- **Initial generation**: 30-60 seconds (depends on model)
- **Critique**: 15-30 seconds
- **Revision**: 30-60 seconds
- **Summary**: 10-20 seconds

Total for one scene with 1 revision: ~2-3 minutes

## Cost Estimates (OpenRouter)

For scene-001 (1500-2000 word target):

- **Generation (Opus)**: ~$0.20-0.40 per attempt
- **Critique (Sonnet)**: ~$0.05-0.10
- **Revision (Opus)**: ~$0.20-0.40
- **Summary (Sonnet)**: ~$0.03-0.05

**Full scene with 2 revisions**: ~$1.00-1.50

## Troubleshooting

### "Connection refused"
- Make sure the server is running in the other terminal
- Check if port 8000 is available: `lsof -i :8000`

### "Generation not found"
- Double-check the generation_id
- Check if the file exists: `ls /home/john/prose-pipeline/data/generations/`

### "LLM API failed"
- Check your OpenRouter API key in `.env`
- Verify you have credits: https://openrouter.ai/credits
- Check server logs for detailed error

### Status stuck on "generating"
- Check server logs for errors
- The generation might be taking a while (large scene)
- OpenRouter rate limits might apply

### "Invalid model"
- Check model names in `.env`
- Visit https://openrouter.ai/models for valid names
- Format: `provider/model-name`

## Next Steps

Once this works:
1. Try generating scene-002 (it references scene-001!)
2. Build a simple web UI to make this easier
3. Add more scenes to your story
4. Experiment with different models

## Files to Check

**Server Logs**: Terminal where `python3 -m app.main` is running

**Generated Prose**:
```bash
cat /home/john/prose-pipeline/data/generations/YOUR_GENERATION_ID.json
```

**Scene Data**:
```bash
cat /home/john/prose-pipeline/data/scenes/scene-001.json
```

---

## 🎯 Quick Start (Copy-Paste This)

```bash
# Terminal 1: Start server
cd /home/john/prose-pipeline/backend
python3 -m app.main

# Terminal 2: Test generation
curl -X POST http://localhost:8000/api/generations/start \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "scene-001", "max_iterations": 3}' \
  | jq

# Wait 60 seconds, then check status (replace ID)
curl http://localhost:8000/api/generations/YOUR_ID | jq .status

# View prose and critique
curl http://localhost:8000/api/generations/YOUR_ID | jq '.current_prose, .current_critique'

# Accept it
curl -X POST http://localhost:8000/api/generations/YOUR_ID/accept

# View final with summary (wait 20 seconds first)
curl http://localhost:8000/api/generations/YOUR_ID | jq '.scene_summary'
```

**That's it! You're generating AI prose!** 🎉
