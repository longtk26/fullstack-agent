export type TLoginResult = { ok: true } | { ok: false; message: string };

export type TUserRole = "USER" | "ADMIN";

export type TCurrentUser = {
  id: string;
  email: string;
  role: TUserRole;
  createdAt: string | null;
};
