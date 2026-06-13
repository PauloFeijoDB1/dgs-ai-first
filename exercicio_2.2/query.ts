import {
  app,
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";

export async function query(
  _request: HttpRequest,
  _context: InvocationContext,
): Promise<HttpResponseInit> {
  return {
    status: 200,
    jsonBody: {
      answer: "ok",
    },
  };
}

app.http("query", {
  methods: ["POST"],
  authLevel: "anonymous",
  route: "query",
  handler: query,
});
