import http from 'k6/http';
import { check, sleep } from 'k6';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

export const options = {
  stages: [
    { duration: '30s', target: 25 }, // Ramp-up to 25 virtual users
    { duration: '1m', target: 25 },  // Stay at 25 users for 1 minute
    { duration: '30s', target: 0 },  // Ramp-down to 0 users
  ],
  thresholds: {
    // SLOs:
    // 99% of requests must complete within 500ms
    http_req_duration: ['p(99)<500'],
    // Less than 1% of requests should fail
    http_req_failed: ['rate<0.01'],
  },
};

const API_BASE_URL = __ENV.API_BASE_URL || 'http://localhost:3000';
const API_TOKEN = __ENV.API_TOKEN || 'YOUR_JWT_TOKEN_HERE';

export default function () {
  const url = `${API_BASE_URL}/api/v1/telemetry`;
  
  // Create a payload matching the Zod schema from Phase 2
  const payload = JSON.stringify({
    eventId: uuidv4(),
    deviceId: `DEVICE-${__VU}`, // Use the virtual user ID to simulate different devices
    temperature: Math.random() * 50 + 20, // 20 to 70
    humidity: Math.random() * 60 + 30, // 30 to 90
    vibration: Math.random() * 5, // 0 to 5
    pressure: Math.random() * 200 + 900, // 900 to 1100
    machineState: 'RUNNING', // Valid states: RUNNING, IDLE, MAINTENANCE
    timestamp: Date.now(),
    mlInference: {
      score: Math.random(),
      severity: 'NORMAL',
      decision: 'LOG',
      modelVersion: 'v1.0.0'
    }
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_TOKEN}`,
    },
  };

  const res = http.post(url, payload, params);

  check(res, {
    'status is 200 or 201': (r) => r.status === 200 || r.status === 201,
  });

  // Wait 1 second before the next iteration
  sleep(1);
}
