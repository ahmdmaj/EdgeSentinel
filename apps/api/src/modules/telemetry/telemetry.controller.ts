import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { EventEmitter } from 'events';
import { telemetrySchema } from './telemetry.schema';
import { processTelemetry } from './telemetry.service';
import type { UserTokenPayload } from '../../plugins/auth';

// Ensure Fastify recognizes the authenticate and requireRole decorators
declare module 'fastify' {
  interface FastifyInstance {
    authenticate: (request: FastifyRequest, reply: FastifyReply) => Promise<void>;
    requireRole: (allowedRoles: string[]) => (request: FastifyRequest, reply: FastifyReply) => Promise<void>;
  }
}

// In-memory buffer for recent telemetry events (used by GET /telemetry and SSE)
export const recentEvents: any[] = [];

// Event emitter to notify SSE streaming and metrics listeners without coupling controller to them
export const telemetryEvents = new EventEmitter();

/**
 * Route handler for POST /api/v1/telemetry.
 * Validates input using Zod and delegates data persistence to the service layer.
 * Strictly decoupled from Prisma.
 */
export async function handleCreateTelemetry(
  request: FastifyRequest,
  reply: FastifyReply
) {
  // 1. Zod Validation
  const parseResult = telemetrySchema.safeParse(request.body);
  if (!parseResult.success) {
    return reply.status(422).send({
      error: {
        message: 'Validation failed: Invalid telemetry data payload',
        details: parseResult.error.issues.map((issue) => ({
          field: issue.path.join('.'),
          message: issue.message,
        })),
      },
    });
  }

  // 2. Delegate to Service Layer
  try {
    const result = await processTelemetry(parseResult.data);

    // Track recent events buffer
    recentEvents.unshift(parseResult.data);
    if (recentEvents.length > 50) {
      recentEvents.pop();
    }

    // Emit event for real-time subscribers (SSE, metrics counters)
    telemetryEvents.emit('telemetry_received', parseResult.data);

    // 3. Return standardized JSON response
    const statusCode = result.isDuplicate ? 200 : 201;
    return reply.status(statusCode).send({
      data: {
        message: result.message,
        ...result.data,
      },
    });
  } catch (error: any) {
    request.log.error(error);
    return reply.status(500).send({
      error: {
        message: 'Internal server error while processing telemetry',
      },
    });
  }
}

/**
 * Route handler for GET /api/v1/telemetry.
 * Returns the most recent telemetry events for authenticated dashboards.
 */
export async function handleGetTelemetry(
  request: FastifyRequest,
  reply: FastifyReply
) {
  return reply.status(200).send(recentEvents);
}

/**
 * Fastify plugin to register telemetry routes with onRequest RBAC middleware hooks.
 * When registered with prefix '/api/v1', this exposes:
 *   - POST /api/v1/telemetry (requires OPERATOR or ADMIN role)
 *   - GET  /api/v1/telemetry (requires VIEWER, OPERATOR, or ADMIN role)
 */
export async function telemetryRoutes(fastify: FastifyInstance) {
  // POST /api/v1/telemetry: Protected by authenticate & requireRole(['OPERATOR', 'ADMIN'])
  fastify.post(
    '/telemetry',
    {
      onRequest: [
        fastify.authenticate,
        fastify.requireRole(['OPERATOR', 'ADMIN']),
      ],
    },
    handleCreateTelemetry
  );

  // GET /api/v1/telemetry: Protected by authenticate & requireRole(['VIEWER', 'OPERATOR', 'ADMIN'])
  fastify.get(
    '/telemetry',
    {
      onRequest: [
        fastify.authenticate,
        fastify.requireRole(['VIEWER', 'OPERATOR', 'ADMIN']),
      ],
    },
    handleGetTelemetry
  );
}

// Aliases for convenient importing
export const telemetryController = telemetryRoutes;
export const createTelemetryHandler = handleCreateTelemetry;
export const getTelemetryHandler = handleGetTelemetry;
