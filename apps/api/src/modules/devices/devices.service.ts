import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export async function getDevices(dbClient: PrismaClient = prisma) {
  const data = await dbClient.device.findMany({
    orderBy: { created_at: 'desc' }
  });
  return data;
}
