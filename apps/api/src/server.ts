import 'dotenv/config';

const requiredEnvVars = [
  'DATABASE_URL',
  'JWT_SECRET',
  'SEED_ADMIN_EMAIL',
  'SEED_ADMIN_PASSWORD'
];

const dummyValues = [
  'your-super-secret-jwt-key-here',
  'admin123',
  'secret',
  'admin'
];

for (const envVar of requiredEnvVars) {
  const value = process.env[envVar];
  if (!value) {
    console.error(`FATAL ERROR: Environment variable ${envVar} is missing.`);
    process.exit(1);
  }
  if (dummyValues.includes(value)) {
    console.error(`FATAL ERROR: Environment variable ${envVar} contains an insecure dummy value.`);
    process.exit(1);
  }
}

import Fastify from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import { collectDefaultMetrics, register, Counter } from 'prom-client';
import authPlugin from './plugins/auth';
import fastifyRateLimit from '@fastify/rate-limit';
import { authRoutes } from './modules/auth/auth.controller';
import { seedDefaultUsersIfEmpty } from './modules/auth/auth.service';
import { telemetryController, telemetryEvents, authEvents } from './modules/telemetry/telemetry.controller';
import { devicesController } from './modules/devices/devices.controller';

collectDefaultMetrics();

const cloudEventsReceivedTotal = new Counter({
  name: 'cloud_events_received_total',
  help: 'Total number of telemetry events received by Cloud API'
});

const telemetryReceivedTotal = new Counter({
  name: 'telemetry_received_total',
  help: 'Total number of telemetry events received by Cloud API, labeled by status',
  labelNames: ['status']
});

const authFailuresTotal = new Counter({
  name: 'auth_failures_total',
  help: 'Total number of failed authentication attempts'
});

import crypto from 'crypto';

const fastify = Fastify({ 
  logger: {
    level: 'info',
    serializers: {
      req(req) {
        return {
          method: req.method,
          url: req.url,
          reqId: req.id, // Ensure reqId is included in every log line
        };
      }
    }
  },
  genReqId: function (req) {
    return (req.headers['x-request-id'] as string) || crypto.randomUUID();
  },
  requestIdHeader: 'x-request-id',
  requestIdLogLabel: 'reqId'
});

// Security Plugins
fastify.register(helmet, {
  // Configured to not break Next.js development and standard usage
  contentSecurityPolicy: false, // Let Next.js handle its own CSP
  crossOriginResourcePolicy: { policy: "cross-origin" } 
});

const allowedOrigins = process.env.ALLOWED_ORIGINS 
  ? process.env.ALLOWED_ORIGINS.split(',')
  : ['http://localhost:3001', 'http://localhost']; // Safe development defaults

fastify.register(cors, {
  origin: (origin, cb) => {
    // Allow server-to-server requests (like from Next.js SSR) which have no origin
    if (!origin) {
      return cb(null, true);
    }
    if (allowedOrigins.includes(origin)) {
      cb(null, true);
      return;
    }
    // Block wildcard * in production
    cb(new Error('Not allowed by CORS'), false);
  }
});
fastify.register(fastifyRateLimit, {
  max: 100,
  timeWindow: '1 minute'
});

// Register Authentication & RBAC Plugin (enforces JWT_SECRET at startup per Section 13)
fastify.register(authPlugin);

const sseClients = new Set<any>();

// Wire real-time telemetry events to Prometheus metrics and SSE clients
telemetryEvents.on('telemetry_received', (event: any) => {
  cloudEventsReceivedTotal.inc();
  telemetryReceivedTotal.inc({ status: event.status || 'success' });

  // Broadcast to active SSE clients
  const eventString = `data: ${JSON.stringify(event.data || event)}\n\n`;
  sseClients.forEach((client) => {
    try {
      client.write(eventString);
    } catch {
      sseClients.delete(client);
    }
  });
});

authEvents.on('auth_failure', () => {
  authFailuresTotal.inc();
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

// Mount Devices routes under /api/v1 prefix
fastify.register(devicesController, { prefix: '/api/v1' });

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
