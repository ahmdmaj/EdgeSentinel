import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import Fastify from 'fastify';
import authPlugin from '../../plugins/auth';
import { authRoutes } from './auth.controller';
import * as authService from './auth.service';

describe('Auth Module', () => {
  let app: any;

  beforeAll(async () => {
    process.env.JWT_SECRET = 'test-secret';
    app = Fastify();
    await app.register(authPlugin);
    await app.register(authRoutes, { prefix: '/api/v1' });
    await app.ready();
  });

  afterAll(async () => {
    await app.close();
    vi.restoreAllMocks();
  });

  it('should return a JWT on valid login', async () => {
    // Mock database lookup
    vi.spyOn(authService, 'login').mockResolvedValue({
      userId: '1',
      email: 'test@example.com',
      role: 'ADMIN',
    });

    const response = await app.inject({
      method: 'POST',
      url: '/api/v1/auth/login',
      payload: {
        email: 'test@example.com',
        password: 'password123',
      },
    });

    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.payload);
    expect(body.data.token).toBeDefined();
    expect(body.data.user.email).toBe('test@example.com');
  });

  it('should return 401 on invalid login', async () => {
    vi.spyOn(authService, 'login').mockRejectedValue(new authService.AuthError('Invalid credentials', 401));

    const response = await app.inject({
      method: 'POST',
      url: '/api/v1/auth/login',
      payload: {
        email: 'test@example.com',
        password: 'wrongpassword',
      },
    });

    expect(response.statusCode).toBe(401);
  });
});
