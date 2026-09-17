import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { getDevices } from './devices.service';

/**
 * Route handler for GET /api/v1/devices.
 * Returns a list of all devices.
 */
export async function handleGetDevices(
  request: FastifyRequest,
  reply: FastifyReply
) {
  try {
    const devices = await getDevices();
    return reply.status(200).send({
      data: devices
    });
  } catch (error: any) {
    request.log.error(error);
    return reply.status(500).send({
      error: {
        message: 'Internal server error while fetching devices',
      },
    });
  }
}

/**
 * Fastify plugin to register devices routes.
 */
export async function devicesRoutes(fastify: FastifyInstance) {
  fastify.get(
    '/devices',
    {
      onRequest: [
        fastify.authenticate,
        fastify.requireRole(['VIEWER', 'OPERATOR', 'ADMIN']),
      ],
    },
    handleGetDevices
  );
}

export const devicesController = devicesRoutes;
