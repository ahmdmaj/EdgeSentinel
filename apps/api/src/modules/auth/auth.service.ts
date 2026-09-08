import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcrypt';
import { LoginInput } from './auth.schema';

const prisma = new PrismaClient();

export class AuthError extends Error {
  statusCode: number;

  constructor(message: string, statusCode: number = 401) {
    super(message);
    this.name = 'AuthError';
    this.statusCode = statusCode;
  }
}

export interface AuthUserResult {
  userId: string;
  email: string;
  role: string;
}

/**
 * Authenticates a user by email and password using bcrypt and Prisma.
 * Strictly decoupled from HTTP request/reply objects.
 */
export async function login(
  credentials: LoginInput,
  dbClient: PrismaClient = prisma
): Promise<AuthUserResult> {
  const user = await dbClient.user.findUnique({
    where: { email: credentials.email },
  });

  if (!user) {
    throw new AuthError('Invalid email or password', 401);
  }

  const isPasswordValid = await bcrypt.compare(
    credentials.password,
    user.password_hash
  );

  if (!isPasswordValid) {
    throw new AuthError('Invalid email or password', 401);
  }

  return {
    userId: user.id,
    email: user.email,
    role: user.role,
  };
}

/**
 * Ensures default users exist in the database with hashed passwords.
 * Creates 'admin' and role-based accounts on first launch if users table is empty.
 */
export async function seedDefaultUsersIfEmpty(dbClient: PrismaClient = prisma): Promise<void> {
  const count = await dbClient.user.count();
  if (count === 0) {
    const defaultPasswordHash = await bcrypt.hash('password', 10);
    await dbClient.user.createMany({
      data: [
        {
          email: 'admin',
          password_hash: defaultPasswordHash,
          role: 'ADMIN',
        },
        {
          email: 'admin@edgesentinel.local',
          password_hash: defaultPasswordHash,
          role: 'ADMIN',
        },
        {
          email: 'operator@edgesentinel.local',
          password_hash: defaultPasswordHash,
          role: 'OPERATOR',
        },
        {
          email: 'viewer@edgesentinel.local',
          password_hash: defaultPasswordHash,
          role: 'VIEWER',
        },
      ],
    });
  }
}
