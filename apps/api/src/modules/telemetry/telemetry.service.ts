import { PrismaClient } from '@prisma/client';
import { TelemetryInput } from './telemetry.schema';

const prisma = new PrismaClient();

export interface ProcessTelemetryResult {
  isDuplicate: boolean;
  message: string;
  data: {
    id: string;
    eventId: string;
    deviceId: string;
    isDuplicate: boolean;
    createdAt: Date;
    machineState?: string;
    temperature?: number;
    humidity?: number;
    vibration?: number;
    pressure?: number;
    timestamp?: Date;
  };
}

/**
 * Service function to process validated telemetry data.
 * Implements database-backed idempotency using the eventId.
 * Never interacts with HTTP request or response objects directly.
 */
export async function processTelemetry(
  data: TelemetryInput,
  dbClient: PrismaClient = prisma
): Promise<ProcessTelemetryResult> {
  // 1. Idempotency Check: Query the database for the eventId
  const existingTelemetry = await dbClient.telemetry.findUnique({
    where: { event_id: data.eventId },
    include: {
      device: true,
      anomaly_events: true,
    },
  });

  if (existingTelemetry) {
    return {
      isDuplicate: true,
      message: 'Telemetry event already processed (idempotent duplicate)',
      data: {
        id: existingTelemetry.id,
        eventId: existingTelemetry.event_id,
        deviceId: data.deviceId,
        isDuplicate: true,
        createdAt: existingTelemetry.created_at,
        machineState: existingTelemetry.machine_state,
        temperature: existingTelemetry.temperature,
        humidity: existingTelemetry.humidity,
        vibration: existingTelemetry.vibration,
        pressure: existingTelemetry.pressure,
        timestamp: existingTelemetry.timestamp,
      },
    };
  }

  // 2. Normalize timestamp to JavaScript Date object
  const normalizedTimestamp =
    data.timestamp instanceof Date
      ? data.timestamp
      : new Date(data.timestamp);

  // 3. Create telemetry record with device association (connectOrCreate)
  const createdRecord = await dbClient.telemetry.create({
    data: {
      event_id: data.eventId,
      temperature: data.temperature,
      humidity: data.humidity,
      vibration: data.vibration,
      pressure: data.pressure,
      machine_state: data.machineState,
      timestamp: normalizedTimestamp,
      device: {
        connectOrCreate: {
          where: { device_id: data.deviceId },
          create: {
            device_id: data.deviceId,
            name: data.deviceId,
            status: 'ACTIVE',
          },
        },
      },
      ...(data.anomalyScore !== undefined && data.severity
        ? {
            anomaly_events: {
              create: {
                severity: data.severity,
                score: data.anomalyScore,
                decision: data.processingDecision || 'NONE',
                model_version: 'v1.0.0',
              },
            },
          }
        : {}),
    },
    include: {
      device: true,
      anomaly_events: true,
    },
  });

  return {
    isDuplicate: false,
    message: 'Telemetry recorded successfully',
    data: {
      id: createdRecord.id,
      eventId: createdRecord.event_id,
      deviceId: data.deviceId,
      isDuplicate: false,
      createdAt: createdRecord.created_at,
      machineState: createdRecord.machine_state,
      temperature: createdRecord.temperature,
      humidity: createdRecord.humidity,
      vibration: createdRecord.vibration,
      pressure: createdRecord.pressure,
      timestamp: createdRecord.timestamp,
    },
  };
}

// Aliases for flexibility and consistency
export const recordTelemetry = processTelemetry;
export const createTelemetry = processTelemetry;
