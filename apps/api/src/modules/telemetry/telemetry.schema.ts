import { z } from 'zod';

export const telemetrySchema = z.object({
  eventId: z.string({
    required_error: 'eventId is required',
    invalid_type_error: 'eventId must be a string',
  }).min(1, 'eventId cannot be empty'),

  deviceId: z.string({
    required_error: 'deviceId is required',
    invalid_type_error: 'deviceId must be a string',
  }).min(1, 'deviceId cannot be empty'),

  temperature: z.number({
    required_error: 'temperature is required',
    invalid_type_error: 'temperature must be a number',
  }),

  humidity: z.number({
    required_error: 'humidity is required',
    invalid_type_error: 'humidity must be a number',
  }),

  vibration: z.number({
    required_error: 'vibration is required',
    invalid_type_error: 'vibration must be a number',
  }),

  pressure: z.number({
    required_error: 'pressure is required',
    invalid_type_error: 'pressure must be a number',
  }),

  machineState: z.string({
    required_error: 'machineState is required',
    invalid_type_error: 'machineState must be a string',
  }).min(1, 'machineState cannot be empty'),

  timestamp: z.union([
    z.number({ invalid_type_error: 'timestamp must be a unix epoch number or valid date' }),
    z.string().refine((val) => !isNaN(Date.parse(val)), {
      message: 'timestamp string must be a valid date format',
    }),
    z.date(),
  ]),

  // Optional ML and edge operational metrics
  anomalyScore: z.number().optional(),
  severity: z.string().optional(),
  processingDecision: z.string().optional(),
  edgeCpu: z.number().optional(),
  networkLatency: z.number().optional(),
});

export const createTelemetrySchema = telemetrySchema;

export type TelemetryInput = z.infer<typeof telemetrySchema>;
