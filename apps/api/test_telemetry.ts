import Fastify from 'fastify';
import { telemetryController } from './src/modules/telemetry/telemetry.controller';
import { PrismaClient } from '@prisma/client';

async function test() {
  const prisma = new PrismaClient();
  const fastify = Fastify({ logger: false });
  await fastify.register(telemetryController, { prefix: '/api/v1' });
  await fastify.ready();

  console.log('--- 1. Testing Validation Error (422) ---');
  const invalidRes = await fastify.inject({
    method: 'POST',
    url: '/api/v1/telemetry',
    payload: {
      eventId: 'evt-test-invalid',
      // missing deviceId, temperature, etc.
    }
  });
  console.log('Invalid status:', invalidRes.statusCode);
  console.log('Invalid body:', invalidRes.body);
  if (invalidRes.statusCode !== 422) throw new Error('Expected 422');

  console.log('\n--- 2. Testing Valid Ingestion (201) ---');
  const testEventId = 'evt-test-' + Date.now();
  const validRes = await fastify.inject({
    method: 'POST',
    url: '/api/v1/telemetry',
    payload: {
      eventId: testEventId,
      deviceId: 'device-test-01',
      temperature: 42.5,
      humidity: 55.0,
      vibration: 0.15,
      pressure: 1012.8,
      machineState: 'RUNNING',
      timestamp: Date.now()
    }
  });
  console.log('Valid status:', validRes.statusCode);
  console.log('Valid body:', validRes.body);
  if (validRes.statusCode !== 201) throw new Error('Expected 201');

  console.log('\n--- 3. Testing Database Persistence ---');
  const dbRecord = await prisma.telemetry.findUnique({
    where: { event_id: testEventId },
    include: { device: true }
  });
  console.log('DB Record found:', dbRecord?.event_id, 'Device:', dbRecord?.device?.device_id);
  if (!dbRecord) throw new Error('Record not found in DB');

  console.log('\n--- 4. Testing Idempotency (200 on duplicate) ---');
  const duplicateRes = await fastify.inject({
    method: 'POST',
    url: '/api/v1/telemetry',
    payload: {
      eventId: testEventId,
      deviceId: 'device-test-01',
      temperature: 42.5,
      humidity: 55.0,
      vibration: 0.15,
      pressure: 1012.8,
      machineState: 'RUNNING',
      timestamp: Date.now()
    }
  });
  console.log('Duplicate status:', duplicateRes.statusCode);
  console.log('Duplicate body:', duplicateRes.body);
  if (duplicateRes.statusCode !== 200) throw new Error('Expected 200');

  const count = await prisma.telemetry.count({
    where: { event_id: testEventId }
  });
  console.log('Count of records with eventId in DB:', count);
  if (count !== 1) throw new Error('Expected count 1, found ' + count);

  // Clean up test record
  await prisma.telemetry.delete({ where: { id: dbRecord.id } });
  await prisma.device.delete({ where: { device_id: 'device-test-01' } });
  await prisma.$disconnect();
  console.log('\nAll tests passed successfully!');
}

test().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
