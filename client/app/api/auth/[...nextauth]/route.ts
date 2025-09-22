import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

// Minimal NextAuth config using Google provider.
// Ensure the following env vars are set in client/.env.local:
// - NEXTAUTH_URL (e.g. http://localhost:3000)
// - NEXTAUTH_SECRET
// - GOOGLE_CLIENT_ID
// - GOOGLE_CLIENT_SECRET

const authOptions = {
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  session: {
    strategy: "jwt" as const,
  },
};

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
