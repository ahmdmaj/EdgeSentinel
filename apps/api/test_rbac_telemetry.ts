import Fastify from 'fastify';
import authPlugin from './src/plugins/auth';
import { authRoutes } from './src/modules/auth/auth.controller';
import { telemetryController } from './src/modules/telemetry/telemetry.controller';
import { seedDefaultUsersIfEmpty } from './src/modules/auth/auth.service';
import { PrismaClient } from '@prisma/client';

async function testRbacTelemetry() {
  process.env.JWT_SECRET = 'rbac-test-secret-12345';

  const prisma = new PrismaClient();
  await seedDefaultUsersIfEmpty(prisma);

  const fastify = Fastify({ logger: false });
  await fastify.register(authPlugin);
  await fastify.register(authRoutes, { prefix: '/api/v1' });
  await fastify.register(telemetryController, { prefix: '/api/v1' });
  await fastify.ready();

  // Helper to obtain token for a given user
  async function getToken(email: string) {
    const res = await fastify.inject({
      method: 'POST',
      url: '/api/v1/auth/login',
      payload: { email, password: 'password' },
    });
    const body = JSON.parse(res.body);
    return body.data.token;
  }

  const adminToken = await getToken('admin@edgesentinel.local');
  const operatorToken = await getToken('operator@edgesentinel.local');
  const viewerToken = await getToken('viewer@edgesentinel.local');

  console.log('--- 1. POST /api/v1/telemetry RBAC tests ---');

  // 1a. Unauthenticated request -> 401
  const postNoAuth = await fastify.inject({
    method: 'POST',
    url: '/api/v1/telemetry',
    payload: { eventId: 'evt-test-1', deviceId: 'machine-001', temperature: 30, humidity: 40, vibration: 0.1, pressure: 1000, machineState: 'RUNNING', timestamp: Date.now() },
  });
  console.log('POST without token status:', postNoAuth.statusCode);
  if (postNoAuth.statusCode !== 401) throw new Error('Expected 401 on unauthenticated POST /telemetry');

  // 1b. VIEWER role -> 403 Forbidden
  const postViewer = await fastify.inject({
    method: 'POST',
    url: '/api/v1/telemetry',
    headers: { authorization: `Bearer ${viewerToken}` },
    payload: { eventId: 'evt-test-2', deviceId: 'machine-001', temperature: 30, humidity: 40, vibration: 0.1, pressure: 1000, machineState: 'RUNNING', timestamp: Date.now() },
  });
  console.log('POST with VIEWER role status:', postViewer.statusCode);
  if (postViewer.statusCode !== 403) throw new Error('Expected 403 on VIEWER POST /telemetry');

  // 1c. OPERATOR role -> 201 Created
  const evtIdOperator = 'evt-test-op-' + Date.now();
  const postOperator = await fastify.inject({
    method: 'POST',
    url: '/api/v1/telemetry',
    headers: { authorization: `Bearer ${operatorToken}` },
    payload: { eventId: evtIdOperator, deviceId: 'machine-001', temperature: 32, humidity: 45, vibration: 0.12, pressure: 1010, machineState: 'RUNNING', timestamp: Date.now() },
  });
  console.log('POST with OPERATOR role status:', postOperator.statusCode);
  if (postOperator.statusCode !== 201) throw new Error('Expected 201 on OPERATOR POST /telemetry');

  // 1d. ADMIN role -> 201 Created
  const evtIdAdmin = 'evt-test-admin-' + Date.now();
  const postAdmin = await fastify.inject({
    method: 'POST',
    url: '/api/v1/telemetry',
    headers: { authorization: `Bearer ${adminToken}` },
    payload: { eventId: evtIdAdmin, deviceId: 'machine-001', temperature: 28, humidity: 50, vibration: 0.08, pressure: 1013, machineState: 'RUNNING', timestamp: Date.now() },
  });
  console.log('POST with ADMIN role status:', postAdmin.statusCode);
  if (postAdmin.statusCode !== 201) throw new Error('Expected 201 on ADMIN POST /telemetry');

  console.log('\n--- 2. GET /api/v1/telemetry RBAC tests ---');

  // 2a. Unauthenticated request -> 401
  const getNoAuth = await fastify.inject({
    method: 'GET',
    url: '/api/v1/telemetry',
  });
  console.log('GET without token status:', getNoAuth.statusCode);
  if (getNoAuth.statusCode !== 401) throw new Error('Expected 401 on unauthenticated GET /telemetry');

  // 2b. VIEWER role -> 200 OK
  const getViewer = await fastify.inject({
    method: 'GET',
    url: '/api/v1/telemetry',
    headers: { authorization: `Bearer ${viewerToken}` },
  });
  console.log('GET with VIEWER role status:', getViewer.statusCode);
  if (getViewer.statusCode !== 200) throw new Error('Expected 200 on VIEWER GET /telemetry');

  // 2c. OPERATOR role -> 200 OK
  const getOperator = await fastify.inject({
    method: 'GET',
    url: '/api/v1/telemetry',
    headers: { authorization: `Bearer ${operatorToken}` },
  });
  console.log('GET with OPERATOR role status:', getOperator.statusCode);
  if (getOperator.statusCode !== 200) throw new Error('Expected 200 on OPERATOR GET /telemetry');

  // 2d. ADMIN role -> 200 OK
  const getAdmin = await fastify.inject({
    method: 'GET',
    url: '/api/v1/telemetry',
    headers: { authorization: `Bearer ${adminToken}` },
  });
  console.log('GET with ADMIN role status:', getAdmin.statusCode);
  if (getAdmin.statusCode !== 200) throw new Error('Expected 200 on ADMIN GET /telemetry');

  // Clean up created telemetry records
  await prisma.telemetry.deleteMany({
    where: { event_id: { in: [evtIdOperator, evtIdAdmin] } },
  });
  await prisma.$disconnect();

  console.log('\nAll Telemetry RBAC tests passed successfully!');
}

testRbacTelemetry().catch((err) => {
  console.error('Test failed:', err);
  process.exit(1);
});
