import Fastify from 'fastify';
import cors from '@fastify/cors';
import fastifyJwt from '@fastify/jwt';
import { collectDefaultMetrics, register, Counter } from 'prom-client';
import { telemetryController, telemetryEvents } from './modules/telemetry/telemetry.controller';

collectDefaultMetrics();

const cloudEventsReceivedTotal = new Counter({
  name: 'cloud_events_received_total',
  help: 'Total number of telemetry events received by Cloud API'
});

const fastify = Fastify({ logger: true });
fastify.register(cors, { origin: '*' });

fastify.register(fastifyJwt, {
  secret: process.env.JWT_SECRET || 'supersecret'
});

const recentEvents: any[] = [];
const sseClients = new Set<any>();

// Wire real-time telemetry events to Prometheus metrics and SSE clients
telemetryEvents.on('telemetry_received', (data: any) => {
  cloudEventsReceivedTotal.inc();

  recentEvents.unshift(data);
  if (recentEvents.length > 50) {
    recentEvents.pop();
  }

  // Broadcast to active SSE clients
  const eventString = `data: ${JSON.stringify(data)}\n\n`;
  sseClients.forEach((client) => {
    try {
      client.write(eventString);
    } catch {
      sseClients.delete(client);
    }
  });
});

// Health check endpoint
fastify.get('/health', async (request, reply) => {
  return { status: 'healthy' };
});

// Prometheus metrics endpoint
fastify.get('/metrics', async (request, reply) => {
  reply.header('Content-Type', register.contentType);
  return reply.send(await register.metrics());
});

// Auth login endpoint
fastify.post('/api/v1/auth/login', async (request, reply) => {
  const { username, password } = (request.body as any) || {};
  if (username === 'admin' && password === 'password') {
    const token = fastify.jwt.sign({ username });
    return reply.send({ token });
  }
  return reply.status(401).send({ error: 'Invalid credentials' });
});

// Fetch recent telemetry events (used by web UI initial load)
fastify.get('/api/v1/telemetry', async (request, reply) => {
  try {
    await request.jwtVerify();
  } catch (err) {
    return reply.status(401).send({ error: 'Unauthorized' });
  }
  return reply.send(recentEvents);
});

// Real-time telemetry event stream (SSE)
fastify.get('/api/v1/telemetry/stream', async (request, reply) => {
  const query = request.query as Record<string, string>;
  const queryToken = query?.token;

  if (queryToken) {
    try {
      fastify.jwt.verify(queryToken);
    } catch (err) {
      return reply.status(401).send({ error: 'Unauthorized' });
    }
  } else {
    try {
      await request.jwtVerify();
    } catch (err) {
      return reply.status(401).send({ error: 'Unauthorized' });
    }
  }

  reply.raw.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Access-Control-Allow-Origin': '*'
  });

  reply.raw.write(': ping\n\n');
  sseClients.add(reply.raw);

  request.raw.on('close', () => {
    sseClients.delete(reply.raw);
  });
});

// Register modular telemetry controller under /api/v1 prefix
// Handles POST /api/v1/telemetry
fastify.register(telemetryController, { prefix: '/api/v1' });

const start = async () => {
  try {
    await fastify.listen({ port: 3000, host: '0.0.0.0' });
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
