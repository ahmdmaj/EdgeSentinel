import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { loginSchema } from './auth.schema';
import { login, AuthError } from './auth.service';

/**
 * Route handler for POST /api/v1/auth/login.
 * Validates request payload and delegates authentication to the service layer.
 * Strictly decoupled from Prisma.
 */
export async function handleLogin(request: FastifyRequest, reply: FastifyReply) {
  const body = (request.body as any) || {};

  // Support both 'email' and legacy 'username' input formats
  const normalizedPayload = {
    email: body.email ?? body.username,
    password: body.password,
  };

  // 1. Zod Validation
  const parseResult = loginSchema.safeParse(normalizedPayload);
  if (!parseResult.success) {
    return reply.status(422).send({
      error: {
        message: 'Validation failed: Invalid login payload',
        details: parseResult.error.issues.map((issue) => ({
          field: issue.path.join('.'),
          message: issue.message,
        })),
      },
    });
  }

  // 2. Delegate to Service Layer
  try {
    const user = await login(parseResult.data);

    // 3. Sign JWT containing user claims (userId, email, role)
    const token = (request.server as any).jwt.sign({
      userId: user.userId,
      email: user.email,
      role: user.role,
    });

    // 4. Return standard JSON envelope
    return reply.status(200).send({
      data: {
        token,
        user: {
          id: user.userId,
          email: user.email,
          role: user.role,
        },
      },
      token, // Compatibility for existing clients expecting root-level token
    });
  } catch (error: any) {
    if (error instanceof AuthError) {
      return reply.status(error.statusCode).send({
        error: {
          message: error.message,
        },
      });
    }

    request.log.error(error);
    return reply.status(500).send({
      error: {
        message: 'Internal server error during authentication',
      },
    });
  }
}

/**
 * Fastify plugin to register auth routes.
 * When mounted under prefix '/api/v1', exposes POST /api/v1/auth/login.
 */
export async function authRoutes(fastify: FastifyInstance) {
  fastify.post('/auth/login', handleLogin);
}

export const authController = authRoutes;
