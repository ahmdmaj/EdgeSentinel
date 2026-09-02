import Fastify from 'fastify';
import { z } from 'zod';

const fastify = Fastify({ logger: true });

const telemetrySchema = z.object({
  eventId: z.string(),
  deviceId: z.string(),
  temperature: z.number(),
  humidity: z.number(),
  vibration: z.number(),
  pressure: z.number(),
  machineState: z.string(),
  timestamp: z.number(),
  anomalyScore: z.number(),
  severity: z.enum(["NORMAL", "WARNING", "CRITICAL"]),
  processingDecision: z.string(),
  edgeCpu: z.number(),
  networkLatency: z.number()
});

const processedEvents = new Set<string>();

fastify.get('/health', async (request, reply) => {
  return { status: 'healthy' };
});

fastify.post('/api/v1/telemetry', async (request, reply) => {
  try {
    const data = telemetrySchema.parse(request.body);
    
    // Idempotency Check
    if (processedEvents.has(data.eventId)) {
      console.log("Duplicate event detected and ignored");
      return reply.status(200).send({ message: "Already processed" });
    }
    
    processedEvents.add(data.eventId);
    // Basic limit to prevent memory leak
    if (processedEvents.size > 10000) {
      processedEvents.clear();
    }

    console.log("Received valid telemetry from Edge:", data);
    return reply.status(201).send();
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.log("Zod Validation Failed!");
      error.issues.forEach(issue => {
        console.log(`- Field '${issue.path.join('.')}' error: ${issue.message}`);
      });
    } else {
      fastify.log.error(error);
    }
    return reply.status(400).send({ error: "Invalid telemetry data" });
  }
});

const start = async () => {
  try {
    await fastify.listen({ port: 3000, host: '0.0.0.0' });
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
