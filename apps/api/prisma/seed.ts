import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcrypt';

const prisma = new PrismaClient();

async function main() {
  const saltRounds = 10;
  const passwordHash = await bcrypt.hash('admin123', saltRounds);

  // Upsert default ADMIN user
  const adminUser = await prisma.user.upsert({
    where: { email: 'admin@edgesentinel.local' },
    update: {
      password_hash: passwordHash,
      role: 'ADMIN',
    },
    create: {
      email: 'admin@edgesentinel.local',
      password_hash: passwordHash,
      role: 'ADMIN',
    },
  });

  console.log(
    `Seeded ADMIN user: ${adminUser.email} (ID: ${adminUser.id}, Role: ${adminUser.role})`
  );

  // Upsert baseline Device
  const baselineDevice = await prisma.device.upsert({
    where: { device_id: 'machine-001' },
    update: {
      status: 'ACTIVE',
      name: 'Baseline Machine 001',
    },
    create: {
      device_id: 'machine-001',
      name: 'Baseline Machine 001',
      status: 'ACTIVE',
    },
  });

  console.log(
    `Seeded baseline device: ${baselineDevice.device_id} (ID: ${baselineDevice.id}, Status: ${baselineDevice.status})`
  );
}

main()
  .catch((e) => {
    console.error('Error executing seed script:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
