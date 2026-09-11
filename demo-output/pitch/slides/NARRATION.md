# Opening

I asked for gaming peripherals. But for my game, I only needed the headphones. Generating a model isn’t the same as getting the asset you actually need.

# Who it helps

SlashData estimated eleven million game developers worldwide in early twenty twenty-four. Our rough estimate is that two to five million creators work in the broader imported-asset workflow. Not all need help. We focus on solo developers and small teams without a dedicated technical artist.

# Human, AI and tools

The human sets the goal and approves changes. The AI interprets measurements and images, then proposes supported repairs. Deterministic tools make the edits and check the result. The agent guides the process; it doesn’t replace your judgment.

# More than headphones

The toolbox also handles scale, grounding, pivots, quarter-turn rotations, naming, simplification and exact geometry cleanup. It builds on open-source projects including Strands, pygltflib, NumPy, Trimesh and meshoptimizer. The same repair engine serves both the command line and the agent.

# Architecture: request flow

ECS hosts the website. SQS and Lambda dispatch work to AgentCore, where the Strands agent runs separately from the web request.

# Architecture: saved work

S3 stores models and evidence. DynamoDB tracks progress. The browser polls for updates and downloads the result.

# Architecture: protection

Cognito handles sign-in. IAM scopes access. Secrets Manager holds the API key, while alerts and spending safeguards support operations.

# Architecture: models

The application runs on AWS. Luna calls go to OpenAI; Kimi is available through Amazon Bedrock.

# Why Luna

We tested Luna, Kimi, Muse and Gemini on real assets. Luna’s visual selection and multi-step results made it our current choice. We consider quality, latency and cost, including retries.

# Closing

Asset Shepherd. Less asset cleanup. More time making your game.

Thank you to the Agents for Humans organizers, judges, and open-source community. I'd love to hear what you'd make with Asset Shepherd.
