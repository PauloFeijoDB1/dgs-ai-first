import { app, HttpRequest, HttpResponseInit } from '@azure/functions';
import { CosmosClient } from '@azure/cosmos';
import pino from 'pino';
import { z } from 'zod';

const logger = pino();

const FeedbackSchema = z.object({
  queryId: z.string().uuid(),
  rating: z.number().int().min(1).max(5),
  comment: z.string().max(2000).optional(),
  attendantEmail: z.string().email()
}).strict();

export async function feedbackHandler(
  request: HttpRequest
): Promise<HttpResponseInit> {
  const parsed = FeedbackSchema.safeParse(await request.json());
  if (!parsed.success) {
    return { status: 400, body: JSON.stringify(parsed.error.flatten()) };
  }

  const feedback = {
    queryId: parsed.data.queryId,
    rating: parsed.data.rating,
    comment: parsed.data.comment,
    attendantEmail: parsed.data.attendantEmail,
    timestamp: new Date().toISOString()
  };

  logger.info(
    { queryId: feedback.queryId, rating: feedback.rating },
    'Feedback recebido'
  );

  const env = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env;
  const connectionString = env?.COSMOS_CONNECTION_STRING;
  if (!connectionString) {
    return { status: 500, body: 'COSMOS_CONNECTION_STRING not configured' };
  }

  const client = new CosmosClient(connectionString);
  const database = client.database('novatech');
  const container = database.container('feedbacks');

  await container.items.create(feedback);

  return { status: 200, body: 'OK' };
}

app.http('feedback', {
  methods: ['POST'],
  handler: feedbackHandler
});