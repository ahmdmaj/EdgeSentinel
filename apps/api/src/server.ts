import Fastify from 'fastify';
import cors from '@fastify/cors';
import { collectDefaultMetrics, register, Counter } from 'prom-client';
import authPlugin from './plugins/auth';
import { authRoutes } from './modules/auth/auth.controller';
import { seedDefaultUsersIfEmpty } from './modules/auth/auth.service';
import { telemetryController, telemetryEvents, recentEvents } from './modules/telemetry/telemetry.controller';

collectDefaultMetrics();

const cloudEventsReceivedTotal = new Counter({
  name: 'cloud_events_received_total',
  help: 'Total number of telemetry events received by Cloud API'
});

const fastify = Fastify({ logger: true });
fastify.register(cors, { origin: '*' });

// Register Authentication & RBAC Plugin (enforces JWT_SECRET at startup per Section 13)
fastify.register(authPlugin);

const sseClients = new Set<any>();

// Wire real-time telemetry events to Prometheus metrics and SSE clients
telemetryEvents.on('telemetry_received', (data: any) => {
  cloudEventsReceivedTotal.inc();

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

// Mount Authentication routes under /api/v1 prefix (POST /api/v1/auth/login)
fastify.register(authRoutes, { prefix: '/api/v1' });

// Mount Telemetry routes under /api/v1 prefix (POST & GET /api/v1/telemetry with RBAC)
fastify.register(telemetryController, { prefix: '/api/v1' });

// Real-time telemetry event stream (SSE)
fastify.get('/api/v1/telemetry/stream', async (request, reply) => {
  const query = request.query as Record<string, string>;
  const queryToken = query?.token;

  if (queryToken) {
    try {
      fastify.jwt.verify(queryToken);
    } catch (err) {
      return reply.status(401).send({ error: { message: 'Unauthorized' } });
    }
  } else {
    try {
      await request.jwtVerify();
    } catch (err) {
      return reply.status(401).send({ error: { message: 'Unauthorized' } });
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

const start = async () => {
  try {
    // Seed initial users (admin, operator, viewer) if the users table is empty
    await seedDefaultUsersIfEmpty();

    await fastify.listen({ port: 3000, host: '0.0.0.0' });
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
