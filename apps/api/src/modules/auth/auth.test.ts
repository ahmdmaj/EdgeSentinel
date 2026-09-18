import { describe, it, expect, vi, beforeEach } from 'vitest';
import Fastify from 'fastify';
import authPlugin from '../../plugins/auth';
import { authRoutes } from './auth.controller';
import * as authService from './auth.service';

describe('Auth Module Integration', () => {
  let fastify: any;

  beforeEach(async () => {
    fastify = Fastify();
    
    // Create a mock rate limit plugin to satisfy dependency
    fastify.register(require('@fastify/rate-limit'), { max: 100 });
    
    // Register the real auth plugin and routes
    await fastify.register(authPlugin);
    await fastify.register(authRoutes, { prefix: '/api/v1' });
    
    await fastify.ready();
    vi.restoreAllMocks();
  });

  it('should return 200 and a token on valid login', async () => {
    vi.spyOn(authService, 'login').mockResolvedValue({
      userId: 'user-123',
      email: 'admin@edgesentinel.local',
      role: 'ADMIN'
    });

    const response = await fastify.inject({
      method: 'POST',
      url: '/api/v1/auth/login',
      payload: {
        email: 'admin@edgesentinel.local',
        password: 'correct-password'
      }
    });

    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.payload);
    expect(body.data).toHaveProperty('token');
    expect(body.data.user.role).toBe('ADMIN');
  });

  it('should return 401 on invalid login', async () => {
    vi.spyOn(authService, 'login').mockRejectedValue(
      new authService.AuthError('Invalid credentials', 401)
    );

    const response = await fastify.inject({
      method: 'POST',
      url: '/api/v1/auth/login',
      payload: {
        email: 'admin@edgesentinel.local',
        password: 'wrong-password'
      }
    });

    expect(response.statusCode).toBe(401);
    const body = JSON.parse(response.payload);
    expect(body.error.message).toBe('Invalid credentials');
  });
});
