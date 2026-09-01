import Fastify from 'fastify';
import { z } from 'zod';

const fastify = Fastify({ logger: true });

const telemetrySchema = z.object({
  deviceId: z.string(),
  temperature: z.number(),
  humidity: z.number(),
  vibration: z.number(),
  pressure: z.number(),
  machineState: z.string(),
  timestamp: z.string(),
  anomalyScore: z.number(),
  severity: z.enum(["NORMAL", "WARNING", "CRITICAL"])
});

fastify.get('/health', async (request, reply) => {
  return { status: 'healthy' };
});

fastify.post('/api/v1/telemetry', async (request, reply) => {
  try {
    const data = telemetrySchema.parse(request.body);
    console.log("Received valid telemetry from Edge:", data);
    return reply.status(201).send();
  } catch (error) {
    fastify.log.error(error);
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
