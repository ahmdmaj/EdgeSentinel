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
    invalid_type_error: 'humidity must be a number',
  }).default(50.0),

  vibration: z.number({
    invalid_type_error: 'vibration must be a number',
  }).default(0.5),

  pressure: z.number({
    invalid_type_error: 'pressure must be a number',
  }).default(1013.25),

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

export const getTelemetryQuerySchema = z.object({
  limit: z.coerce.number().min(1).max(100).default(20),
  offset: z.coerce.number().min(0).default(0),
});
