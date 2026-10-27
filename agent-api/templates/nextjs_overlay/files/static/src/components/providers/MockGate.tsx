import type { ReactNode } from "react";

type MockGateProps = {
  children: ReactNode;
};

/** Static sites have no API, so there is nothing to mock. */
export function MockGate({ children }: MockGateProps) {
  return children;
}
