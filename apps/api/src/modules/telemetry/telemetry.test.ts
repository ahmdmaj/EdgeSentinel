import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import Fastify from 'fastify';
import authPlugin from '../../plugins/auth';
import { telemetryController } from './telemetry.controller';
import * as telemetryService from './telemetry.service';

describe('Telemetry Module', () => {
  let app: any;

  beforeAll(async () => {
    process.env.JWT_SECRET = 'test-secret';
    app = Fastify();
    await app.register(authPlugin);
    await app.register(telemetryController, { prefix: '/api/v1' });
    await app.ready();
  });

  afterAll(async () => {
    await app.close();
    vi.restoreAllMocks();
  });

  it('should deny POST /api/v1/telemetry for VIEWER role (403)', async () => {
    const viewerToken = app.jwt.sign({ userId: '1', email: 'viewer@test.com', role: 'VIEWER' });
    
    const response = await app.inject({
      method: 'POST',
      url: '/api/v1/telemetry',
      headers: { authorization: `Bearer ${viewerToken}` },
      payload: {
        eventId: 'test-1',
        deviceId: 'dev-1',
        timestamp: new Date().toISOString(),
        temperature: 20
      }
    });

    expect(response.statusCode).toBe(403);
  });

  it('should allow POST /api/v1/telemetry for OPERATOR role (201)', async () => {
    const operatorToken = app.jwt.sign({ userId: '2', email: 'op@test.com', role: 'OPERATOR' });
    
    vi.spyOn(telemetryService, 'processTelemetry').mockResolvedValue({
      isDuplicate: false,
      message: 'Created',
      data: { id: 'x', eventId: 'test-2', deviceId: 'dev-1', isDuplicate: false, createdAt: new Date() }
    });

    const response = await app.inject({
      method: 'POST',
      url: '/api/v1/telemetry',
      headers: { authorization: `Bearer ${operatorToken}` },
      payload: {
        eventId: 'test-2',
        deviceId: 'dev-1',
        timestamp: new Date().toISOString(),
        temperature: 20
      }
    });

    expect(response.statusCode).toBe(201);
  });

  it('should return 200 for idempotent requests (same eventId)', async () => {
    const adminToken = app.jwt.sign({ userId: '3', email: 'admin@test.com', role: 'ADMIN' });
    
    vi.spyOn(telemetryService, 'processTelemetry').mockResolvedValue({
      isDuplicate: true,
      message: 'Duplicate',
      data: { id: 'y', eventId: 'test-3', deviceId: 'dev-1', isDuplicate: true, createdAt: new Date() }
    });

    const response = await app.inject({
      method: 'POST',
      url: '/api/v1/telemetry',
      headers: { authorization: `Bearer ${adminToken}` },
      payload: {
        eventId: 'test-3',
        deviceId: 'dev-1',
        timestamp: new Date().toISOString(),
        temperature: 20
      }
    });

    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.payload);
    expect(body.data.isDuplicate).toBe(true);
  });
});
