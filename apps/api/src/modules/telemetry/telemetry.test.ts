import { describe, it, expect, vi, beforeEach } from 'vitest';
import Fastify from 'fastify';
import authPlugin from '../../plugins/auth';
import { telemetryRoutes } from './telemetry.controller';
import * as telemetryService from './telemetry.service';

describe('Telemetry Module Integration', () => {
  let fastify: any;

  beforeEach(async () => {
    fastify = Fastify();
    
    // Create a mock rate limit plugin to satisfy auth plugin dependency if any
    fastify.register(require('@fastify/rate-limit'), { max: 100 });
    
    // Register the auth plugin to provide fastify.jwt and authenticate hooks
    await fastify.register(authPlugin);
    
    // Register telemetry routes
    await fastify.register(telemetryRoutes, { prefix: '/api/v1' });
    
    await fastify.ready();
    vi.restoreAllMocks();
  });

  it('should return 403 when VIEWER tries to POST telemetry', async () => {
    const token = fastify.jwt.sign({
      userId: 'user-viewer',
      email: 'viewer@edgesentinel.local',
      role: 'VIEWER'
    }, { expiresIn: '1h' });

    const response = await fastify.inject({
      method: 'POST',
      url: '/api/v1/telemetry',
      headers: {
        authorization: `Bearer ${token}`
      },
      payload: {
        eventId: 'test-event-1',
        deviceId: 'DEVICE-001',
        temperature: 45.0,
        humidity: 50.0,
        vibration: 0.5,
        pressure: 1013.25,
        timestamp: Date.now()
      }
    });

    expect(response.statusCode).toBe(403);
    const body = JSON.parse(response.payload);
    expect(body.error.message).toMatch(/Forbidden/i);
  });

  it('should return 201 when OPERATOR POSTs new telemetry', async () => {
    vi.spyOn(telemetryService, 'processTelemetry').mockResolvedValue({
      isDuplicate: false,
      message: 'Telemetry ingested successfully',
      data: { eventId: 'test-event-2' }
    });

    const token = fastify.jwt.sign({
      userId: 'user-operator',
      email: 'operator@edgesentinel.local',
      role: 'OPERATOR'
    }, { expiresIn: '1h' });

    const response = await fastify.inject({
      method: 'POST',
      url: '/api/v1/telemetry',
      headers: {
        authorization: `Bearer ${token}`
      },
      payload: {
        eventId: 'test-event-2',
        deviceId: 'DEVICE-001',
        temperature: 45.0,
        humidity: 50.0,
        vibration: 0.5,
        pressure: 1013.25,
        timestamp: Date.now()
      }
    });

    expect(response.statusCode).toBe(201);
  });

  it('should handle duplicate eventId safely and return 200 idempotency response', async () => {
    vi.spyOn(telemetryService, 'processTelemetry').mockResolvedValue({
      isDuplicate: true,
      message: 'Duplicate event received and safely ignored',
      data: { eventId: 'test-event-dup' }
    });

    const token = fastify.jwt.sign({
      userId: 'user-operator',
      email: 'operator@edgesentinel.local',
      role: 'OPERATOR'
    }, { expiresIn: '1h' });

    const response = await fastify.inject({
      method: 'POST',
      url: '/api/v1/telemetry',
      headers: {
        authorization: `Bearer ${token}`
      },
      payload: {
        eventId: 'test-event-dup',
        deviceId: 'DEVICE-001',
        temperature: 45.0,
        humidity: 50.0,
        vibration: 0.5,
        pressure: 1013.25,
        timestamp: Date.now()
      }
    });

    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.payload);
    expect(body.data.message).toMatch(/duplicate/i);
  });
});
