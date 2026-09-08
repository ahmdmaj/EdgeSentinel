import fp from 'fastify-plugin';
import fastifyJwt from '@fastify/jwt';
import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';

export interface UserTokenPayload {
  userId: string;
  email: string;
  role: string;
}

declare module 'fastify' {
  interface FastifyInstance {
    authenticate: (request: FastifyRequest, reply: FastifyReply) => Promise<void>;
    requireRole: (allowedRoles: string[]) => (request: FastifyRequest, reply: FastifyReply) => Promise<void>;
  }
}

declare module '@fastify/jwt' {
  interface FastifyJWT {
    payload: UserTokenPayload;
    user: UserTokenPayload;
  }
}

/**
 * Authentication and RBAC Plugin.
 * Enforces JWT_SECRET presence at startup (Section 13) and decorates Fastify with
 * `authenticate` and `requireRole` middleware hooks.
 */
async function authPlugin(fastify: FastifyInstance) {
  const jwtSecret = process.env.JWT_SECRET;

  if (!jwtSecret || jwtSecret.trim() === '') {
    throw new Error(
      'FATAL: JWT_SECRET environment variable is missing. Authentication plugin cannot start (Section 13).'
    );
  }

  // Register JWT plugin
  await fastify.register(fastifyJwt, {
    secret: jwtSecret,
  });

  // Fastify decorator to authenticate requests via JWT
  fastify.decorate(
    'authenticate',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        await request.jwtVerify();
      } catch (err) {
        return reply.status(401).send({
          error: {
            message: 'Unauthorized: Invalid or missing authentication token',
          },
        });
      }
    }
  );

  // Fastify decorator to enforce Role-Based Access Control (RBAC)
  fastify.decorate(
    'requireRole',
    (allowedRoles: string[]) => {
      return async (request: FastifyRequest, reply: FastifyReply) => {
        // First verify authentication
        try {
          await request.jwtVerify();
        } catch (err) {
          return reply.status(401).send({
            error: {
              message: 'Unauthorized: Invalid or missing authentication token',
            },
          });
        }

        const user = request.user as UserTokenPayload | undefined;
        if (!user || !user.role || !allowedRoles.includes(user.role)) {
          return reply.status(403).send({
            error: {
              message: 'Forbidden: Insufficient permissions for this resource',
              requiredRoles: allowedRoles,
              currentRole: user?.role ?? null,
            },
          });
        }
      };
    }
  );
}

export default fp(authPlugin, {
  name: 'auth-plugin',
});
