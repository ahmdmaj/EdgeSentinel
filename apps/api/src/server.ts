import Fastify from 'fastify';
import { z } from 'zod';
import cors from '@fastify/cors';
import fastifyJwt from '@fastify/jwt';

const fastify = Fastify({ logger: true });
fastify.register(cors, { origin: '*' });

fastify.register(fastifyJwt, {
  secret: process.env.JWT_SECRET || 'supersecret'
});

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
const recentEvents: any[] = [];
const sseClients = new Set<any>();

fastify.get('/health', async (request, reply) => {
  return { status: 'healthy' };
});

fastify.get('/api/v1/telemetry', async (request, reply) => {
  try {
    await request.jwtVerify();
  } catch (err) {
    return reply.status(401).send({ error: 'Unauthorized' });
  }
  return reply.send(recentEvents);
});

fastify.post('/api/v1/auth/login', async (request, reply) => {
  const { username, password } = (request.body as any) || {};
  if (username === 'admin' && password === 'password') {
    const token = fastify.jwt.sign({ username });
    return reply.send({ token });
  }
  return reply.status(401).send({ error: 'Invalid credentials' });
});

fastify.get('/api/v1/telemetry/stream', async (request, reply) => {
  try {
    await request.jwtVerify();
  } catch (err) {
    return reply.status(401).send({ error: 'Unauthorized' });
  }

  reply.raw.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Access-Control-Allow-Origin': '*'
  });
  
  // Send an initial ping to establish connection
  reply.raw.write(': ping\n\n');
  
  sseClients.add(reply.raw);
  
  request.raw.on('close', () => {
    sseClients.delete(reply.raw);
  });
});

fastify.post('/api/v1/telemetry', async (request, reply) => {
  try {
    await request.jwtVerify();
  } catch (err) {
    return reply.status(401).send({ error: 'Unauthorized' });
  }

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
    
    recentEvents.unshift(data);
    if (recentEvents.length > 50) {
      recentEvents.pop();
    }
    
    // Broadcast to active SSE clients
    const eventString = `data: ${JSON.stringify(data)}\n\n`;
    sseClients.forEach(client => {
      client.write(eventString);
    });

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
