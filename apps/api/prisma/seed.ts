import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcrypt';

const prisma = new PrismaClient();

async function main() {
  const seedEmail = process.env.SEED_ADMIN_EMAIL;
  const seedPassword = process.env.SEED_ADMIN_PASSWORD;

  if (!seedEmail || !seedPassword) {
    console.error('FATAL ERROR: SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD must be provided in the environment.');
    process.exit(1);
  }

  const saltRounds = 10;
  const passwordHash = await bcrypt.hash(seedPassword, saltRounds);

  // Upsert the single explicit ADMIN user
  const adminUser = await prisma.user.upsert({
    where: { email: seedEmail },
    update: {
      password_hash: passwordHash,
      role: 'ADMIN',
    },
    create: {
      email: seedEmail,
      password_hash: passwordHash,
      role: 'ADMIN',
    },
  });

  console.log(
    `Seeded ADMIN user: ${adminUser.email} (ID: ${adminUser.id}, Role: ${adminUser.role})`
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
