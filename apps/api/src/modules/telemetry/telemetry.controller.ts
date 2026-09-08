import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { EventEmitter } from 'events';
import { telemetrySchema } from './telemetry.schema';
import { processTelemetry } from './telemetry.service';

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
  // Optional JWT verification if Authorization header is provided
  if (request.headers.authorization && typeof (request as any).jwtVerify === 'function') {
    try {
      await (request as any).jwtVerify();
    } catch (err) {
      return reply.status(401).send({
        error: {
          message: 'Unauthorized: Invalid or expired token',
        },
      });
    }
  }

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
 * Fastify plugin to register telemetry routes.
 * When registered with prefix '/api/v1', this exposes POST /api/v1/telemetry.
 */
export async function telemetryRoutes(fastify: FastifyInstance) {
  fastify.post('/telemetry', handleCreateTelemetry);
}

// Aliases for convenient importing
export const telemetryController = telemetryRoutes;
export const createTelemetryHandler = handleCreateTelemetry;
