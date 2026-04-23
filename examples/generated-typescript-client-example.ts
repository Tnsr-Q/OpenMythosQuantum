/** Example usage of the generated TypeScript Axios SDK. */

import { Configuration, DefaultApi } from "../generated/typescript-client";

async function main(): Promise<void> {
  const config = new Configuration({
    basePath: "https://api.openmythos.local/v1",
    accessToken: "replace-with-token",
  });

  const api = new DefaultApi(config);
  const { data } = await api.healthzGet();
  console.log("healthz:", data);
}

main().catch((error) => {
  console.error("SDK call failed", error);
  process.exit(1);
});
