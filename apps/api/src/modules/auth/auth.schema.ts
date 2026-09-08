import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string({
    required_error: 'email is required',
    invalid_type_error: 'email must be a string',
  }).min(1, 'email cannot be empty'),

  password: z.string({
    required_error: 'password is required',
    invalid_type_error: 'password must be a string',
  }).min(1, 'password cannot be empty'),
});

export type LoginInput = z.infer<typeof loginSchema>;
